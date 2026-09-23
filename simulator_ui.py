"""Screenshot-informed local mock of the portal and native AO dialogs.

The reference screenshots are intentionally not bundled with this repository.
This UI is a visual test fixture, not a selector map for the company website.
"""
import html


CSS = """<style>
*{box-sizing:border-box}body{margin:0;font:16px Arial,'Malgun Gothic',sans-serif;color:#252525;background:#fff}
a{color:inherit;text-decoration:none}button,input{font:inherit}button{cursor:pointer}
.sim-label{position:fixed;bottom:10px;right:12px;z-index:100;background:#fff4ce;color:#664500;
border:1px solid #d8b862;border-radius:4px;padding:5px 9px;font-size:12px;box-shadow:0 2px 8px #0002}
.hope-top{height:82px;background:#240080;color:white;display:flex;align-items:center;gap:38px;padding:0 6%}
.hope-logo{font:700 34px Georgia,serif;letter-spacing:1px;margin-right:2px}.hope-top a{font-weight:700;white-space:nowrap}
.hope-hero{display:grid;grid-template-columns:minmax(400px,39%) 1fr;min-height:530px;background:#f4f1ff}
.hope-message{background:#250080;color:#fff;padding:45px 8%;font-size:27px;font-weight:700;line-height:1.45}
.hope-message small{display:block;margin-top:24px;font-size:15px;font-weight:400;line-height:2}
.hope-board{background:#fff;margin:0;padding:42px 4%;}.hope-board h3{font-size:20px}
.hope-board .board-box{border:1px solid #dedee4;padding:20px;line-height:2.8;font-weight:700}
.systems-title{padding:13px 18px;border-bottom:1px solid #e6e6e6;font-weight:700}
.systems-tabs{padding:18px;border-bottom:1px solid #eee}.systems-tabs b{margin-right:38px}
.systems-layout{display:grid;grid-template-columns:370px 1fr;gap:18px;padding:0 18px}
.systems-side,.systems-panel{border:1px solid #e9e9e9;padding:20px;margin-top:0;min-height:270px}
.systems-side p{margin:21px 0}.systems-panel h3{font-size:17px;margin:5px 0 22px}
.systems-grid{display:grid;grid-template-columns:repeat(3,240px);gap:22px 0}
.systems-grid a{font-weight:600}.star{color:#ff883b;font-size:22px;margin-right:8px}
.bi-head{height:87px;display:flex;align-items:center;gap:20px;padding:0 12px;background:#fff;font-weight:700}
.bi-logo{font-family:Georgia,serif;font-size:23px;color:#142d8c}.bi-logo small{font:700 11px Arial;margin-left:8px}
.bi-mark{border-left:1px solid #ddd;padding-left:14px;color:#0c1b77}
.bi-switch{background:#5b58d9;color:white;border-radius:20px;padding:7px 15px;font-size:14px}
.bi-nav{height:40px;background:#060b75;display:flex;align-items:stretch;color:#fff;font-size:19px;font-weight:700}
.bi-nav a{padding:7px 16px;min-width:74px;text-align:center}.bi-nav a.active,.bi-nav a:hover{background:#514dd1}
.purchase-menu{position:absolute;top:127px;left:220px;width:180px;background:#fff;border:1px solid #172586;box-shadow:0 5px 10px #0002;z-index:2}
.purchase-menu a{display:block;padding:9px 12px}.purchase-menu a:hover,.cube-menu a:hover{background:#eceeff}
.bi-canvas{min-height:calc(100vh - 127px);background:#fff;position:relative;overflow:hidden}
.bi-tab{position:absolute;top:9px;left:12px;padding:9px 14px;background:#6365dc;color:#fff;font-size:13px}
.bi-cards{display:flex;gap:18px;padding:55px 62px}.bi-card{height:196px;min-width:245px;border:1px solid #adbbff;border-radius:8px;background:#f0f2ff;padding:50px 18px}
.bi-card:after{content:'';display:block;height:80px;background:#fff;border-radius:9px}
.cube-button{position:absolute;right:0;top:0;width:69px;height:40px;background:#5751d4;color:#fff;text-align:center;font-size:26px;line-height:40px}
.cube-menu{position:absolute;right:9px;top:40px;width:242px;background:white;border:1px solid #1b2689;box-shadow:0 4px 10px #0002;z-index:3}
.cube-menu a{display:block;padding:10px 12px;font-size:15px;white-space:nowrap}
.native-back{min-height:100vh;background:#e6ebf1;display:flex;align-items:center;justify-content:center;padding:20px}
.native-dialog{background:#fff;border:1px solid #969da5;box-shadow:0 14px 45px #0003;color:#252525}
.native-title{height:33px;padding:6px 12px;border-bottom:1px solid #ddd;font-size:14px}
.trust-dialog{width:600px;min-height:220px}.trust-content{display:flex;gap:45px;padding:25px 45px}.trust-content strong{font-size:20px;letter-spacing:3px}
.trust-content p{line-height:1.4}.native-actions{text-align:right;padding:10px 14px}.native-actions a,.native-actions button{
display:inline-block;min-width:90px;background:#f4f4f4;border:1px solid #999;padding:5px 15px;margin-left:8px;text-align:center;color:#222}
.prompt-dialog{width:1090px;max-width:100%}.prompt-head{padding:7px 13px;background:#f4f8fc;border-bottom:1px solid #b8c6d3;font-weight:700}
.prompt-layout{display:grid;grid-template-columns:315px 1fr;min-height:360px}.prompt-side{border-right:1px solid #bdd0e0;padding:14px;background:#fcfdff;line-height:2.1;font-size:14px}
.prompt-side .selected{background:#c8e3ff}.prompt-fields{padding:14px 18px}.prompt-fields h4{margin:0 0 10px}
.prompt-row{display:grid;grid-template-columns:150px 1fr;align-items:center;min-height:39px;font-size:14px}
.prompt-row input{height:25px;border:1px solid #aebdcc;padding:2px 5px;width:70%}.prompt-row input[type=date]{width:80%}
.prompt-row.required label:before{content:'* ';color:#333}.prompt-foot{border-top:1px solid #d8e1e8;background:#f8f8f8;padding:5px 10px;text-align:right}
.prompt-foot button{padding:4px 22px;margin-left:8px}
@media(max-width:800px){.hope-top{gap:13px;padding:0 15px}.hope-logo{font-size:23px}.hope-hero{grid-template-columns:1fr}
.systems-layout{grid-template-columns:1fr}.systems-grid{grid-template-columns:repeat(2,1fr)}.bi-nav{overflow:auto}.bi-cards{padding-left:15px}}
</style>"""


def shell(title, body):
    return ('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title>'+CSS+
            '<div class="sim-label">화면 재현용 시뮬레이터 · 실제 회사 접속 아님</div>'+body+'</html>')


def portal(suffix):
    nav=''.join(f'<a href="/systems{suffix}">{item}</a>' for item in ['메일','결재','게시판','일정','HiCloud','업무시스템','IT 서비스 요청','HCP'])
    body=('<div class="hope-top"><div class="hope-logo">HYOSUNG</div>'+nav+'</div>'
          '<div class="hope-hero"><div class="hope-message">지속가능한 미래를 만들어가는<br>ESG 경영'
          '<small>• 함께 사는 사회를 위한 사회 공헌 활동<br>• 더 나은 일터를 위한 행복하고 안전한 근무 환경<br>• 환경 친화적 공정 개발</small></div>'
          '<div class="hope-board"><h3>📢 &nbsp; Happy Day 실시 안내</h3><div class="board-box">그룹 게시판<hr>'
          '그룹 공지사항 &nbsp; 경영 메시지 &nbsp; 경조사 &nbsp; 통통게시판</div></div></div>')
    return shell('업무 포털',body)


def systems(suffix):
    entries=['SAP','Power BI','CRM','SRM','QMS','통합계정관리(IAM)','IT 서비스 요청','(구) SAP(ECC)']
    grid=''.join(f'<a href="/{"bi" if item=="Power BI" else "wrong"}{suffix}" aria-label="{item}"><span class="star">★</span>{item}</a>' for item in entries)
    body=('<div class="systems-title">업무시스템</div><div class="systems-tabs"><b>시스템별</b> 업무별</div>'
          '<div class="systems-layout"><div class="systems-side">'
          '<p>▸ &nbsp; 중공업 차세대시스템</p><p>▸ &nbsp; 중공업 Legacy 시스템</p><p>▸ &nbsp; 건설</p>'
          '<p>▸ &nbsp; HIFOS 메뉴 (Legacy)</p><p>▸ &nbsp; 차세대 시스템 운영자 연락처</p></div>'
          '<div class="systems-panel"><h3>중공업 차세대시스템</h3><div class="systems-grid">'+grid+'</div></div></div>')
    return shell('업무시스템',body)


def bi(suffix, stage, menu_changed=False):
    tabs=['종합','영업','설계','구매','생산','재고','품질','프로젝트','안전','스마트팩토리']
    nav=''.join(f'<a href="/{"purchase" if item=="구매" else "wrong"}{suffix}" class="{"active" if item=="구매" and stage=="purchase" else ""}">{item}</a>' for item in tabs)
    top=('<div class="bi-head"><span class="bi-logo">H <small>HEAVY INDUSTRIES</small></span>'
         '<span class="bi-mark">BI Portal</span><span class="bi-switch">중공업</span> 건설</div>'
         '<div class="bi-nav">'+nav+'</div>')
    if stage=='purchase':
        body=('<div class="purchase-menu"><a href="/wrong'+suffix+'">구매실적감현황</a>'
              '<a href="/wrong'+suffix+'">글로벌 소싱 및 절감현황</a>'
              '<a href="/wrong'+suffix+'">개발구매 현황</a>'
              '<a href="/wrong'+suffix+'">수입부대비 현황</a>'
              '<a href="/delivery'+suffix+'">납기 현황</a>'
              '<a href="/wrong'+suffix+'">협력사 현황</a></div>')
    elif stage in ('delivery','cube'):
        cards=''.join('<div class="bi-card"></div>' for _ in range(7))
        body='<div class="bi-canvas"><div class="bi-tab">납기 현황 &nbsp; ×</div><a class="cube-button" href="/cube'+suffix+'" aria-label="정육면체 분석 메뉴">◇</a><div class="bi-cards">'+cards+'</div>'
        if stage=='cube':
            target='생산계획별 납기 초과 미입고 현황' if menu_changed else '납기경과 미입고_생산계획구분'
            items=['납기준수율','비전전PO점유율','자재적기발주율','사내조달LT추이',target,'납품완료율_PJT기준','납품완료율_자재기준']
            body+='<div class="cube-menu">'+''.join('<a href="/'+('download' if item==target else 'wrong')+suffix+'">'+html.escape(item)+'</a>' for item in items)+'</div>'
        body+='</div>'
    else:
        body='<div class="bi-canvas"></div>'
    return shell('BI Portal',top+body)


def trust(suffix):
    body=('<div class="native-back"><div class="native-dialog trust-dialog"><div class="native-title">시스템에 대한 비보안 연결: HWP</div>'
          '<div class="trust-content"><div>⚠</div><div><strong>비보안 연결</strong><p>설정하려는 시스템 "HWP"에 대한 연결이 안전하지 않습니다. 계속하시겠습니까?</p></div></div>'
          '<div class="native-actions"><a href="/prompt'+suffix+'">계속</a><a href="/wrong'+suffix+'">취소</a></div></div></div>')
    return shell('시스템 연결',body)


def prompt(suffix, company='H904', pu='410', scale='1'):
    fields=[('달력일','date','date','',False),('회사코드(Auth)','company','text',company,True),
            ('PU(Auth)','pu','text',pu,True),('구매부서','department','text','',False),
            ('스케일(수량)','scale','text',scale,True),('구매 그룹','group','text','',False),
            ('지연일구분','delay','text','',False)]
    rows=''.join('<div class="prompt-row'+(' required' if required else '')+'"><label for="'+key+'">'+label+'</label>'
                 '<input id="'+key+'" name="'+key+'" type="'+kind+'" value="'+html.escape(value)+'" '
                 +('required ' if required or key=='date' else '')+'aria-label="'+label+'"></div>'
                 for label,key,kind,value,required in fields)
    side='<div class="prompt-side"><b>프롬프트 요약</b><div class="selected">달력일</div>회사코드(Auth)<br>PU(Auth)<br>구매부서<br>스케일(수량)<br>구매 그룹<br>지연일구분</div>'
    body=('<div class="native-back"><div class="native-dialog prompt-dialog"><div class="native-title">프롬프트</div>'
          '<div class="prompt-head">변형 사용 &nbsp; ▭</div><form action="/refresh"><input type="hidden" name="run" value="'+html.escape(suffix.split('=')[-1])+'">'
          '<div class="prompt-layout">'+side+'<div class="prompt-fields"><h4>프롬프트 값 지정</h4>'+rows+'</div></div>'
          '<div class="prompt-foot"><button type="submit">확인</button><button type="button">취소</button></div></form></div></div>')
    return shell('AO 프롬프트',body)
