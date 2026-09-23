"""Strict, row-count-independent extraction for the photographed report steps."""


def locate_header(matrix, cfg):
    required = {'구매부서', '협력사', cfg['sort_column'], *cfg['delete_columns']}
    matches = []
    for index, row in enumerate(matrix[:30]):
        labels = [value.strip() if isinstance(value, str) else value for value in row]
        if required.issubset(set(labels)):
            matches.append(index)
    if len(matches) != 1:
        raise ValueError(f'헤더 행을 하나로 확인하지 못함: {len(matches)}개')
    return matches[0]


def prepare_report(matrix, cfg):
    header_index = locate_header(matrix, cfg)
    header = list(matrix[header_index])
    while header and header[-1] is None:
        header.pop()
    if any(not isinstance(label, str) or not label.strip() for label in header):
        raise ValueError('빈 헤더 또는 병합 헤더: 구조 확인 필요')
    header = [label.strip() for label in header]
    if len(set(header)) != len(header):
        raise ValueError('중복 헤더')
    team_index = header.index('구매부서')
    supplier_index = header.index('협력사')
    sort_index = header.index(cfg['sort_column'])
    rows = []
    for raw in matrix[header_index + 1:]:
        row = list(raw[:len(header)])
        if len(row) < len(header):
            row.extend([None] * (len(header) - len(row)))
        if all(value is None or value == '' for value in row):
            continue
        if row[team_index] in ('결과', '총계'):
            continue
        if row[team_index] != cfg['team']:
            continue
        if not isinstance(row[supplier_index], str) or not row[supplier_index].strip():
            raise ValueError('전력구매팀 협력사명 누락')
        for index, value in enumerate(row):
            if index in (team_index, supplier_index):
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise ValueError('수량에 비숫자 또는 음수 포함')
        rows.append(row)
    if not rows:
        raise ValueError('전력구매팀 결과 0건: 발송 중단')
    rows.sort(key=lambda row: (-row[sort_index], row[supplier_index]))
    keep = [index for index, label in enumerate(header) if label not in cfg['delete_columns']]
    out_header = [header[index] for index in keep]
    out_rows = [[row[index] for index in keep] for row in rows]
    numeric_columns = [index for index in range(len(keep)) if keep[index] not in (team_index, supplier_index)]
    totals = ['결과' if index == 0 else
              sum(row[index] for row in out_rows) if index in numeric_columns else None
              for index in range(len(keep))]
    return {'headers': out_header, 'rows': out_rows, 'totals': totals,
            'source_header_row_index': header_index}
