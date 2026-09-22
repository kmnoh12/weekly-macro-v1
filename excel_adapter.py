"""Real desktop Excel COM. SAP itself is simulated, never claimed to be connected."""
import hashlib
import shutil
from pathlib import Path


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
        header = list(summary.Range('A3:I3').Value2[0])
        if len(set(header)) != len(header):
            raise ValueError('중복 헤더')
        required = ['구매부서', '협력사', cfg['sort_column'], *cfg['delete_columns']]
        if any(c not in header for c in required):
            raise ValueError('필수 헤더 누락')
        data = [list(r) for r in summary.Range('A4:I9').Value2]
        team_index = header.index('구매부서')
        rows = [r for r in data if r[team_index] == cfg['team']]
        if not rows:
            raise ValueError('전력구매팀 결과 0건: 발송 중단')
        for row in rows:
            if any(not isinstance(v, (int,float)) or v < 0 for v in row[2:]):
                raise ValueError('수량에 비숫자 또는 음수 포함')
        sort_index = header.index(cfg['sort_column'])
        rows.sort(key=lambda row: (-row[sort_index], str(row[1])))
        keep = [i for i,h in enumerate(header) if h not in cfg['delete_columns']]
        out_header = [header[i] for i in keep]
        out_rows = [[row[i] for i in keep] for row in rows]
        totals = ['결과'] + [sum(row[c] for row in out_rows) for c in range(1,len(keep))]
        report = book.Worksheets.Add(After=book.Worksheets(book.Worksheets.Count))
        report.Name = '전력구매팀_발송'
        # First copy the entire summary as values; transformations affect only this sheet.
        report.Range(summary.UsedRange.Address).Value2 = summary.UsedRange.Value2
        report.Cells.Clear()
        report.Range('A1').Value2 = '조회일'
        report.Range('B1').NumberFormat = '@'
        report.Range('B1').Value2 = target_date
        final = [out_header] + out_rows + [[None]*len(keep)] + [totals]
        report.Range(report.Cells(3,1),report.Cells(3+len(final)-1,len(keep))).Value2 = tuple(tuple(r) for r in final)
        report.UsedRange.Font.Name = '맑은 고딕'
        report.UsedRange.Font.Size = 11
        report.Range(report.Cells(3,1),report.Cells(3,len(keep))).Font.Bold = True
        report.Range(report.Cells(3,1),report.Cells(3,len(keep))).Interior.Color = 15132390
        report.Range(report.Cells(4,2),report.Cells(3+len(final)-1,len(keep))).NumberFormat = '#,##0'
        report.UsedRange.Columns.AutoFit()
        report.UsedRange.Rows.RowHeight = 22
        report.Range(report.Cells(3,1),report.Cells(3+len(out_rows),len(keep))).AutoFilter()
        for source in (summary,raw):
            if fingerprint(source) != before[source.Name]:
                raise ValueError('원본 시트 변경 감지')
        if report.UsedRange.HasFormula is not False:
            raise ValueError('발송 시트에 수식 발견')
        book.Save()
        book.Close(SaveChanges=False)
        book = excel.Workbooks.Open(str(destination), UpdateLinks=0, ReadOnly=True)
        report = book.Worksheets('전력구매팀_발송')
        saved = [list(r) for r in report.Range(report.Cells(3,1),report.Cells(3+len(final)-1,len(keep))).Value2]
        if saved != final or report.UsedRange.HasFormula is not False:
            raise ValueError('저장 후 재검증 실패')
        for name, expected in before.items():
            if fingerprint(book.Worksheets(name)) != expected:
                raise ValueError('저장 후 원본 시트 보존 실패')
        if digest(template) != template_hash:
            raise ValueError('템플릿 원본 변경')
        result = {'headers':out_header,'rows':out_rows,'totals':totals,'date':target_date,
                  'source_preserved':True,'values_only':True,'row_count':len(rows),
                  'workbook':str(destination),'workbook_sha256':digest(destination)}
        log('excel_verified', rows=len(rows), source_preserved=True, values_only=True)
        return result
    finally:
        if book is not None:
            book.Close(SaveChanges=False)
        if excel is not None:
            excel.Quit()
        book = excel = None
        pythoncom.CoUninitialize()
