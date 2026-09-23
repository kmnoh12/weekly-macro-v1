import datetime as dt
import json
import unittest
from pathlib import Path
from decision import validate_answer, DecisionError
from simulator import ROOT, start_server
from runner import execute
from report_table import prepare_report


class Decisions(unittest.TestCase):
    def test_reject_low_probability(self):
        with self.assertRaises(DecisionError):
            validate_answer({'type':'choice','choice':'WAIT','probabilities':{'WAIT':.55,'STOP':.45}},['WAIT','STOP'],{'min_probability':.85,'min_margin':.2})
    def test_reject_invented_action(self):
        with self.assertRaises(DecisionError):
            validate_answer({'type':'choice','choice':'DELETE','probabilities':{'DELETE':1}},['WAIT','STOP'],{'min_probability':.85,'min_margin':.2})


class ReportRows(unittest.TestCase):
    def setUp(self):
        self.cfg={'team':'전력구매팀','sort_column':'4주이상',
                  'delete_columns':['구매부서','생산계획 미확정','계(총계+생산계획 미확정)']}
        self.header=('구매부서','협력사','1주미만','1~2주','2~4주','4주이상','총계',
                     '생산계획 미확정','계(총계+생산계획 미확정)')

    def test_shifted_header_and_variable_row_count(self):
        rows=[('제목',),('조회일','2026-09-20'),(None,),self.header,
              ('전력구매팀','A',1,2,3,7,13,2,15),
              ('기계구매팀','B',3,4,5,99,111,0,111),
              ('전력구매팀','C',2,3,1,12,18,1,19),
              ('전력구매팀 지원','D',1,1,1,88,91,0,91),
              ('결과',None,7,10,10,206,233,3,236)]
        result=prepare_report(rows,self.cfg)
        self.assertEqual(result['source_header_row_index'],3)
        self.assertEqual([row[0] for row in result['rows']],['C','A'])
        self.assertEqual(result['totals'],['결과',3,5,4,19,31])

    def test_unexpected_team_quantity_stops(self):
        rows=[self.header,('전력구매팀','A',1,2,3,'확인필요',13,2,15)]
        with self.assertRaisesRegex(ValueError,'비숫자'):
            prepare_report(rows,self.cfg)


def integration(mode='mock'):
    stamp=dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    server=start_server(runtime=ROOT/'runtime'/'tests'/stamp)
    cases=['normal','menu_changed','refresh_delay','timeout_once','wrong_date','empty','bad_number','unknown_popup','send_ack_lost']
    if mode=='live':
        cases=['menu_changed','timeout_once','unknown_popup']
    expected_fail={'wrong_date':'조회 날짜 불일치','empty':'결과 0건','bad_number':'비숫자','unknown_popup':'Jev 중지 선택'}
    results=[]
    try:
        for case in cases:
            with server.db() as con:
                before_count=con.execute('SELECT COUNT(*) FROM mail').fetchone()[0]
            result=execute(server,case,mode,'2026-09-21')
            expected='FAILED' if case in expected_fail else 'SUCCESS'
            ok=result['status']==expected
            if expected=='SUCCESS' and ok:
                actual=result['result']
                # Independent fixture oracle: three power-team suppliers, sorted counts 12,7,0.
                ok=actual['rows']==[['가상협력사-C',2,3,1,12,18],['가상협력사-A',1,2,3,7,13],['가상협력사-E',0,1,0,0,1]]
                ok=ok and actual['totals']==['결과',3,6,4,19,32]
                repeat=execute(server,case,mode,'2026-09-21')
                ok=ok and repeat['status']=='ALREADY_SENT'
            if expected=='FAILED':
                with server.db() as con:
                    after_count=con.execute('SELECT COUNT(*) FROM mail').fetchone()[0]
                # A failed run has no mail key and no final send event.
                events=(server.runtime/'runs'/result['run_id']/'events.jsonl').read_text(encoding='utf-8')
                ok=ok and 'mail_received' not in events and before_count==after_count
                ok=ok and expected_fail[case] in result.get('error','')
            entry={'case':case,'expected':expected,'actual':result['status'],'pass':ok,'run_id':result.get('run_id'),'error':result.get('error'),'jev_calls':result.get('jev_calls')}
            results.append(entry)
            print(json.dumps(entry,ensure_ascii=False),flush=True)
        skip=execute(server,'normal',mode,'2026-09-22')
        results.append({'case':'non_monday','pass':skip['status']=='SKIPPED'})
        for d in ['2026-01-05','2026-03-02']:
            assert (dt.date.fromisoformat(d)-dt.timedelta(days=1)).weekday()==6
        summary={'mode':mode,'passed':sum(r['pass'] for r in results),'total':len(results),'results':results,'runtime':str(server.runtime)}
        (ROOT/'runtime'/f'test-summary-{mode}.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
        if summary['passed']!=summary['total']:
            raise SystemExit(1)
    finally:
        server.shutdown()


if __name__=='__main__':
    unittest.main()
