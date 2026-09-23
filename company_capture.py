"""Best-effort capture of the photographed company portal and AO handoff.

This module never sends mail or edits an AO workbook. It records the exact
screen it reaches so the Windows operator can adjust the remaining RPA.
"""
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse


PORTAL_URL = 'https://hope2.hyosung.com/Website/Portal/Main.aspx'
REPORT_NAME = '납기경과 미입고_생산계획구분'


class CaptureStopped(RuntimeError):
    pass


def write_event(output, stage, **details):
    output.mkdir(parents=True, exist_ok=True)
    event = {'time': dt.datetime.now().isoformat(timespec='seconds'), 'stage': stage, **details}
    with (output / 'events.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + '\n')


def page_location(page):
    parsed = urlparse(page.url)
    return {'host': parsed.hostname, 'path': parsed.path}


def find_page(context, name, timeout_seconds=45, *, exact=True):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        for page in reversed(context.pages):
            if page.is_closed():
                continue
            try:
                if any(page.get_by_role(role, name=name, exact=exact).count() == 1
                       for role in ('link', 'button')) or page.get_by_text(name, exact=exact).count() > 0:
                    return page
            except Exception:
                pass
        time.sleep(.25)
    raise CaptureStopped(f'화면에서 {name!r} 항목을 하나로 확인하지 못함')


def click_unique(page, name):
    target = page.get_by_role('link', name=name, exact=True)
    if target.count() != 1:
        target = page.get_by_text(name, exact=True)
    if target.count() != 1:
        raise CaptureStopped(f'{name!r} 클릭 대상이 없거나 여러 개임')
    target.click()


def open_cube_menu(page):
    for label in ('정육면체 분석 메뉴', '분석 메뉴', 'Cube'):
        for role in ('button', 'link'):
            target = page.get_by_role(role, name=label, exact=True)
            if target.count() == 1:
                target.click()
                return 'named control'
    # The reference capture places this icon at the extreme right of a wide
    # BI Portal viewport. Use this once, and only accept it if the menu appears.
    viewport = page.viewport_size
    if not viewport or viewport['width'] < 1400:
        raise CaptureStopped('정육면체 버튼을 찾지 못했고 화면 폭도 참조 캡처보다 작음')
    page.mouse.click(viewport['width'] - 39, 60)
    try:
        page.get_by_text(REPORT_NAME, exact=True).wait_for(state='visible', timeout=4000)
    except Exception as exc:
        raise CaptureStopped('오른쪽 정육면체 좌표 클릭 후 대상 메뉴가 나타나지 않음') from exc
    return 'verified top-right position'


def capture_download(output, *, portal_url=PORTAL_URL, login_timeout=180,
                     browser_channel='chrome', allow_simulator=False):
    from playwright.sync_api import sync_playwright

    output = Path(output).resolve()
    profile = output.parent / 'chrome-profile'
    if output.exists() and any(output.iterdir()):
        raise CaptureStopped('실행 폴더가 비어 있지 않음: 새 실행 폴더를 사용하세요')
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(profile), channel=browser_channel, headless=False,
            accept_downloads=True, viewport={'width': 1900, 'height': 900})
        downloads = []

        def watch(page):
            page.on('download', lambda item: downloads.append(item))

        context.on('page', watch)
        for page in context.pages:
            watch(page)
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(portal_url, wait_until='domcontentloaded', timeout=45000)
            write_event(output, 'portal_opened', **page_location(page))
            # Login is done by the employee in the visible Chrome window.
            page = find_page(context, '업무시스템', login_timeout)
            click_unique(page, '업무시스템')
            write_event(output, 'systems_clicked', **page_location(page))
            page = find_page(context, 'Power BI')
            click_unique(page, 'Power BI')
            write_event(output, 'power_bi_clicked', **page_location(page))
            page = find_page(context, '구매')
            click_unique(page, '구매')
            write_event(output, 'purchase_clicked', **page_location(page))
            page = find_page(context, '납기 현황')
            click_unique(page, '납기 현황')
            write_event(output, 'delivery_clicked', **page_location(page))
            page = find_page(context, '납기 현황', exact=False)
            if page.get_by_role('link', name=REPORT_NAME, exact=True).count() != 1:
                method = open_cube_menu(page)
                write_event(output, 'cube_opened', method=method, **page_location(page))
            click_unique(page, REPORT_NAME)
            deadline = time.monotonic() + 45
            while not downloads and time.monotonic() < deadline:
                page.wait_for_timeout(200)
            if len(downloads) != 1:
                raise CaptureStopped(f'다운로드 수가 예상과 다름: {len(downloads)}')
            download = downloads[0]
            if download.suggested_filename.lower() != 'analysis.sapaox':
                raise CaptureStopped('다운로드 파일명이 analysis.sapaox가 아님')
            destination = output / 'analysis.sapaox'
            download.save_as(str(destination))
            prefix = destination.read_bytes()[:120].lstrip()
            if not destination.stat().st_size or (not allow_simulator and
                    (prefix.startswith(b'{') or prefix.lower().startswith(b'<!doctype html'))):
                destination.unlink(missing_ok=True)
                raise CaptureStopped('실제 AO 파일로 확인되지 않음')
            write_event(output, 'ao_downloaded', file=destination.name,
                        bytes=destination.stat().st_size, **page_location(page))
            return destination
        except Exception as exc:
            try:
                active = next((p for p in reversed(context.pages) if not p.is_closed()), None)
                if active:
                    active.screenshot(path=str(output / 'stopped.png'))
            except Exception:
                pass
            write_event(output, 'stopped', error=str(exc))
            raise
        finally:
            context.close()


def inspect_ao(downloaded, output, *, open_file=True):
    """Collect visible Windows AO/Excel UI evidence after a real download."""
    if sys.platform != 'win32':
        raise CaptureStopped('AO 창 조사는 Windows에서만 가능')
    from pywinauto import Desktop

    downloaded = Path(downloaded).resolve()
    output = Path(output).resolve()
    if downloaded.suffix.lower() != '.sapaox' or not downloaded.is_file():
        raise CaptureStopped('실제 .sapaox 파일 경로가 필요함')
    output.mkdir(parents=True, exist_ok=True)
    if open_file:
        os.startfile(str(downloaded))
        write_event(output, 'ao_open_requested', file=downloaded.name)
    desktop = Desktop(backend='uia')
    deadline = time.monotonic() + 60
    windows = []
    while time.monotonic() < deadline:
        windows = [window for window in desktop.windows() if
                   re.search('HWP|프롬프트|Excel', window.window_text(), re.I)]
        if windows:
            break
        time.sleep(.5)
    if not windows:
        raise CaptureStopped('60초 안에 HWP/프롬프트/Excel 창이 보이지 않음')
    evidence = []
    for index, window in enumerate(windows):
        controls = []
        for child in window.descendants()[:300]:
            try:
                rect = child.rectangle()
                controls.append({'name': child.window_text()[:120],
                                 'type': child.element_info.control_type,
                                 'rect': [rect.left, rect.top, rect.right, rect.bottom]})
            except Exception:
                continue
        evidence.append({'title': window.window_text(), 'controls': controls})
        try:
            window.capture_as_image().save(output / f'ao-window-{index+1}.png')
        except Exception:
            pass
    (output / 'ao-windows.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    write_event(output, 'ao_windows_inspected', count=len(evidence))
    inspect_running_excel(output)
    return evidence


def inspect_running_excel(output):
    """Read only names, dimensions and known headers from an already open Excel."""
    if sys.platform != 'win32':
        raise CaptureStopped('Excel 창 조사는 Windows에서만 가능')
    import pythoncom
    import win32com.client

    output = Path(output).resolve()
    pythoncom.CoInitialize()
    try:
        try:
            excel = win32com.client.GetActiveObject('Excel.Application')
        except Exception:
            write_event(output, 'excel_not_running')
            return []
        result = []
        known = {'구매부서', '협력사', '생산계획 미확정', '계(총계+생산계획 미확정)', '4주이상'}
        for book in excel.Workbooks:
            sheets = []
            for sheet in book.Worksheets:
                area = sheet.UsedRange
                found = []
                first_row, first_col = area.Row, area.Column
                row_count = min(25, area.Rows.Count)
                col_count = min(100, area.Columns.Count)
                block = sheet.Range(sheet.Cells(first_row, first_col),
                                    sheet.Cells(first_row + row_count - 1,
                                                first_col + col_count - 1)).Value2
                if row_count == 1 and col_count == 1:
                    block = ((block,),)
                elif row_count == 1:
                    block = (tuple(block),)
                elif col_count == 1:
                    block = tuple((value,) for value in block)
                for row_offset, values in enumerate(block):
                    for col_offset, value in enumerate(values):
                        if isinstance(value, str) and value.strip() in known:
                            found.append({'label': value.strip(), 'row': first_row + row_offset,
                                          'column': first_col + col_offset})
                sheets.append({'name': sheet.Name, 'used_range': area.Address,
                               'rows': area.Rows.Count, 'columns': area.Columns.Count,
                               'known_headers': found})
            result.append({'workbook': book.Name, 'sheets': sheets})
        (output / 'excel-structure.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        write_event(output, 'excel_structure_inspected', workbooks=len(result))
        return result
    finally:
        pythoncom.CoUninitialize()
