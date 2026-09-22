# 주간 미입고 자동화 — 1차 시뮬레이터

가상 회사 포털을 Microsoft Edge로 실제 조작하고, 실제 데스크톱 Excel에서 표를 가공한 뒤 로컬 테스트 메일함에 전송합니다. 실제 Jev API와 호출 없는 테스트 대역을 선택할 수 있습니다.

## 빠른 시작

Windows 10/11, Python 3.12 이상, Microsoft Edge, 데스크톱 Excel이 필요합니다. `start.cmd`를 실행하면 최초 의존성 설치 후 `http://127.0.0.1:8765`가 열립니다. 이 PC에는 실행 환경을 연결해 두었습니다.

1. 시나리오를 선택합니다. 정상은 `normal`, 메뉴명 변경은 `menu_changed`입니다.
2. 판단 모드를 선택합니다. `실제 Jev`는 `.env`의 API 키를 사용합니다. 테스트 대역은 Jev가 아닙니다.
3. 가상 실행일 `2026-09-21`을 유지하고 실행합니다. 조회일은 `2026-09-20`입니다.
4. 완료 후 `테스트 메일함`을 엽니다. 실제 회사 메일은 보내지 않습니다.
5. `runtime/runs/<실행ID>/`에 결과 Excel, HTML 메일, 실행 로그, 브라우저 추적, 결과 JSON이 저장됩니다.

`.env`에는 로컬용 `kmnoh16` 키를 설정했습니다. 전달 ZIP에는 키를 포함하지 않습니다. 다른 PC에서는 `.env.example`을 `.env`로 복사하고 키를 입력합니다.

## 구현한 순서

월요일 여부 확인 → 전날 계산 → 가상 로그인 → Power BI → 구매 → 납기 현황 → 정육면체 → 보고서 다운로드 → 가상 AO 연결 확인 → 달력일 입력 → 조회 완료 확인 → 실제 Excel 작업본 저장 → 요약/Raw data 보존 → 새 발송 시트에 값만 복사 → 전력구매팀 정확 일치 추출 → 구매부서/생산계획 미확정/계 열 제거 → 4주이상 내림차순 → 빈 행/팀 결과 합계 → 저장 후 다시 열어 검증 → 테스트 메일 전송 → 수신 확인.

결과행은 가상 데이터의 전력구매팀 소계로 재계산한 값입니다. 실제 보고서의 전체 총계행을 그대로 사용할지, 팀 소계를 만들지는 실제 AO 결과표 확인 후 확정해야 합니다.

## Jev가 판단하는 곳

- 정확한 메뉴 이름이 없을 때 실제 DOM에서 읽은 후보 중 목표 보고서 선택.
- 낯선 갱신 메시지를 `WAIT`, `RETRY`, `STOP` 중 하나로 분류.
- 선택 후 매크로가 해당 행동을 실행하고 화면을 다시 확인.
- API 실패·미등록 선택·불확실한 판단·호출 한도 초과는 중단.

공식 `POST https://api.typesafe.ai/v1/systemone`의 `Choice` 스키마를 사용합니다. 입력에는 가상 메뉴명/상태만 포함됩니다. 키는 로그에 기록하지 않습니다. 최고 확률 0.85, 2위와 차이 0.20은 시뮬레이션 초기 설정이며 한국어 회사 화면에 검증된 임계값이 아닙니다. 설정은 `config.json`에 있습니다.

## 테스트

```powershell
.venv\Scripts\python.exe -m unittest tests -v
.venv\Scripts\python.exe app.py test
.venv\Scripts\python.exe app.py test --mode live
.venv\Scripts\python.exe app.py run --scenario menu_changed --mode live --date 2026-09-21 --headed
```

`normal`, `menu_changed`, `refresh_delay`, `timeout_once`, `send_ack_lost`는 정상 완료가 기대됩니다. `wrong_date`, `empty`, `bad_number`, `unknown_popup`은 의도적인 중단이 기대됩니다. 동일 조회일/시나리오/판단 모드로 재실행하면 `ALREADY_SENT`로 중복 발송을 막습니다. 월요일 이외 날짜는 `SKIPPED`입니다. 테스트 실행마다 별도 메일함을 사용합니다.

테스트는 기대된 표의 각 셀과 소계를 독립된 정답에 비교하고, 오류가 정확한 이유로 발생했는지와 미발송을 확인합니다. `runtime/test-summary-mock.json`, `runtime/test-summary-live.json`에 최신 결과가 있습니다.

## 월요일 예약

`schedule.ps1`은 Windows 작업 스케줄러에 월요일 09:00 **시뮬레이션** 실행을 등록합니다. 아직 자동 등록하지 않았습니다. 필요할 때 실행하세요. 작업명은 `WeeklyDeliverySimulation`이며 사용자 로그인 세션에서 실행됩니다. PC 시간대는 한국으로 설정해야 합니다. 시간은 `-Time '10:00'`으로 바꿀 수 있습니다. 기존 동명 작업을 덮어쓰지 않습니다.

## 1차의 경계

- `.sapaox`는 가상 실행 정보를 담은 JSON입니다. 실제 SAP AO 파일 형식을 구현한 것이 아닙니다.
- AO 프롬프트·연결·조회 지연은 웹으로 재현합니다. SAP 플러그인의 Windows UI는 아직 연결하지 않았습니다.
- Excel COM 가공은 실제입니다. 가상 입력의 고정 범위 A3:I9를 사용합니다. 실제 회사 헤더·병합·크로스탭 범위는 다음 단계에서 맞춰야 합니다.
- 실제 AO 연결을 보존하는지는 이 가상 파일로 검증할 수 없습니다. 검증하는 보존 범위는 두 원본 시트의 셀 값·수식·일부 서식입니다.
- HiCloud는 실행 폴더 아래의 로컬 폴더로 재현합니다.
- 메일은 HTTP 로컬 수신함입니다. SMTP/Outlook/회사 웹메일 연동은 미구현입니다.
- 테스트용 로그인은 인증 보안 구현이 아닙니다. 가상 사용자 정보만 사용합니다.
- 회사 운영 모드는 제공하지 않습니다. 현재 단계는 가상 환경에서 동작과 실패 처리를 확인하는 1차입니다.

## 파일 구성

`app.py`: 실행 명령 / `simulator.py`: 가상 회사·AO·메일함 / `runner.py`: 브라우저와 단계 실행 / `decision.py`: Jev / `excel_adapter.py`: 실제 Excel / `tests.py`: 검증 / `assets/ao-template.xlsx`: 가상 자료.

Jev 연결 근거: https://api.typesafe.ai/docs
