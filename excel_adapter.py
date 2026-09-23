"""Real desktop Excel COM. SAP itself is simulated, never claimed to be connected."""
import hashlib
import shutil
from pathlib import Path
from report_table import prepare_report


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def matrix(sheet):
    return tuple(tuple(row) for row in sheet.UsedRange.Value2)


def fingerprint(sheet):
    return {'values': matrix(sheet), 'formulas': sheet.UsedRange.Formula,
            'format': [[(sheet.Cells(r,c).NumberFormat, sheet.Cells(r,c).Interior.Color,
                          sheet.Cells(r,c).Font.Bold) for c in range(1, sheet.UsedRange.Columns.Count+1)]
                       for r in range(1, sheet.UsedRange.Rows.Count+1)]}


def process(template, destination, target_date, returned_date, cfg, scenario, log):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    excel = book = None
    template_hash = digest(template)
    try:
        excel = win32com.client.DispatchEx('Excel.Application')
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AutomationSecurity = 3
        excel.EnableEvents = False
        destination = Path(destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template, destination)
        book = excel.Workbooks.Open(str(destination), UpdateLinks=0, ReadOnly=False)
        # Simulated AO returns a date and fixture data. Refresh only occurs here.
        summary = book.Worksheets('요약')
        raw = book.Worksheets('Raw data')
        raw.Range('B1').NumberFormat = '@'
        raw.Range('B1').Value2 = returned_date
        if scenario == 'empty':
            raw.Range('A4:A9').Value2 = '기타구매팀'
        if scenario == 'bad_number':
            raw.Range('F4').Value2 = '확인필요'
        excel.CalculateFull()
        book.Save()
        log('save_working_copy', file=destination.name)
        before = {s.Name: fingerprint(s) for s in (summary, raw)}
        snapshot = destination.with_name('조회완료_원본.xlsx')
        book.SaveCopyAs(str(snapshot))
        if summary.Range('B1').Value2 != target_date:
            raise ValueError('조회 날짜 불일치: 발송 중단')
        area = summary.UsedRange
        if area.Rows.Count > 100000 or area.Columns.Count > 100:
            raise ValueError('요약 시트 범위가 예상보다 큼: 구조 확인 필요')
        values = area.Value2
        if not isinstance(values, tuple) or not isinstance(values[0], tuple):
            raise ValueError('요약 시트 표 구조를 읽을 수 없음')
        prepared = prepare_report(values, cfg)
        out_header, out_rows, totals = prepared['headers'], prepared['rows'], prepared['totals']
        keep_count = len(out_header)
        report = book.Worksheets.Add(After=book.Worksheets(book.Worksheets.Count))
        report.Name = '전력구매팀_발송'
        # First copy the entire summary as values; transformations affect only this sheet.
        report.Range(summary.UsedRange.Address).Value2 = summary.UsedRange.Value2
        report.Cells.Clear()
        report.Range('A1').Value2 = '조회일'
        report.Range('B1').NumberFormat = '@'
        report.Range('B1').Value2 = target_date
        final = [out_header] + out_rows + [[None]*keep_count] + [totals]
        report.Range(report.Cells(3,1),report.Cells(3+len(final)-1,keep_count)).Value2 = tuple(tuple(r) for r in final)
        report.UsedRange.Font.Name = '맑은 고딕'
        report.UsedRange.Font.Size = 11
        report.Range(report.Cells(3,1),report.Cells(3,keep_count)).Font.Bold = True
        report.Range(report.Cells(3,1),report.Cells(3,keep_count)).Interior.Color = 15132390
        report.Range(report.Cells(4,2),report.Cells(3+len(final)-1,keep_count)).NumberFormat = '#,##0'
        report.UsedRange.Columns.AutoFit()
        report.UsedRange.Rows.RowHeight = 22
        report.Range(report.Cells(3,1),report.Cells(3+len(out_rows),keep_count)).AutoFilter()
        for source in (summary,raw):
            if fingerprint(source) != before[source.Name]:
                raise ValueError('원본 시트 변경 감지')
        if report.UsedRange.HasFormula is not False:
            raise ValueError('발송 시트에 수식 발견')
        book.Save()
        book.Close(SaveChanges=False)
        book = excel.Workbooks.Open(str(destination), UpdateLinks=0, ReadOnly=True)
        report = book.Worksheets('전력구매팀_발송')
        saved = [list(r) for r in report.Range(report.Cells(3,1),report.Cells(3+len(final)-1,keep_count)).Value2]
        if saved != final or report.UsedRange.HasFormula is not False:
            raise ValueError('저장 후 재검증 실패')
        for name, expected in before.items():
            if fingerprint(book.Worksheets(name)) != expected:
                raise ValueError('저장 후 원본 시트 보존 실패')
        if digest(template) != template_hash:
            raise ValueError('템플릿 원본 변경')
        result = {'headers':out_header,'rows':out_rows,'totals':totals,'date':target_date,
                  'source_preserved':True,'values_only':True,'row_count':len(out_rows),
                  'workbook':str(destination),'workbook_sha256':digest(destination)}
        log('excel_verified', rows=len(out_rows), source_preserved=True, values_only=True)
        return result
    finally:
        if book is not None:
            book.Close(SaveChanges=False)
        if excel is not None:
            excel.Quit()
        book = excel = None
        pythoncom.CoUninitialize()
