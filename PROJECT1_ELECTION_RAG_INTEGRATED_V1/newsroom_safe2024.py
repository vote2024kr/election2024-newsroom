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
from newsroom_election_map import election_result_map, map_frame
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
@media(max-width:900px){.layout{grid-template-columns:1fr}nav{border:0;padding:10px;display:flex;flex-wrap:wrap}nav a{padding:8px}nav .sidetitle{width:100%}nav .extra{width:100%}.grid4,.columns{grid-template-columns:repeat(2,minmax(0,1fr))}.regiongrid{grid-template-columns:repeat(3,minmax(0,1fr))}main{padding:20px}}
@media(max-width:530px){.grid4,.columns,.regiongrid,.gallery{grid-template-columns:1fr}.barrow{grid-template-columns:90px 1fr 70px}header{height:auto;padding:14px}}
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
    footer_note = '확인된 과거 시점의 투표율·전국 지역구 개표율을 재생합니다. 브라우저의 작은 시간재생 기능만 사용하며 모의개표 프로그램은 실행하지 않습니다.' if is_replay else '중앙선거관리위원회 제22대 국회의원선거 최종 개표자료 및 투표율 분석자료 · PostgreSQL 조회 · 기존 모의 개표 미실행'
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Cache-Control" content="no-store"><title>{e(title)} | 22대 총선 데이터 상황실</title><style>{CSS}</style></head>
<body><header><div><strong>▣ 22대 총선 데이터 상황실</strong><br><small>2024년 제22대 국회의원선거 · 과거 기록 재현</small></div><div class="hstatus">● {e(status)} · {e(state_note)}</div></header>
<div class="layout"><nav><p class="sidetitle">BROADCAST DESK</p>{menu}</nav>
<main><div class="eyebrow">{e(eyebrow)}</div><h1>{e(title)}</h1><p class="sub">{e(subtitle)}</p>{content}<footer>{e(footer_note)}</footer></main></div></body></html>'''


@lru_cache(maxsize=1)
def get_data():
    if not postgres_data.active():
        raise HTTPException(503,'PostgreSQL 모드가 아닙니다. RUN_POSTGRES_NEWSROOM.cmd 파일로 실행해 주세요.')
    return real_api.vote_data(),real_api.turnout()


def dashboard(d,t):
    s,p=d['constituency'],d['proportional']
    top=sorted(s['seats_by_party'].items(),key=lambda kv:-kv[1])
    seats=panel('지역구 당선 의석 (254석)', ''.join(barrow(name,v,'석',v/161*100) for name,v in top))
    prseats=panel('비례대표 배분 의석 (46석)',''.join(barrow(name,v,'석',v/18*100) for name,v in sorted(p['seat_allocation'].items(),key=lambda kv:-kv[1])))
    regions='<div class="regiongrid">'+''.join(f'<a href="{link("district",region=r["name"])}">{e(r["name"])}<small>{r["district_count"]}개 지역구 →</small></a>' for r in s['regions'])+'</div>'
    cards='<div class="grid4">'+metric('전국 개표 완료','100%','2024년 4월 10일 최종 집계')+metric('지역구','254석','지역구 254개 선거구')+metric('비례대표','46석',f'전국 비례대표 투표 {n(p["nation"]["ballots"])}표')+metric('전국 최종 투표율',pp(t['national']['final']),'전체 선거인 기준 · 실제 집계')+'</div>'
    return cards+'<div class="columns">'+seats+prseats+'</div>'+panel('전국 254개 지역구 확정 결과 지도',map_frame(885))+ '<p class="box-note">이 화면에는 시각별 실시간 개표 기록이 없습니다. 최종 개표 결과만 표시합니다. 2024년 실제 득표 자료와 기존 교육용 가상 개표는 섞이지 않습니다.</p>'


def districtpage(d,region='',district=''):
    ds=d['constituency']['districts'];regions=d['constituency']['regions'];filtered=[x for x in ds if not region or x['region']==region]
    if not filtered:filtered=ds;region=''
    active=next((x for x in filtered if x['id']==district),filtered[0])
    opts='<a class="btn '+('selected' if not region else '')+'" href="'+link('district')+'">전국</a>'+''.join('<a class="btn '+('selected' if region==x['name'] else '')+'" href="'+link('district',region=x['name'])+'">'+e(x['name'])+'</a>' for x in regions)
    lst=table(['시·도','지역구','당선 후보','정당','득표율','상세'],[(e(x['region']),e(x['district']),e(x['winner']['name']),e(x['winner']['party']),pp(x['winner']['share']),f'<a href="{link("district",region=x["region"],district=x["id"])}">보기</a>') for x in filtered])
    votes=table(['후보','정당','득표수','득표율'],[(e(c['name']),e(c['party']),n(c['votes']),f'{c["share"]:.2f}%') for c in active['candidates']])
    detail=panel(f'{active["region"]} {active["district"]} · 최종 개표',f'<p class="box-note">당선: <b>{e(active["winner"]["name"])} ({e(active["winner"]["party"])})</b> · 최종 득표 {n(active["winner"]["votes"])}표 · 1·2위 격차 {n(active["margin"])}표</p>'+votes+f'<p class="note">유효투표 {n(active["valid"])}표 · 무효투표 {n(active["invalid"])}표 · 선관위 개표결과.xlsx 지역구 시트 {n(active["excel_row"])}행</p>')
    return panel('지역 선택',opts)+detail+panel(f'지역구 전체 목록 · {len(filtered)}개',lst)


def prpage(d,region='',area=''):
    p=d['proportional']; regions=d['constituency']['regions']; ps=p['nation']; areas=[x for x in p['areas'] if x['region']==region]
    active=next((x for x in areas if x['area']==area),None)
    choices='<a class="btn '+('selected' if not region else '')+'" href="'+link('pr')+'">전국</a>'+''.join(f'<a class="btn '+("selected" if region==x["name"] else "")+'" href="'+link('pr',region=x['name'])+'">'+e(x['name'])+'</a>' for x in regions)
    ph=ps if not region else next((x for x in regions if x['name']==region),None)
    parties=ps['parties'] if not region else (active['parties'] if active else ph['proportional_parties'])
    info='전국 정당별 비례대표 득표율' if not region else region+(' '+area if active else ' 시·도 합계')
    rows=table(['정당','득표수','득표율'],[(e(x['party']),n(x['votes']),f'{x["share"]:.2f}%') for x in parties])
    choices2=''.join(f'<a class="btn '+('selected' if active and active['area']==a['area'] else '')+'" href="'+link('pr',region=region,area=a['area'])+'">'+e(a['area'])+'</a>' for a in areas)
    return '<div class="grid4">'+metric('전국 비례대표 유효투표',n(ps['valid']))+metric('정당별 투표수 합계',n(ps['ballots']))+metric('비례대표 의석','46석')+metric('전국 정당 수',n(len(ps['parties'])))+'</div>'+panel('지역 선택',choices)+(panel('구·시·군 선택',choices2) if region else '')+panel(info,rows)


def turnoutpage(t):
    na=t['national'];cards='<div class="grid4">'+metric('전국 실제 최종 투표율',pp(na['final']),'실제 집계')+metric('전국 표본 투표율',pp(na['sample']),'전체 선거인 10.1% 표본')+metric('사전투표율',pp(na['early']),'통합선거인명부 전수조사')+metric('선거일 투표율',pp(t['election_day']['all']),'선거일 투표 대상 표본 기준')+'</div>'
    panels=panel('연령별 전체 투표율 · 표본조사',''.join(barrow(a,v) for a,v in t['age'].items()),'1,505개 투표구 표본조사 · 선관위 PDF 인쇄 23쪽')+panel('성별 전체 투표율 · 표본조사',''.join(barrow(a,v) for a,v in t['sex'].items())+'<h3>사전투표율 · 전수조사</h3>'+''.join(barrow(a,v) for a,v in t['early_sex'].items()))
    region=panel('시·도별 전체 투표율',table(['시·도','실제 투표율','표본 투표율','사전투표율'],[(e(name),pp(v),pp(t['region_sample'].get(name)),pp(t['region_early'].get(name))) for name,v in t['region_actual'].items()]))
    methods='<p class="box-note">연령·성별 전체 투표율은 표본조사 결과이며 사전투표율은 통합선거인명부 전수조사 결과입니다. 표본조사 투표율 67.2%와 실제 최종 투표율 67.0%는 서로 다른 자료입니다.</p><p><a href="/safe2024/turnout-methodology.pdf" target="_blank" rel="noopener noreferrer">조사방법 확인</a></p><p><a href="/api/real/turnout-report.pdf" target="_blank">선관위 「제22대 국회의원선거 투표율 분석」 PDF 원문</a></p>'
    return cards+turnout_cross()+'<div class="columns">'+panels+'</div>'+region+panel('자료의 분모와 조사 방법',methods)


def turnout_cross():
    cross = """<style>
    .cross-guide{font-size:13px;color:#b4cbdc;line-height:1.7;margin:0 0 12px}
    .cross-toolbar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin-bottom:15px}
    .cross-toolbar button{border:1px solid #4787aa;color:#e1faff;background:#194660;border-radius:6px;padding:8px 12px}
    .cross-toolbar button:disabled{opacity:.4;cursor:default}
    .cross-grid{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(270px,1fr);gap:14px}
    .cross-box{background:#102238;border:1px solid #34536e;border-radius:9px;padding:17px;min-width:0}
    .cross-box h3{font-size:15px;margin:0 0 12px}
    .cross-reg-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
    .cross-reg-item{min-width:0}
    .cross-reg-btn{width:100%;text-align:left;color:#e3f5ff;background:#182d47;border:1px solid #2d4a65;border-radius:6px;padding:6px 8px;cursor:pointer}
    .cross-reg-btn:hover,.cross-reg-btn.is-selected{outline:2px solid #60dff5;background:#204b60}
    .cross-reg-name{display:block;font-size:12px;margin-bottom:4px}
    .cross-reg-contents{display:flex;flex-direction:column;gap:3px}
    .cross-reg-bar{height:19px;border-radius:3px;position:relative;min-width:56px;display:block}
    .cross-reg-bar span{display:block;white-space:nowrap;color:#fff;font-size:11px;line-height:19px;padding-left:6px;text-shadow:0 1px 2px #001}
    .is-male{background:#1877da}.is-female{background:#db6643}
    .cross-sex-btn{display:grid;grid-template-columns:35px 1fr 65px;align-items:center;gap:8px;width:100%;padding:11px;background:#182d47;border:1px solid #344c66;border-radius:6px;color:white;margin-bottom:9px;cursor:pointer;text-align:left}
    .cross-sex-btn.is-selected,.cross-sex-btn:hover{outline:2px solid #60dff5}
    .cross-sex-track{height:16px;overflow:hidden;border-radius:3px;background:#2b4057}
    .cross-sex-fill{display:block;height:100%}
    .cross-sex-btn strong{text-align:right;font-size:14px}
    .cross-status{background:#142e41;padding:11px;border-radius:5px;color:#c9e6ee;line-height:1.6;font-size:13px}
    .cross-source{margin-top:14px;font-size:12px;color:#acc3dc}
    @media(max-width:850px){.cross-grid{grid-template-columns:1fr}}
    @media(max-width:550px){.cross-reg-list{grid-template-columns:1fr}}
    </style>
    <section class="panel" data-turnout-crossfilter>
      <h2>지역·성별 투표율 교차 분석</h2>
      <p class="cross-guide">지역 또는 성별 그래프의 막대를 클릭하면 다른 그래프도 함께 변경됩니다. 원자료: 전체 선거인 표본조사(전국 1,505개 투표구).</p>
      <div class="cross-toolbar"><strong id="cross-selection">지역: 전체 · 성별: 전체</strong><button type="button" id="cross-reset" disabled>선택 초기화</button></div>
      <div class="cross-grid">
        <div class="cross-box"><h3>시·도별 남녀 투표율 비교</h3><p class="note">지역을 클릭하면 오른쪽에 해당 지역 남녀 투표율이 표시됩니다.</p><div id="cross-region-bars" class="cross-reg-list" aria-label="시도별 성별 투표율"></div></div>
        <div class="cross-box"><h3 id="cross-sex-title">전국 성별 투표율</h3><p class="note">남성 또는 여성 막대를 클릭하면 왼쪽 지역별 자료가 해당 성별로 바뀝니다.</p><div id="cross-sex-bars" aria-label="남녀 투표율"></div><p id="cross-message" class="cross-status" aria-live="polite">원본 데이터를 불러오는 중입니다.</p></div>
      </div>
      <p class="cross-source">자료: 중앙선관위 「제22대 국회의원선거 투표율 분석」 인쇄 29쪽(그림 15) · <a href="/api/real/turnout-report.pdf#page=37" target="_blank" rel="noopener noreferrer">원자료 확인</a><br>지역별 최종 확정 투표율과 표본조사의 성별 투표율은 집계 방식이 다르므로 서로 합산하지 않습니다.</p>
    </section>
    <script src="/static/turnout_crossfilter_2024.js" defer></script>"""
    return cross


def statspage(d,t):
    # Only actual vote-count results belong in the election counting analysis.
    # Turnout's region/sex crossfilter lives exclusively in turnoutpage().
    districts=d['constituency']['districts']
    seats=d['constituency']['seats_by_party']
    pr=d['proportional']['seat_allocation']
    major=sorted(seats.items(),key=lambda kv:-kv[1])
    cons=panel('지역구 정당별 의석 비교 · 총 254석',
        ''.join(barrow(k,v,'석',v/254*100) for k,v in major))
    prop=panel('비례대표 정당별 의석 비교 · 총 46석',
        ''.join(barrow(k,v,'석',v/46*100) for k,v in sorted(pr.items(),key=lambda kv:-kv[1])))
    close=[('1,000표 이하',lambda x:x<=1000),('1,001~5,000표',lambda x:1000<x<=5000),
           ('5,001~10,000표',lambda x:5000<x<=10000),('10,000표 초과',lambda x:x>10000)]
    margin=panel('지역구별 1·2위 득표차 분포 (254개 지역구)',
        ''.join(barrow(label,sum(1 for x in districts if f(x['margin'])),'곳',
                       sum(1 for x in districts if f(x['margin']))/254*100)
                for label,f in close))
    tight=sorted(districts,key=lambda x:x['margin'])[:12]
    closest=panel('득표차가 작은 지역구 12곳',
        table(['지역구','당선인','당선 정당','1·2위 득표차'],
              [(e(x['region']+' '+x['district']),e(x['winner']['name']),
                e(x['winner']['party']),n(x['margin'])+'표') for x in tight]))
    return '<div class="columns">'+cons+prop+'</div>'+margin+closest+'<p class="note">모든 개표 데이터는 선관위 최종 결과입니다. 실시간 개표 중간 후보 득표수는 포함하지 않습니다.</p>'


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
    # Existing screenshots of the project's real-data dashboard; not fictional
    # polling-place photographs and not videos.
    media=[
        ('dashboard_actual.png','2024년 실제 개표 결과 화면','실제 확정 개표 데이터로 구성한 프로젝트 대시보드'),
        ('analytics_actual.png','투표율 분석 화면','중앙선관위 원자료 기반 통계 분석 결과'),
        ('district_actual.png','지역구 개표 결과 화면','실제 선거구별 후보 및 득표 자료 조회 화면'),
        ('articles_actual.png','근거 기반 기사 초안 화면','확정 결과에 대한 검수 전 기사 작성 화면'),
    ]
    cards=''.join(
        f'<div class="panel" style="margin:0"><a href="/safe2024/visuals/{filename}" target="_blank" rel="noopener noreferrer"><img alt="{e(label)}" src="/safe2024/visuals/{filename}" loading="lazy" style="width:100%;height:auto;border-radius:7px"></a><h3 style="margin-top:13px">{e(label)}</h3><p class="note">{e(desc)}</p><p><a href="/safe2024/visuals/{filename}" target="_blank" rel="noopener noreferrer">원본 이미지 열기</a></p></div>'
        for filename,label,desc in media)
    return panel('선거 데이터 시각자료','<p class="note">프로젝트의 실제 선거 데이터 화면 캡처입니다. 개표 현장을 촬영한 사진은 아니며 출처 및 이용권한이 확인되지 않은 현장 사진은 포함하지 않았습니다.</p><div class="gallery" style="grid-template-columns:repeat(auto-fit,minmax(260px,1fr))">'+cards+'</div><p class="note">영상은 추후 제작 후 추가합니다. 기존 교육용 이미지 파일은 삭제하지 않고 프로젝트 내부에 보존했습니다.</p>')


def errorpage(message):
    return HTMLResponse(layout('home','DB 조회 확인 필요','PostgreSQL 조회 중 문제가 발생했습니다.',f'<section class="panel"><h2>데이터를 표시하지 못했습니다</h2><p>{e(message)}</p><p class="note">PostgreSQL에 직접 연결되는 안전 화면입니다. 오류가 있으면 기존 JSON으로 자동 전환하지 않습니다.</p></section>',status='DB 조회 오류'),status_code=503)


@lru_cache(maxsize=1)
def extract_methodology_pdf():
    """Original NEC turnout-analysis PDF pages 12-14, not the 190-page original."""
    from pypdf import PdfReader, PdfWriter
    source=real_api.DATA/'turnout_report_2024.pdf'
    reader=PdfReader(str(source))
    if len(reader.pages)<14:
        raise ValueError('원본 PDF에서 조사방법 12~14페이지를 확인할 수 없습니다.')
    writer=PdfWriter()
    for page_index in (11,12,13):
        writer.add_page(reader.pages[page_index])
    out=io.BytesIO()
    writer.write(out)
    return out.getvalue()


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
                'district':lambda:districtpage(d,region,district),
                'pr':lambda:prpage(d,region,area),
                'turnout':lambda:turnoutpage(t),
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
    def final_map(region:str='',district:str=''):
        if not postgres_data.active():
            raise HTTPException(503,'최종 개표 지도는 PostgreSQL 연결이 필요합니다.')
        try:
            data=real_api.vote_data()
            return HTMLResponse(election_result_map(data,region,district))
        except ValueError as exc:
            raise HTTPException(503,'선거구 경계와 실제 개표자료 연결을 확인해 주세요.') from exc

    @router.get('/safe2024/visuals/{filename}')
    def existing_visual(filename: str):
        allowed={'dashboard_actual.png','analytics_actual.png','district_actual.png','articles_actual.png'}
        if filename not in allowed:
            raise HTTPException(404,'등록된 선거 시각자료가 아닙니다.')
        return FileResponse(real_api.ROOT.parent/'screenshots_2024'/filename,media_type='image/png',headers={'Cache-Control':'public, max-age=3600'})

    @router.get('/safe2024/turnout-methodology.pdf')
    def methodology_pdf():
        """Serve only source PDF pages 12-14 (report printed pages 4-6)."""
        try:
            content=extract_methodology_pdf()
        except (OSError, ValueError, ImportError) as exc:
            raise HTTPException(503, '조사방법 PDF 3쪽을 생성하지 못했습니다. 실행환경과 원본을 확인해 주세요.') from exc
        return Response(content,media_type='application/pdf',headers={
            'Content-Disposition':'inline; filename="turnout_methodology_2024.pdf"',
            'Cache-Control':'public, max-age=3600',
        })

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
