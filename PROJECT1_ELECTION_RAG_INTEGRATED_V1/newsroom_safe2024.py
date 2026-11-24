"""Server-rendered 2024 results: no client JavaScript, websocket, chart library or simulation.

This is an ADDITIVE safe entrance for computers where the legacy SPA freezes.
All votes and turnout values are loaded from the existing PostgreSQL adapter,
not from the shipped JSON files when NEWSROOM_DATA_SOURCE=postgres.
"""
from __future__ import annotations

import csv
import html
import io
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response, RedirectResponse, FileResponse
from newsroom import real_data_api as real_api, postgres_data
from newsroom_replay2024 import replay_html, pg_replay_observation
from newsroom_district_explorer2024 import final_summary, district_explorer
from newsroom_visuals2024 import (seat_charts,donut_svg,_legend,seat_semicircle_svg,
        map_html,map_iframe,turnout_regions_html,turnout_crossfilter_html,_winner_margin_chart,STYLE as VISUAL_CSS)
from functools import lru_cache

router=APIRouter()

NAV=[('home','2024 투·개표 상황'),('final','전국 확정 개표'),('district','지역·선거구 탐색'),('pr','비례대표 개표'),
     ('turnout','투표율 분석'),('stats','개표 분석'),('articles','기사 초안·검증'),
     ('qa','RAG 근거 질문'),('cg','방송 CG·대본'),('csv','공식 결과 CSV'),
     ('training','보도자료·학습데이터'),('media','사진·영상 자료')]
CSS=r'''
:root{color-scheme:dark;font-family:"Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif}
*{box-sizing:border-box} body{margin:0;background:#0b1424;color:#edf5ff}
header{height:80px;background:#0f1c30;border-bottom:1px solid #315174;display:flex;align-items:center;justify-content:space-between;padding:0 24px;gap:15px}
header strong{font-size:20px;letter-spacing:1.2px} header small{color:#78b8d7;font-size:11px;letter-spacing:1px}
.hstatus{color:#8ce0b6;background:#143b36;padding:12px 16px;border-radius:9px;font-size:12px}
.layout{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:calc(100vh - 80px)}
nav{padding:24px 12px;background:#101d32;border-right:1px solid #33455f}nav .sidetitle{color:#82a0c7;font-size:11px;letter-spacing:2px;margin:0 14px 15px}
nav a{display:block;color:#c2d6eb;text-decoration:none;padding:13px 15px;margin:3px 0;border-radius:8px;font-size:14px}
nav a:hover{background:#253b53}nav a.active{background:#204567;color:#fff;font-weight:bold;border-left:4px solid #3bd4e6}
nav .extra{border-top:1px solid #35465f;margin-top:22px;padding-top:14px}nav .extra a{font-size:12px;color:#9bb8ce}
main{max-width:1500px;width:100%;padding:28px 32px;margin:0 auto}h1{margin:10px 0 4px;font-size:29px}h2{font-size:20px;margin:0 0 16px}h3{font-size:15px;margin:0 0 12px}
.sub{font-size:13px;color:#9eb6d0}.eyebrow{font-size:11px;color:#43d4e7;letter-spacing:2px;font-weight:bold}
.grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin:22px 0}.metric{border:1px solid #30455f;background:#17283f;border-radius:10px;padding:21px;min-height:135px}
.metric small{display:block;font-size:12px;color:#9bb8d7;margin-bottom:14px}.metric strong{font-size:31px}.metric p{font-size:11px;color:#9bb8d7}
.columns{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px}.panel{background:#101e32;border:1px solid #2e4560;border-radius:10px;padding:22px;margin:12px 0;min-width:0}
a{color:#60dff5}a:focus-visible,button:focus-visible{outline:2px solid #9cefff}button{cursor:pointer}
.btn{display:inline-block;background:#183e5d;border:1px solid #39719b;color:#dff5ff;padding:9px 12px;margin:3px;border-radius:7px;text-decoration:none;font-size:13px}
.btn:hover,.btn.selected{background:#1a8299;color:white}
.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th{color:#a1bfd8;text-align:left;background:#152b44}th,td{padding:10px 12px;border-bottom:1px solid #30425a;vertical-align:top}td.number{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr:hover td{background:#1b3048}.note{font-size:12px;line-height:1.8;color:#a3b9d0}.box-note{background:#132b39;padding:13px;border-left:3px solid #45cfb8;color:#d6ebec;border-radius:4px}
.barrow{display:grid;grid-template-columns:minmax(100px,170px) 1fr 105px;align-items:center;gap:10px;margin:12px 0;font-size:13px}
.track{height:12px;border-radius:5px;background:#29405d;overflow:hidden}.fill{height:100%;background:#4c9bed;border-radius:5px}.barrow b{text-align:right}
.regiongrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.regiongrid a{background:#153951;color:#b8f0fb;text-decoration:none;padding:14px;border-radius:8px;border:1px solid #2b7184;text-align:center;font-size:13px}
.regiongrid a small{display:block;color:#a3b8c6;font-size:11px;padding-top:6px}
input,select{color:#fff;background:#1a3049;border:1px solid #466888;border-radius:6px;padding:10px;font-size:14px;max-width:100%}
input[type=text]{min-width:min(100%,330px)}button[type=submit]{background:#168297;border:0;color:#fff;font-weight:bold;padding:11px 18px;border-radius:6px}
article{line-height:1.85;white-space:pre-wrap;background:#111f31;padding:20px;border:1px solid #36516a;border-radius:9px}
footer{font-size:12px;color:#7f9db7;border-top:1px solid #30445f;margin-top:32px;padding:18px 0}
.gallery{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.gallery img{display:block;width:100%;border-radius:7px}
.latest-media-gallery{grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}
.latest-media-item{margin:0;background:#142b43;border:1px solid #345575;border-radius:12px;overflow:hidden}
.latest-media-item img{width:100%;aspect-ratio:16/9;object-fit:cover;object-position:top;border-radius:0}
.latest-media-item figcaption{padding:13px;display:flex;flex-direction:column;align-items:flex-start;gap:7px;font-size:13px}
.latest-media-item figcaption strong{font-size:14px}.latest-media-item figcaption small{color:#a6c1d7}
@media(max-width:800px){.latest-media-gallery{grid-template-columns:1fr}}

@media(max-width:900px){.layout{grid-template-columns:1fr}nav{border:0;padding:10px;display:flex;flex-wrap:wrap}nav a{padding:8px}nav .sidetitle{width:100%}nav .extra{width:100%}.grid4,.columns{grid-template-columns:repeat(2,minmax(0,1fr))}.regiongrid{grid-template-columns:repeat(3,minmax(0,1fr))}main{padding:20px}}
@media(max-width:530px){.grid4,.columns,.regiongrid,.gallery{grid-template-columns:1fr}.barrow{grid-template-columns:90px 1fr 70px}header{height:auto;padding:14px}}
.vcat-grid{display:flex;flex-wrap:wrap;gap:8px}.vcat-item{min-width:90px;flex:1;display:flex;flex-direction:column;gap:8px;align-items:center;border:1px solid #315875;background:#17354c;padding:12px 6px;border-radius:8px;color:#dbf6ff;cursor:pointer}
.vcat-item span:first-child{font-size:12px}.vcat-item b{font-size:16px}.vcat-line{height:8px;max-width:95%;background:#37bdd3;border-radius:8px}.vcat-item.vcat-dim{opacity:.24}.vcat-item:hover{border-color:#60dff5}
.closest-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.margin-buckets{display:grid;gap:12px}.margin-buckets>div{display:grid;grid-template-columns:140px 1fr 50px;gap:10px;align-items:center}
.margin-bucket-track{height:13px;background:#2c4b60;overflow:hidden;border-radius:11px}.margin-bucket-track i{height:100%;display:block;background:#49cad2}
.pr-standalone>svg{max-height:210px;display:block;margin:auto}@media(max-width:830px){.closest-grid{grid-template-columns:1fr}}

.explore-provinces{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:10px}
.explore-provinces a{border:1px solid #335c75;background:#173b57;border-radius:6px;font-size:12px;text-align:center;text-decoration:none;padding:7px;color:#d3f4fc}
.explore-provinces a.selected,.explore-provinces a:hover{background:#15839c;border-color:#83eaf2;color:white}
.party-sw{display:inline-block;width:11px;height:11px;vertical-align:middle;margin-right:7px;border-radius:3px}
.final-headline{display:flex;align-items:center;flex-wrap:wrap;gap:16px;background:#132c46;border:1px solid #305a73;border-radius:11px;padding:15px 20px;margin:16px 0}
.final-headline .final-badge{font-size:12px;background:#195345;color:#a5f6c7;border-radius:18px;padding:6px 10px}
.final-headline strong{font-size:20px}.final-headline span:last-child{color:#b5d5e6;font-size:13px}
.final-total th,.final-total td{background:#1b3b54;font-weight:bold}
.explore-center{background:#142b44}
@media(max-width:1050px){main{padding:18px 15px}}

'''


def e(value):return html.escape(str(value if value is not None else ''), quote=True)
def n(value):return f'{int(value or 0):,}'
def pp(value):return f'{float(value or 0):.1f}%'
def link(page='home',**args):return '/safe2024?'+urlencode({'page':page,**{k:v for k,v in args.items() if v is not None}})
def barrow(name,value,unit='%',width=None):
    x=float(value or 0); w=max(0,min(100, width if width is not None else x))
    label=f'{x:,.2f}%' if unit=='%' else n(x)+' '+unit
    return f'<div class="barrow"><span>{e(name)}</span><div class="track"><div class="fill" style="width:{w:.2f}%"></div></div><b>{e(label)}</b></div>'
def panel(title,html_body,sub=''):
    return f'<section class="panel"><h2>{e(title)}</h2>'+ (f'<p class="sub">{e(sub)}</p>' if sub else '') +html_body+'</section>'
def table(heads,rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join(f'<th>{e(h)}</th>' for h in heads)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{c}</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def metric(label,value,desc=''):
    return f'<div class="metric"><small>{e(label)}</small><strong>{e(value)}</strong><p>{e(desc)}</p></div>'
def layout(page,title,subtitle,content,status='PostgreSQL DB 조회 성공'):
    menu=''.join(f'<a class="{"active" if page==k else ""}" href="{link(k)}">{e(label)}</a>' for k,label in NAV)
    is_replay = page=='home'
    state_note = '과거 기록 자동 재생 / 실시간 아님' if is_replay else '최종 확정자료 / 실시간 아님'
    eyebrow = '2024 · HISTORICAL REPLAY' if is_replay else '2024 · FINAL RESULTS · SERVER-RENDERED'
    footer_note = '2024년 제22대 총선 당시 확인된 투표율·지역구·비례대표 개표율을 재생합니다. 확인되지 않은 시각은 임의로 만들지 않습니다.' if is_replay else '중앙선거관리위원회 제22대 국회의원선거 최종 개표자료 및 투표율 분석자료 · PostgreSQL 조회 · 기존 모의 개표 미실행'
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Cache-Control" content="no-store"><title>{e(title)} | 22대 총선 데이터 상황실</title><style>{CSS}
{VISUAL_CSS}</style></head>
<body><header><div><strong>▣ 22대 총선 데이터 상황실</strong><br><small>2024년 제22대 국회의원선거 · 과거 기록 재현</small></div><div class="hstatus">● {e(status)} · {e(state_note)}</div></header>
<div class="layout"><nav><p class="sidetitle">BROADCAST DESK</p>{menu}</nav>
<main><div class="eyebrow">{e(eyebrow)}</div><h1>{e(title)}</h1><p class="sub">{e(subtitle)}</p>{content}<footer>{e(footer_note)}</footer></main></div></body></html>'''


@lru_cache(maxsize=1)
def get_data():
    if not postgres_data.active():
        raise HTTPException(503,'PostgreSQL 모드가 아닙니다. RUN_POSTGRES_NEWSROOM.cmd 파일로 실행해 주세요.')
    return real_api.vote_data(),real_api.turnout()


def dashboard(d,t):
    """전국 확정 개표: 확정 254석 지도 + 46석·300석 의석 요약만."""
    return final_summary(d,t)


def districtpage(d,t,region='',district='',area='',q=''):
    """지역·선거구 탐색: 시·도→시·군→실제 선거구→후보별 상세."""
    return district_explorer(d,t,region,district,area,q)


def prpage(d,region='',area=''):
    p=d['proportional']; regions=d['constituency']['regions']; ps=p['nation']; areas=[x for x in p['areas'] if x['region']==region]
    active=next((x for x in areas if x['area']==area),None)
    choices='<a class="btn '+('selected' if not region else '')+'" href="'+link('pr')+'">전국</a>'+''.join(f'<a class="btn '+("selected" if region==x["name"] else "")+'" href="'+link('pr',region=x['name'])+'">'+e(x['name'])+'</a>' for x in regions)
    ph=ps if not region else next((x for x in regions if x['name']==region),None)
    parties=ps['parties'] if not region else (active['parties'] if active else ph['proportional_parties'])
    info='전국 정당별 비례대표 득표율' if not region else region+(' '+area if active else ' 시·도 합계')
    rows=table(['정당','득표수','득표율'],[(e(x['party']),n(x['votes']),f'{x["share"]:.2f}%') for x in parties])
    choices2=''.join(f'<a class="btn '+('selected' if active and active['area']==a['area'] else '')+'" href="'+link('pr',region=region,area=a['area'])+'">'+e(a['area'])+'</a>' for a in areas)
    return panel('비례대표 46석 정당별 구성', '<div class="vis-card pr-standalone">'+donut_svg(sorted(p['seat_allocation'].items(),key=lambda x:-x[1]),46,'비례대표 46석')+_legend(sorted(p['seat_allocation'].items(),key=lambda x:-x[1]))+'</div>')+'<div class="grid4">'+metric('전국 비례대표 유효투표',n(ps['valid']))+metric('정당별 투표수 합계',n(ps['ballots']))+metric('비례대표 의석','46석')+metric('전국 정당 수',n(len(ps['parties'])))+'</div>'+panel('지역 선택',choices)+(panel('구·시·군 선택',choices2) if region else '')+panel(info,rows)


def turnoutpage(t,region=""):
    na=t['national']
    cards='<div class="grid4">'+metric('전국 실제 최종 투표율',pp(na['final']),'선관위 확정 집계')+metric('사전투표율',pp(na['early']),'통합선거인명부 전수조사')+metric('선거일 투표율',pp(t['election_day']['all']),'선거일 대상 표본조사')+metric('비교 대상','17개 시·도','최종 지역별 투표율')+'</div>'
    # Emphasize only selected bar, fade other ages/genders; exact numbers remain visible.
    def category_chart(values,label):
        return '<div class="vcat-grid" aria-label="'+e(label)+'">'+''.join(
          f'<button type="button" class="vcat-item" onclick="document.querySelectorAll(\'.vcat-item\').forEach(e=>e.classList.toggle(\'vcat-dim\',e!==this))"><span>{e(name)}</span><span class="vcat-line" style="width:{max(5,float(v))}%"></span><b>{v:.1f}%</b></button>'
          for name,v in values.items())+'</div>'
    age=panel('연령별 전체 투표율 · 표본조사',category_chart(t['age'],'연령별 전체 투표율'),
              '중앙선관위 1,505개 투표구 표본조사 · 막대를 선택하면 나머지 흐리게 표시')
    sex=panel('성별 전체 투표율 · 표본조사',category_chart(t['sex'],'성별 투표율')+
              '<h3 style="margin-top:20px">성별 사전투표율 · 전수조사</h3>'+category_chart(t['early_sex'],'성별 사전투표율'))
    methods='<p class="box-note">연령·성별 전체 투표율은 표본조사 결과이며 사전투표율은 통합선거인명부 전수조사 결과입니다. 표본조사 투표율 67.2%와 실제 최종 투표율 67.0%는 서로 다른 자료입니다.</p><p><a href="/safe2024/turnout-methodology.pdf" target="_blank">조사방법 확인 (원본 PDF 발췌)</a> · <a href="/api/real/turnout-report.pdf" target="_blank">중앙선관위 원문 PDF 전체</a></p>'
    return cards+panel('전국 시·도별 실제 투표율',turnout_regions_html(t,region))+panel('성별·시도별 투표율 교차 분석 · 표본조사',turnout_crossfilter_html())+'<div class="columns">'+age+sex+'</div>'+panel('조사방법과 분모 확인',methods)


def statspage(d,t):
    districts=d['constituency']['districts']
    margin_ranges=[('1천 표 이하',lambda x:x<=1000),('1천~5천 표',lambda x:1000<x<=5000),
                   ('5천~1만 표',lambda x:5000<x<=10000),('1만 표 초과',lambda x:x>10000)]
    bars='<div class="margin-buckets">'+''.join(f'<div><b>{e(label)}</b><span class="margin-bucket-track"><i style="width:{sum(1 for x in districts if pred(x["margin"]))/254*100:.1f}%"></i></span><strong>{sum(1 for x in districts if pred(x["margin"]))}곳</strong></div>' for label,pred in margin_ranges)+'</div>'
    closest=sorted(districts,key=lambda x:x['margin'])[:12]
    closecharts=''.join('<div class="vis-card"><h4>'+e(x['region']+' '+x['district'])+'</h4>'+_winner_margin_chart(x)+'</div>' for x in closest)
    return seat_charts(d)+panel('지역구 1·2위 득표차 분포',bars)+panel('접전 지역구 12곳 · 실제 후보별 득표수',
        '<div class="closest-grid">'+closecharts+'</div>')+'<p class="note">득표차와 득표수는 2024년 최종 집계만 사용하며 과거 중간 득표수는 생성하지 않습니다.</p>'


def articlepage(d,region='',district=''):
    ds=d['constituency']['districts']; target=next((x for x in ds if x['id']==district),ds[0]); win=target['winner']
    title=f'[검수 전 기사 초안] {target["region"]} {target["district"]} {win["name"]} 후보 당선'
    body=(f'2024년 4월 10일 실시된 제22대 국회의원선거 {target["region"]} {target["district"]} 지역구에서 '
          f'{win["party"]} {win["name"]} 후보가 {n(win["votes"])}표를 얻어 당선됐습니다.\n\n'
          f'해당 후보의 득표율은 유효투표 대비 {win["share"]:.2f}%입니다. 선거구 전체 유효투표는 {n(target["valid"])}표였으며 '
          f'무효투표는 {n(target["invalid"])}표입니다. 1·2위 득표차는 {n(target["margin"])}표입니다.\n\n'
          f'[근거] 중앙선거관리위원회 개표결과.xlsx 지역구 시트 {n(target["excel_row"])}행 · 지역구 ID {target["id"]}\n'
          '[편집 유의] 초안은 자동 생성된 사실 요약입니다. 후보 신상·현장 반응·정치적 의미는 추가 취재 없이 작성하지 않았습니다.')
    choices='<form action="/safe2024" method="get"><input type="hidden" name="page" value="articles"><label>지역구 ID: <select name="district">'+''.join(f'<option value="{e(x["id"])}" '+('selected' if x['id']==target['id'] else '')+'>'+e(x['region']+' '+x['district'])+'</option>' for x in ds)+'</select></label> <button type="submit">기사 초안 생성</button></form>'
    return panel('대상 지역구 선택',choices)+panel(title,'<article>'+e(body)+'</article><p class="note">검수·승인 여부를 기록하지 않습니다. 기존 프로그램의 기사 승인 기능은 원본 화면에 별도 보존되어 있습니다.</p>')


def qapage(app,q=''):
    presets=['전국 투표율은?','사전투표는 전수조사인가요?','20대 남녀 투표율 차이는?','비례대표 의석은 몇 석인가요?']
    input_form=f'<form action="/safe2024" method="get"><input type="hidden" name="page" value="qa"><input type="text" name="q" maxlength="350" value="{e(q)}" placeholder="선관위 개표·투표율 자료에 질문하세요"><button type="submit">자료 검색</button></form>'
    buttons=' '.join(f'<a class="btn" href="{link("qa",q=x)}">{e(x)}</a>' for x in presets)
    result=''
    if q.strip():
        qa_endpoint=next((rt.endpoint for rt in app.routes if getattr(rt,'path',None)=='/api/real/ask'),None)
        if qa_endpoint:
            r=qa_endpoint(q=q[:350],region='',district='',kind='auto')
            proof=''.join(f'<li>{e(x.get("source",x.get("file","근거자료")))} '+(f'<a href="{e(x["url"])}" target="_blank">원문 확인</a>' if x.get('url') else '')+'</li>' for x in r.get('evidence',[]))
            result=panel('자료 확인 결과','<p>'+e(r['answer'])+'</p><h3>출처·근거</h3><ul>'+proof+'</ul><p class="note">'+e(r.get('limitations',''))+'</p>')
    return panel('선거 데이터 근거 검색',input_form+'<h3>예시 질문</h3>'+buttons)+result


def cgpage(d,t):
    seats=d['constituency']['seats_by_party']; p=d['proportional']['seat_allocation'];
    major=[(k,v) for k,v in sorted(seats.items(),key=lambda a:-a[1])[:4]]
    script=(f'2024년 제22대 국회의원선거 최종 개표 결과입니다.\n\n전국 투표율은 {t["national"]["final"]:.1f}%를 기록했습니다. '
            f'지역구 254석과 비례대표 46석을 합쳐 전체 의석은 300석입니다.\n\n'
            + '\n'.join(f'지역구에서 {k}은 {v}석을 확보했습니다.' for k,v in major)
            + '\n\n비례대표 정당별 의석은 '+', '.join(f'{k} {v}석' for k,v in sorted(p.items(),key=lambda a:-a[1]))+'입니다.\n\n'
            '[방송 시 주의] 시각별 개표 중계자료가 아닌 확정 결과만 제시합니다.')
    return panel('실제 2024년 확정 결과 방송 대본', '<article>'+e(script)+'</article>')+panel('원래 교육용 모의 CG·대본 기능','<p>기존 모의 개표 CG·대본 제작 기능은 삭제하지 않았습니다. 별도의 기존 화면에서 이용할 수 있습니다.</p><a class="btn" href="/legacy-newsroom">기존 CG 도구 열기</a>')


def csvpage():
    return panel('PostgreSQL 데이터를 CSV로 내보내기','<p>저장된 SQL의 실제 개표 결과를 CSV로 내보냅니다. 기존 원본 파일은 수정하지 않습니다.</p><p><a class="btn" href="/safe2024/export?kind=district">지역구 전체 후보별 결과 CSV 다운로드</a> <a class="btn" href="/safe2024/export?kind=proportional">비례대표 전국 정당별 결과 CSV 다운로드</a> <a class="btn" href="/safe2024/export?kind=turnout">투표율 분석 항목 CSV 다운로드</a></p><p class="note">성별·연령별 투표율은 표본조사이며 사전투표율은 전수조사입니다. 해당 구분을 CSV 열에 기재합니다.</p>')


def trainingpage():
    return panel('보도자료·학습 데이터','<p>기존 학습 자료 파일 및 실습 데이터는 그대로 보존했습니다.</p><p><a class="btn" href="/static/training/press_sample_DEMO.html">교육용 보도자료 HTML</a> <a class="btn" href="/static/training/press_raw_DEMO.csv">교육용 가상 보도자료 CSV</a> <a class="btn" href="/static/training/lead_draft_UNREVIEWED.jsonl">검수 전 JSONL</a></p><p class="note">이 자료는 교육용 예시이며 실제 언론 보도와 혼동하지 않습니다. 사용자 검수 및 사용 권리 확인 후 활용해야 합니다.</p>')


def mediapage():
    """Only CG illustrations calculated from the current verified NEC dataset."""
    current=[
        ('v5_r3_final_overview.png','전국 확정 개표 · 지역구 및 비례대표 의석 도넛', '2024년 확정 의석수로 제작한 데이터 CG'),
        ('v5_r3_district_detail.png','지역·선거구 탐색 · 수원시정 득표 비교', '실제 후보별 득표수·투표수로 제작한 데이터 CG'),
        ('v5_r3_turnout_analysis.png','투표율 분석 · 17개 시·도 명암 비교 CG', '실제 최종 투표율 · 색상 타일은 지도가 아님'),
        ('v5_r3_count_analysis.png','개표 분석 · 표차가 작은 8개 지역구', '실제 1·2위 득표차로 제작한 데이터 CG'),
        ('v5_r3_replay_13.png','시간대별 투표율 CG · 13시 사전투표 합산 주석', '실제 시간별 발표 투표율로 제작한 데이터 CG'),
        ('v5_r3_replay_final.png','최종 재생 CG · 지역구·비례대표 100% 동시 공개', '10:25 보도 기반 재현 시각 · 확정 의석 300석'),
    ]
    gallery='<div class="gallery latest-media-gallery">'+''.join(
        '<figure class="latest-media-item"><a href="/safe2024/visuals/'+name+'" target="_blank" rel="noopener">'
        '<img loading="lazy" alt="'+e(title)+'" src="/safe2024/visuals/'+name+'"></a>'
        '<figcaption><strong>'+e(title)+'</strong><small>'+e(source)+'</small>'
        '<a class="btn" href="/safe2024/visuals/'+name+'" target="_blank" rel="noopener">큰 화면으로 보기</a></figcaption></figure>'
        for name,title,source in current)+'</div>'
    return (panel('V5 최신 데이터 CG · 6종',gallery,
        '2024년 선관위 확정 개표 및 당시 투표율 기록으로 제작 · 구버전 캡처와 교육용 예시 이미지 제외')
        +'<p class="box-note">실제 선거 데이터로 새로 제작한 정적 CG 이미지이며 웹사이트 화면 전체 캡처는 아닙니다. 동영상은 현재 등록돼 있지 않습니다. '
         '완성된 개표방송 영상이나 방송사 공식 화면으로 오인하지 마세요. 실시간 개표도 아닙니다.</p>')


def errorpage(message):
    return HTMLResponse(layout('home','DB 조회 확인 필요','PostgreSQL 조회 중 문제가 발생했습니다.',f'<section class="panel"><h2>데이터를 표시하지 못했습니다</h2><p>{e(message)}</p><p class="note">PostgreSQL에 직접 연결되는 안전 화면입니다. 오류가 있으면 기존 JSON으로 자동 전환하지 않습니다.</p></section>',status='DB 조회 오류'),status_code=503)


def bind_safe(app):
    @router.get('/safe2024',response_class=HTMLResponse)
    def stable(page:str='home',region:str='',district:str='',area:str='',q:str=''):
        page=page if page in dict(NAV) else 'home'
        if page=='home':
            # Fast first paint: playback comes from a small verified historical archive.
            # It must not block on expensive PostgreSQL reads or launch legacy JS.
            return replay_html(layout)
        if page in ('training','media'):
            body=trainingpage() if page=='training' else mediapage()
            return HTMLResponse(layout(page,dict(NAV)[page],'기존 학습 기능과 자료를 유지한 안정 화면',body,status='기존 자료 보존'))
        try:
            d,t=get_data()
            pages={
                'final':lambda:dashboard(d,t),
                'district':lambda:districtpage(d,t,region,district,area,q),
                'pr':lambda:prpage(d,region,area),
                'turnout':lambda:turnoutpage(t,region),
                'stats':lambda:statspage(d,t),
                'articles':lambda:articlepage(d,region,district),
                'qa':lambda:qapage(app,q),
                'cg':lambda:cgpage(d,t),
                'csv':csvpage,
            }
            body=pages[page]()
        except HTTPException as exc:
            return errorpage(str(exc.detail))
        except Exception:
            # Do not leak OS paths, database passwords or SQL text to browser.
            return errorpage('서버의 자료 처리 오류가 발생했습니다. 실행창의 로그를 확인해 주세요.')
        subtitle=('중앙선거관리위원회 제22대 국회의원선거 최종 집계 · PostgreSQL '+postgres_data.SCHEMA+' 테이블 사용')
        return HTMLResponse(layout(page,dict(NAV)[page],subtitle,body),headers={'Cache-Control':'no-store'})

    @router.get('/safe2024/map',response_class=HTMLResponse)
    def election_map(region:str='',district:str='',mode:str='results',compact:int=0):
        if mode not in {'results','outline'}:raise HTTPException(422,'지원하지 않는 지도 표시 방식')
        if not postgres_data.active():raise HTTPException(503,'PostgreSQL 연결 필요')
        d,_=get_data()
        content=map_html(d,region=region,district=district,mode=mode,embed=bool(compact))
        compact_css=(' .vmap-aside{display:none}.vmap-layout{grid-template-columns:1fr}.vmap-body{padding:5px;border:0}'
                     '.vmap-body h3{display:none}.vmap-back{display:none}' if compact else '')
        if mode=='outline':
            # During the replay no winner names or colors appear in the output.
            content=map_html(d,mode='outline',embed=True)
        return HTMLResponse('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#0c2035;color:#e5f5ff;font-family:Malgun Gothic,Arial,sans-serif;margin:0;padding:8px}'+VISUAL_CSS+compact_css+'</style></head><body>'+content+'</body></html>')

    @router.get('/safe2024/seats-snippet',response_class=HTMLResponse)
    def final_seats_snippet():
        if not postgres_data.active():raise HTTPException(503,'PostgreSQL 연결 필요')
        d,_=get_data()
        return HTMLResponse(seat_charts(d),headers={'Cache-Control':'no-store'})

    @router.get('/safe2024/turnout-methodology.pdf')
    def turnout_method():
        from pathlib import Path
        source=Path(__file__).resolve().parent/'newsroom'/'real_data'/'turnout_methodology_excerpt.pdf'
        if not source.exists():raise HTTPException(404,'조사방법 발췌 PDF가 없습니다.')
        return FileResponse(source,media_type='application/pdf',filename='2024_turnout_methodology.pdf',content_disposition_type='inline')

    @router.get('/safe2024/visuals/{filename}')
    def visual_screenshot(filename:str):
        from pathlib import Path
        permitted={'v5_r3_final_overview.png','v5_r3_district_detail.png','v5_r3_turnout_analysis.png','v5_r3_count_analysis.png','v5_r3_replay_13.png','v5_r3_replay_final.png'}
        if filename not in permitted:raise HTTPException(404,'등록되지 않은 검증 캡처')
        path=Path(__file__).resolve().parent/'screenshots_2024'/filename
        if not path.exists():raise HTTPException(404,'검증 캡처 원본 없음')
        return FileResponse(path,media_type='image/png')

    @router.get('/safe2024/api/replay/{index}')
    def replay_tick(index: int):
        if not postgres_data.active():
            raise HTTPException(503, 'PostgreSQL 연결 모드가 아닙니다.')
        return pg_replay_observation(index)

    @router.get('/safe2024/export')
    def export(kind:str='district'):
        if kind not in {'district','proportional','turnout'}:
            raise HTTPException(422,'지원하지 않는 내보내기 형식입니다.')
        d,t=get_data();buf=io.StringIO(newline='');w=csv.writer(buf)
        if kind=='district':
            w.writerow(['지역구ID','시도','선거구','후보','정당','득표수','득표율_pct','당선여부','원본엑셀행'])
            for x in d['constituency']['districts']:
                for c in x['candidates']:
                    w.writerow([x['id'],x['region'],x['district'],c['name'],c['party'],c['votes'],c['share'],c['name']==x['winner']['name'],x['excel_row']])
        elif kind=='proportional':
            w.writerow(['범위','정당','득표수','득표율_pct'])
            for p in d['proportional']['nation']['parties']:w.writerow(['전국',p['party'],p['votes'],p['share']])
        else:
            w.writerow(['자료구분','항목','비율_pct','집계방식'])
            for name,value in t['age'].items():w.writerow(['연령별 전체 투표율',name,value,'표본조사'])
            for name,value in t['sex'].items():w.writerow(['성별 전체 투표율',name,value,'표본조사'])
            for name,value in t['early_age'].items():w.writerow(['연령별 사전투표율',name,value,'전수조사'])
            for name,value in t['early_sex'].items():w.writerow(['성별 사전투표율',name,value,'전수조사'])
            for name,value in t['region_actual'].items():w.writerow(['시도별 실제 투표율',name,value,'실제 집계'])
            for name,value in t['region_sample'].items():w.writerow(['시도별 표본 투표율',name,value,'표본조사'])
        name=f'election2024_{kind}_postgres.csv'
        return Response('\ufeff'+buf.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{name}"','Cache-Control':'no-store'})

    app.include_router(router)

    # In PostgreSQL mode, the plain host root should not launch the legacy
    # browser-heavy SPA. Keep that SPA intact and reachable at /legacy-newsroom.
    @app.get('/legacy-newsroom')
    def legacy_newsroom():
        return FileResponse(real_api.ROOT/'static'/'index.html')

    @app.middleware('http')
    async def stable_pg_home(request, call_next):
        if postgres_data.active() and request.url.path=='/':
            return RedirectResponse('/safe2024', status_code=302)
        return await call_next(request)
