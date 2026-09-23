import argparse
import datetime as dt
import json
import threading
import webbrowser
import urllib.request
from pathlib import Path
from simulator import ROOT, SCENARIOS, start_server
from runner import execute


def main():
    parser=argparse.ArgumentParser(description='주간 미입고 자동화 시뮬레이터 v1')
    parser.add_argument('command',choices=['serve','run','test','capture-real','inspect-ao'])
    parser.add_argument('--mode',choices=['mock','live'],default='mock')
    parser.add_argument('--scenario',choices=SCENARIOS,default='normal')
    parser.add_argument('--date',help='가상 실행일 YYYY-MM-DD. 생략 시 한국 현재 날짜')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--headed',action='store_true')
    parser.add_argument('--no-open',action='store_true')
    parser.add_argument('--portal-url',help='실제 포털 주소. 생략 시 캡처의 HOPE 2.0 주소')
    parser.add_argument('--file',help='inspect-ao에서 조사할 .sapaox 파일')
    parser.add_argument('--login-timeout',type=int,default=180,help='직원 로그인 대기 초')
    args=parser.parse_args()
    if args.command=='test':
        from tests import integration
        integration(args.mode)
        return
    if args.command=='capture-real':
        from company_capture import PORTAL_URL, capture_download
        folder=ROOT/'runtime'/'company'/dt.datetime.now().strftime('%Y%m%d-%H%M%S')
        downloaded=capture_download(folder,portal_url=args.portal_url or PORTAL_URL,
                                    login_timeout=args.login_timeout)
        print(json.dumps({'status':'DOWNLOADED','file':str(downloaded),'evidence':str(folder)},ensure_ascii=False,indent=2))
        return
    if args.command=='inspect-ao':
        from company_capture import inspect_ao
        if not args.file:
            parser.error('inspect-ao에는 --file 경로가 필요합니다')
        folder=ROOT/'runtime'/'company'/dt.datetime.now().strftime('%Y%m%d-%H%M%S')
        evidence=inspect_ao(Path(args.file),folder,open_file=not args.no_open)
        print(json.dumps({'status':'INSPECTED','windows':len(evidence),'evidence':str(folder)},ensure_ascii=False,indent=2))
        return
    try:
        server=start_server(args.port if args.command=='serve' else 0)
    except OSError:
        if args.command!='serve':
            raise
        url=f'http://127.0.0.1:{args.port}'
        with urllib.request.urlopen(url,timeout=2) as response:
            if '주간 미입고 업무 자동화' not in response.read().decode('utf-8'):
                raise RuntimeError('포트를 다른 프로그램이 사용하고 있습니다.')
        if not args.no_open:
            webbrowser.open(url)
        print('이미 실행 중: '+url)
        return
    if args.command=='serve':
        print('자동화 실험실: '+server.url,flush=True)
        if not args.no_open:
            webbrowser.open(server.url)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            server.shutdown()
    else:
        try:
            report=execute(server,args.scenario,args.mode,args.date,not args.headed)
            print(json.dumps(report,ensure_ascii=False,indent=2))
            raise SystemExit(0 if report['status'] in ['SUCCESS','ALREADY_SENT','SKIPPED'] else 1)
        finally:
            server.shutdown()


if __name__=='__main__':
    main()
