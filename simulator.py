"""Local-only virtual company portal, AO prompt and mailbox."""
import datetime as dt
import html
import json
import secrets
import sqlite3
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCENARIOS = ['normal','menu_changed','refresh_delay','timeout_once','wrong_date','empty','bad_number','unknown_popup','send_ack_lost']

STYLE = '''<style>body{font:16px "Segoe UI","Malgun Gothic",sans-serif;background:#f3f5f9;color:#182638;margin:0}header{background:#172f51;color:white;padding:24px 6%}main{max-width:1040px;margin:28px auto;padding:28px;background:white;border-radius:12px}a{color:#205cb0}button,input,select{font:inherit;padding:10px;margin:7px;border:1px solid #a5b2c3;border-radius:5px}button{background:#205cb0;color:white;cursor:pointer}table{border-collapse:collapse;width:100%}td,th{padding:12px;border-bottom:1px solid #dce2e9;text-align:right}td:first-child,th:first-child{text-align:left}pre{white-space:pre-wrap;font-size:13px}nav a{margin-right:24px}.badge{background:#fff1cc;color:#553c00;padding:8px;display:inline-block;border-radius:5px}</style>'''


def page(title, body):
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><title>'+html.escape(title)+'</title>'+STYLE+'<header><b>주간 미입고 업무 자동화 · 1차</b></header><main><span class="badge">가상 회사 환경 / 실제 SAP 연결 없음</span><h1>'+html.escape(title)+'</h1>'+body+'</main></html>'


class SimulationServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, port=0, runtime=None):
        super().__init__(('127.0.0.1',port), Handler)
        self.runtime = Path(runtime or ROOT/'runtime')
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.token = secrets.token_urlsafe(24)
        self.scenes = {}
        self.ui_lock = threading.Lock()
        self.last = None
        with self.db() as con:
            con.execute('CREATE TABLE IF NOT EXISTS mail (key TEXT PRIMARY KEY, payload TEXT NOT NULL, received TEXT NOT NULL)')
    def db(self):
        return sqlite3.connect(self.runtime/'mailbox.sqlite3',timeout=10)
    @property
    def url(self):
        return f'http://127.0.0.1:{self.server_port}'
    def scene(self, run_id):
        return self.scenes[run_id]
    def accept_mail(self, key, payload):
        with self.db() as con:
            con.execute('INSERT OR IGNORE INTO mail VALUES (?,?,?)',(key,json.dumps(payload,ensure_ascii=False),dt.datetime.now().isoformat()))
            stored = json.loads(con.execute('SELECT payload FROM mail WHERE key=?',(key,)).fetchone()[0])
        if stored != payload:
            raise ValueError('동일 발송 ID에 다른 본문: 중단')


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass
    def reply(self, value, code=200, kind='text/html; charset=utf-8'):
        data = value.encode() if isinstance(value,str) else value
        self.send_response(code)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(data)
    def json(self,value,code=200):
        self.reply(json.dumps(value,ensure_ascii=False),code,'application/json; charset=utf-8')
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        run_id = query.get('run',[''])[0]
        p = parsed.path
        if p == '/':
            options=''.join(f'<option>{x}</option>' for x in SCENARIOS)
            self.reply(page('자동화 실험실',f'''<p>가상 포털을 브라우저로 조작하고 실제 Excel에서 표를 만든 뒤 로컬 메일함으로 보냅니다.</p>
            <nav><a href="/mailbox">테스트 메일함</a><a href="/status">최근 실행 결과</a></nav>
            <p><label>시나리오 <select id="scenario">{options}</select></label>
            <label>판단 모드 <select id="mode"><option value="mock">테스트 대역 (API 호출 없음)</option><option value="live">실제 Jev</option></select></label></p>
            <label>가상 실행일 <input type="date" id="date" value="2026-09-21"></label>
            <button id="start">전체 시뮬레이션 실행</button><pre id="result">대기 중</pre>
            <p>월요일이 아닌 날짜는 실행을 건너뜁니다. 실제 회사 수신자에게는 발송되지 않습니다.</p>
            <script>document.querySelector('#start').onclick=async()=>{{const b=document.querySelector('#start');b.disabled=true;
            let r=await fetch('/start',{{method:'POST',headers:{{'Content-Type':'application/json','X-Sim-Token':'{self.server.token}'}},body:JSON.stringify({{scenario:document.querySelector('#scenario').value,mode:document.querySelector('#mode').value,date:document.querySelector('#date').value}})}});
            document.querySelector('#result').textContent=JSON.stringify(await r.json(),null,2);
            const timer=setInterval(async()=>{{let s=await(await fetch('/status')).json();
            const titles={{RUNNING:'실행 중',SUCCESS:'완료 · 테스트 메일 수신 확인',FAILED:'중단',SKIPPED:'실행일이 월요일이 아닙니다',ALREADY_SENT:'이미 발송했습니다 · 중복 발송 방지',BUSY:'다른 실행이 진행 중입니다'}};
            let text=titles[s.status]||s.status;
            if(s.stage)text+='\\n현재 단계: '+s.stage;
            if(s.target_date)text+='\\n조회일: '+s.target_date;
            if(s.mode)text+='\\n판단 모드: '+(s.mode==='live'?'실제 Jev':'테스트 대역');
            if(s.result)text+='\\n전력구매팀 '+s.result.row_count+'개 행 · 원본 시트 보존 · 값만 복사 확인';
            if(s.jev_calls!==undefined)text+='\\nJev 판단 호출: '+s.jev_calls+'회';
            if(s.error)text+='\\n사유: '+s.error;
            if(s.run_id)text+='\\n실행 번호: '+s.run_id;
            document.querySelector('#result').textContent=text;
            if(s.status!=='RUNNING'){{clearInterval(timer);b.disabled=false;}}}},1000);}};</script>'''))
            return
        if p == '/status':
            self.json(self.server.last or {'status':'IDLE'})
            return
        if p == '/mailbox':
            with self.server.db() as con:
                entries=con.execute('SELECT payload,received FROM mail ORDER BY received DESC').fetchall()
            body=''.join('<article><h2>'+html.escape(json.loads(data)['subject'])+'</h2><p>'+html.escape(stamp)+' · '+html.escape(', '.join(json.loads(data)['to']))+'</p>'+json.loads(data)['html']+'</article><hr>' for data,stamp in entries)
            self.reply(page('테스트 메일함',body or '<p>수신된 메일이 없습니다.</p>'))
            return
        if p == '/receipt':
            with self.server.db() as con:
                row=con.execute('SELECT key FROM mail WHERE key=?',(query.get('key',[''])[0],)).fetchone()
            self.json({'received':bool(row)})
            return
        if run_id not in self.server.scenes:
            self.reply('Not found',404)
            return
        scene=self.server.scene(run_id)
        suffix='?run='+run_id
        link=lambda path,label: '<p><a href="'+path+suffix+'">'+html.escape(label)+'</a></p>'
        if p == '/portal':
            body=f'<form action="/systems"><input type="hidden" name="run" value="{run_id}"><label>사용자<input name="user" aria-label="사용자" required></label><label>암호<input type="password" name="password" aria-label="암호" required></label><button>로그인</button></form>'
        elif p == '/systems':
            scene['logged_in']=True
            body=link('/bi','Power BI')
        elif not scene.get('logged_in'):
            self.reply('Login required',403)
            return
        elif p == '/bi':
            body=link('/purchase','구매')
        elif p == '/purchase':
            body=link('/delivery','납기 현황')
        elif p == '/delivery':
            body=link('/cube','정육면체 분석 메뉴')
        elif p == '/cube':
            label='생산계획별 납기 초과 미입고 현황' if scene['scenario']=='menu_changed' else '납기경과 미입고_생산계획구분'
            body=link('/wrong','납기준수율')+link('/download',label)+link('/wrong','납품완료율_자재기준')
        elif p == '/download':
            payload=json.dumps({'simulator':'weekly-macro-v1','run':run_id,'kind':'AO-launch-placeholder'}).encode()
            self.send_response(200)
            self.send_header('Content-Type','application/octet-stream')
            self.send_header('Content-Disposition','attachment; filename="analysis.sapaox"')
            self.end_headers()
            self.wfile.write(payload)
            return
        elif p == '/ao':
            body='<p>가상 AO 연결 확인: SIMULATION 시스템</p>'+link('/prompt','계속')
        elif p == '/prompt':
            body=f'<form action="/refresh"><input type="hidden" name="run" value="{run_id}"><label>달력일<input type="date" name="date" aria-label="달력일" required></label><button>조회</button></form>'
        elif p == '/refresh':
            scene['date']=query.get('date',[''])[0]
            dt.date.fromisoformat(scene['date'])
            scene['polls']=0
            body='<p>조회 요청 접수</p><div id="status">처리 중</div><button id="retry">다시 시도</button>'+f'''<script>
            const poll=async()=>{{let s=await(await fetch('/ao-status{suffix}')).json();document.querySelector('#status').textContent=s.message;document.querySelector('#status').dataset.date=s.date||'';}};
            document.querySelector('#retry').onclick=async()=>{{await fetch('/retry{suffix}',{{method:'POST',headers:{{'X-Sim-Token':'{self.server.token}'}}}});poll();}};
            poll();setInterval(poll,500);</script>'''
        elif p == '/ao-status':
            scene['polls']=scene.get('polls',0)+1
            scenario=scene['scenario']
            if scenario=='unknown_popup':
                message='관리자 설정 변경 필요. 지원 부서에 문의하십시오.'
            elif scenario=='timeout_once' and not scene.get('retried'):
                message='연결 시간이 초과되었습니다. 다시 시도하십시오.'
            elif scene['polls'] < (5 if scenario=='refresh_delay' else 2):
                message='서버에서 조회 처리 중입니다.'
            else:
                message='조회 완료'
            date=scene.get('date','')
            if scenario=='wrong_date' and date:
                date=(dt.date.fromisoformat(date)-dt.timedelta(days=7)).isoformat()
            self.json({'message':message,'date':date if message=='조회 완료' else ''})
            return
        else:
            body='<p>선택한 메뉴가 업무 대상과 다릅니다.</p>'
        self.reply(page('가상 회사 포털',body))

    def do_POST(self):
        if self.headers.get('X-Sim-Token') != self.server.token:
            self.json({'error':'invalid token'},403)
            return
        parsed=urllib.parse.urlparse(self.path)
        query=urllib.parse.parse_qs(parsed.query)
        if parsed.path == '/retry':
            self.server.scene(query['run'][0])['retried']=True
            self.json({'ok':True})
            return
        size=int(self.headers.get('Content-Length','0'))
        if size>200000:
            self.json({'error':'too large'},413)
            return
        try:
            data=json.loads(self.rfile.read(size) or '{}')
            if parsed.path == '/mail':
                if any(not addr.endswith('@example.test') for addr in data['payload']['to']):
                    raise ValueError('테스트 메일 주소만 허용')
                self.server.accept_mail(data['key'],data['payload'])
                if data.get('lose_ack'):
                    self.json({'error':'simulated acknowledgement loss'},503)
                else:
                    self.json({'received':True})
            elif parsed.path == '/start':
                if data.get('scenario') not in SCENARIOS or data.get('mode') not in ['mock','live']:
                    raise ValueError('지원하지 않는 설정')
                dt.date.fromisoformat(data['date'])
                if not self.server.ui_lock.acquire(False):
                    self.json({'status':'BUSY'},409)
                    return
                self.server.last={'status':'RUNNING'}
                def worker():
                    try:
                        from runner import execute
                        self.server.last=execute(self.server,data['scenario'],data['mode'],data['date'],False)
                    except Exception as exc:
                        self.server.last={'status':'FAILED','error':str(exc)}
                    finally:
                        self.server.ui_lock.release()
                threading.Thread(target=worker,daemon=True).start()
                self.json({'status':'RUNNING'})
            else:
                self.json({'error':'not found'},404)
        except Exception as exc:
            self.json({'error':str(exc)},400)


def start_server(port=0,runtime=None):
    server=SimulationServer(port,runtime)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return server
