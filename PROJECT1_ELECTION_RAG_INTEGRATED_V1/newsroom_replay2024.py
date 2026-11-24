"""2024년 제22대 총선 과거 투·개표 시각별 재생: 실측 관측 시점만 표시."""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from newsroom import postgres_data

ROOT=Path(__file__).resolve().parent
ARCHIVE=ROOT/'data'/'election_2024_replay_observed.json'

def dataset():
    return json.loads(ARCHIVE.read_text(encoding='utf-8'))

def _validated_rows():
    rows=dataset()['events']
    if len(rows)!=41 or rows[-1]['id']!='final':raise ValueError('시각별 개표 기록 41개 검증 실패')
    seen=set();previous={'constituency':-1,'proportional':-1}
    for i,row in enumerate(rows):
        if row['id'] in seen or not row['source'].startswith('https://'):raise ValueError('ID 또는 출처 검증 실패')
        seen.add(row['id'])
        if i and row['time']<rows[i-1]['time']:raise ValueError('시간순 정렬 오류')
        field={'constituency':'counting','proportional':'proportional'}.get(row.get('series'))
        if field:
            value=row[field]
            if value is None or not 0<=value<=100 or value<previous[row['series']]:
                raise ValueError('개표율 증감 검증 실패')
            previous[row['series']]=value
    if rows[-1]['counting']!=100 or rows[-1]['proportional']!=100:raise ValueError('최종 결과 불일치')
    return rows

def replay_html(layout):
    data=dataset()
    payload=json.dumps(data['events'],ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    css=r"""
.replay-stage{display:grid;grid-template-columns:minmax(310px,.9fr) minmax(0,1.6fr);gap:15px;align-items:stretch}
.replay-gauges{background:#10263d;border:1px solid #305070;border-radius:13px;padding:18px}
.replay-viz{background:#0d2035;border:1px solid #305070;border-radius:13px;padding:16px;min-width:0}
.replay-viz h3{font-size:17px;margin:0 0 7px}.replay-viz .stage-tag{display:inline-block;background:#194863;color:#c9f3fa;padding:6px 10px;border-radius:7px;font-size:12px;font-weight:bold;margin-bottom:9px}
.replay-time{font-size:22px;font-weight:900;letter-spacing:.5px;color:#e5f6fe;margin:9px 0 18px}
.replay-meter{padding:13px;background:#142d47;border:1px solid #345370;border-radius:10px;margin-bottom:11px}
.replay-meter strong{font-size:30px;display:block;margin:5px 0}.replay-meter small{display:block;color:#b5cddd;font-size:12px}
.replay-track{background:#314b65;height:15px;border-radius:11px;overflow:hidden;margin:11px 0 7px}
.replay-fill{height:100%;border-radius:11px;transition:width .3s ease}
.replay-tools{display:flex;gap:8px;flex-wrap:wrap;margin-top:11px;align-items:center}
.replay-tools button{background:#176e91;color:#fff;border:1px solid #298ead;border-radius:7px;padding:9px 12px;font-weight:bold}
.replay-tools select{padding:8px;background:#163b53;color:#fff;border:1px solid #43819a;border-radius:6px}
.replay-tools label{font-size:12px;color:#bed6e4}.replay-progress{font-size:12px;color:#a7c9df;margin-top:12px}
.replay-timeline{display:grid;gap:6px;margin-top:14px}.replay-timeline label{font-size:12px;color:#a2dbea}
.replay-timeline input{width:100%;height:12px;accent-color:#44cdd6;background:#23435d;cursor:pointer}
.replay-note{font-size:12px;color:#bddeed;line-height:1.8;margin-top:13px}.replay-note a{color:#8bdbf1}
.replay-visual-screen[hidden],.replay-finale[hidden],.replay-final-cta[hidden]{display:none !important}
.replay-visual-screen{min-height:400px}.replay-chart{width:100%;height:auto;max-height:460px}
.replay-svg-axis{fill:#91adc4;font-size:11px}.replay-svg-grid{stroke:#294760;stroke-width:1}.replay-svg-point{fill:#baffee;stroke:#116f83;stroke-width:2}
.replay-map-frame{width:100%;height:545px;border:1px solid #264661;border-radius:10px;background:#0d2137}
.replay-final-layout{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(300px,1fr);gap:12px}
.replay-final-layout .replay-map-frame{height:630px}.replay-chart-slot{min-width:0}
.replay-chart-slot .seats-section h3{font-size:15px}.replay-chart-slot .vis-card{padding:8px}
.replay-chart-slot .donut-grid{gap:7px}.replay-chart-slot .donut-grid svg{height:133px}
.replay-chart-slot .seat-legend span{font-size:10px;padding:3px 5px}.replay-chart-slot .hemi svg{max-height:155px}
.replay-chart-slot .seats-section{margin:0}.replay-chart-slot .seat-legend{gap:5px}
.replay-early-guide{padding:9px 12px;background:#123e48;border-left:4px solid #46c6b2;font-size:12px;color:#c8eee6;margin:10px 0}
.replay-intro{display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;margin-bottom:15px}
.replay-intro b{color:#72dcea}.replay-intro span{font-size:12px;color:#a3c0d6}
.replay-feature-links{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:15px 0}
.replay-feature-links a{display:block;background:#142b44;border:1px solid #2e526e;border-radius:10px;padding:15px 9px;text-align:center;color:#bee9f7;text-decoration:none;font-size:12px}
.replay-feature-links a:hover{background:#1b4564}.replay-feature-links strong{display:block;font-size:14px;margin-bottom:5px}
.replay-card-image{height:110px;display:flex;align-items:center;justify-content:center;overflow:hidden;margin:9px auto;border:1px solid #2a526c;border-radius:7px;background:#0d2035}
.replay-card-image.map-preview img,.replay-card-image.search-preview img{max-height:106px;width:auto;max-width:92%;object-fit:contain;opacity:.62}
.replay-card-image.search-preview{position:relative}.replay-card-image.search-preview>span{position:absolute;right:25%;top:20%;border:2px solid #63d6e8;color:#72e8f7;background:#183c55;font-size:24px;width:37px;height:37px;border-radius:50%}
.replay-card-image.turnout-preview{display:grid;grid-template-columns:52px 1fr;grid-template-rows:repeat(3,24px);align-content:center;gap:5px;padding:6px 14px;color:#c7e7f3;font-size:12px}
.replay-card-image.turnout-preview>i{display:block;height:12px;border-radius:8px;background:#38bfce}.replay-card-image.turnout-preview>i:nth-of-type(2){width:84%;background:#229abb}.replay-card-image.turnout-preview>i:nth-of-type(3){width:65%;background:#167baf}
.replay-card-image.margin-preview{display:flex;flex-direction:column;gap:9px;padding:20px}.replay-card-image.margin-preview i{height:13px;background:linear-gradient(to right,#287bd7 51%,#dc4e62 51%);width:85%;border-radius:7px}
.replay-card-image.margin-preview i:nth-child(2){width:96%;background:linear-gradient(to right,#287bd7 49%,#dc4e62 49%)}
.replay-card-image.margin-preview i:nth-child(3){width:77%;background:linear-gradient(to right,#287bd7 53%,#dc4e62 53%)}
@media(max-width:1120px){.replay-final-layout{grid-template-columns:1fr}.replay-stage{grid-template-columns:1fr}.replay-feature-links{grid-template-columns:repeat(2,1fr)}}
@media(max-width:540px){.replay-feature-links{grid-template-columns:1fr}.replay-gauges,.replay-viz{padding:11px}.replay-meter strong{font-size:25px}}
"""
    body=f'''<section class="panel" aria-label="2024년 시각별 투개표 재생">
<div class="replay-intro"><b>2024년 시간대별 기록</b><span>과거 공개자료 재생 · 실시간 연결 아님</span></div>
<div class="replay-stage">
<div class="replay-gauges"><p class="replay-time" id="replay-time">2024-04-10 07:00</p>
  <div class="replay-meter"><small>전국 투표율</small><strong id="replay-turnout">1.8%</strong><div class="replay-track"><div class="replay-fill" id="replay-turnout-bar" style="width:1.8%;background:#40c8ad"></div></div><small id="replay-turnout-note">당일 본투표 · 사전투표 미포함</small></div>
  <div class="replay-meter"><small>전국 지역구 개표율</small><strong id="replay-counting">개표 전</strong><div class="replay-track"><div class="replay-fill" id="replay-count-bar" style="width:0%;background:#378cde"></div></div><small id="replay-counting-asof">당시 기록 미확인</small></div>
  <div class="replay-meter"><small>전국 비례대표 개표율</small><strong id="replay-pr">개표 전</strong><div class="replay-track"><div class="replay-fill" id="replay-pr-bar" style="width:0%;background:#e29749"></div></div><small id="replay-pr-asof">당시 기록 미확인</small></div>
  <p id="replay-early-vote-guide" class="replay-early-guide" hidden>※ 13시부터 사전투표 등이 합산되어 투표율이 크게 상승합니다.</p>
  <div class="replay-tools"><button id="replay-play" type="button">일시정지</button><button id="replay-restart" type="button">처음부터</button><button id="replay-next" type="button">다음 시점</button><label>갱신 <select id="replay-speed"><option value="5">5초</option><option value="10">10초</option><option value="15">15초</option></select></label></div>
  <div class="replay-timeline"><label for="replay-seek">재생 시점 직접 선택</label><input type="range" id="replay-seek" min="0" max="{len(data['events'])-1}" step="1" value="0" aria-label="2024년 시간별 기록 바로가기"></div>
  <p class="replay-progress" id="replay-progress">확인된 기록 1 / {len(data['events'])}</p>
  <p class="replay-note"><span id="replay-note">전국 투표율 관측값</span><br>출처: <a id="replay-source" href="{data['turnout_source']}" target="_blank" rel="noopener noreferrer">중앙선관위 발표 보도</a></p>
</div>
<div class="replay-viz">
  <div id="replay-viz-turnout" class="replay-visual-screen"><div class="stage-tag">투표 진행 · 시간별 변화</div><h3>전국 투표율 추이</h3><p class="sub">현재 재생 시각까지의 확인된 투표율</p><svg id="replay-line" class="replay-chart" viewBox="0 0 650 390" role="img" aria-label="실제 전국 투표율 시간별 꺾은선 그래프"></svg></div>
  <div id="replay-viz-count" class="replay-visual-screen" hidden><div class="stage-tag">지역구·비례대표 개표 진행</div><h3>전국 개표 진행 상황</h3><p class="sub">정당별 당선 지도와 최종 의석은 개표 완료 전 공개하지 않습니다.</p><iframe class="replay-map-frame" title="당선 정당 미표시 전국 지도" data-src="/safe2024/map?mode=outline&amp;compact=1" loading="lazy"></iframe></div>
  <div id="replay-viz-final" class="replay-visual-screen" hidden><div class="stage-tag">2024.04.11 10:25 · 개표 완료</div><h3>지역구·비례대표 100% · 최종 결과</h3><div class="replay-final-layout"><iframe class="replay-map-frame" id="replay-final-map-frame" title="전국 254개 지역구 최종 당선 지도" loading="lazy"></iframe><div id="replay-final-seat-slot" class="replay-chart-slot" aria-live="polite">최종 의석수 자료 확인 중</div></div></div>
</div></div>
<p class="replay-note"><b>자료 구분:</b> 시간별 투표율과 개표율은 당시 선관위 발표 및 언론이 인용한 확인 시점만 사용합니다. 확인되지 않은 중간 집계율과 지역구별 중간 득표수는 만들지 않았습니다. 10:25는 당시 보도 기반 재현용 완료 시각입니다.</p>
<p id="replay-final-cta" class="replay-final-cta" hidden><a class="btn" href="#replay-viz-final">최종 개표 결과 보기</a></p>
</section>
<section class="panel"><h2>2024년 제22대 총선 · 데이터 분석 바로가기</h2>
<div class="replay-feature-links" id="replay-feature-previews">
 <a href="/safe2024?page=final"><strong>전국 확정 개표</strong><span class="replay-card-image map-preview"><img alt="" src="/static/map_outline_snapshot.png"></span><span>당선 지도 · 정당별 의석</span></a>
 <a href="/safe2024?page=turnout"><strong>투표율 분석</strong><span class="replay-card-image turnout-preview"><span>70.1%</span><i></i><span>67.0%</span><i></i><span>62.2%</span><i></i></span><span>17개 시·도·성별·연령별</span></a>
 <a href="/safe2024?page=district"><strong>지역·선거구 탐색</strong><span class="replay-card-image search-preview"><img alt="" src="/static/map_outline_snapshot.png"><span>⌕</span></span><span>지도 선택 → 후보별 결과</span></a>
 <a href="/safe2024?page=stats"><strong>개표 분석</strong><span class="replay-card-image margin-preview"><i></i><i></i><i></i></span><span>의석 분포 · 접전 득표차</span></a>
 </div>
<p class="sub">이동 메뉴는 별도로 열람할 수 있지만 메인 재생 화면의 최종 당선 지도와 의석수는 100%에 도달하기 전까지 표시하지 않습니다.</p></section>
<script type="application/json" id="election-replay-data">{payload}</script><script>{REPLAY_JS}</script><style>{css}</style>'''
    return HTMLResponse(layout('home','2024년 22대 국회의원 선거 시간대별 투·개표 현황','2024년 당시 확인된 투표·개표 기록을 시각별로 다시 확인합니다. 실제 현재 선거가 아닙니다.',body,status='2024년 시간대별 기록'))

REPLAY_JS=r"""
(()=>{'use strict';
const events=JSON.parse(document.querySelector('#election-replay-data').textContent);
const el=id=>document.getElementById(id);
let position=0,delay=5,playing=true,timer=null,seatHtml=null,finalLoading=null;
const clear=()=>{if(timer!==null){clearTimeout(timer);timer=null}};
function renderLine(current){
  const data=events.filter(x=>x.phase==='turnout'&&x.time<=current.time);
  const svg=el('replay-line'), w=650,h=390;
  const x=n=>56+(n/11)*555, y=n=>320-n/70*267;
  let html='';
  for(let n=0;n<=70;n+=10){html+=`<line class="replay-svg-grid" x1="56" x2="611" y1="${y(n)}" y2="${y(n)}"/><text class="replay-svg-axis" x="50" y="${y(n)+4}" text-anchor="end">${n}%</text>`}
  for(let i=0;i<12;i+=2){html+=`<text class="replay-svg-axis" x="${x(i)}" y="344" text-anchor="middle">${String(7+i).padStart(2,'0')}시</text>`}
  const points=data.map(v=>{let hour=Number(v.time.slice(11,13));return [x(hour-7),y(v.turnout)]});
  if(points.length>=2)html+=`<polyline fill="none" stroke="#3ed9bb" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" points="${points.map(p=>p.join(',')).join(' ')}"/>`;
  for(const [a,b] of points)html+=`<circle class="replay-svg-point" cx="${a}" cy="${b}" r="5"/>`;
  // Show the annotation only after the confirmed 13:00 turnout record.
  // This callout points to the original recorded value, not an estimate.
  const early=data.find(v=>v.time==='2024-04-10 13:00');
  if(early){
    const px=x(13-7), py=y(early.turnout), lx=px+72, ly=py+47;
    html+=`<defs><marker id="replay-early-arrowhead" markerWidth="9" markerHeight="9" refX="7" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 Z" fill="#ffca75"/></marker></defs>`;
    html+=`<g class="replay-early-vote-callout" aria-label="13시 사전투표율 포함됨"><title>13시부터 사전투표 등이 투표율에 합산됩니다.</title><path d="M${lx+10},${ly+3} Q${px+47},${py+29} ${px+7},${py+7}" fill="none" stroke="#ffca75" stroke-width="2.5" stroke-linecap="round" marker-end="url(#replay-early-arrowhead)"/><rect x="${lx}" y="${ly}" width="190" height="39" rx="8" fill="#4c361b" stroke="#ffca75" stroke-width="1.5"/><text x="${lx+95}" y="${ly+25}" fill="#fff2d8" text-anchor="middle" font-size="14" font-weight="bold">13시 · 사전투표율 포함됨</text></g>`;
  }
  if(points.length){let [a,b]=points[points.length-1];html+=`<rect x="${Math.min(540,a-36)}" y="${Math.max(0,b-47)}" width="88" height="29" rx="6" fill="#134b53"/><text x="${Math.min(540,a-36)+44}" y="${Math.max(0,b-47)+20}" text-anchor="middle" fill="white" font-weight="bold" font-size="16">${data.at(-1).turnout.toFixed(1)}%</text>`}
  svg.innerHTML=html;
}
function clearIframe(frame){if(frame&&frame.hasAttribute('src'))frame.removeAttribute('src')}
function activate(screen){
 ['turnout','count','final'].forEach(name=>{el('replay-viz-'+name).hidden=name!==screen});
}
async function finalSeats(){
 if(seatHtml){el('replay-final-seat-slot').innerHTML=seatHtml;return}
 if(finalLoading)return finalLoading;
 finalLoading=fetch('/safe2024/seats-snippet',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('DB '+r.status);return r.text()}).then(s=>{seatHtml=s;if(el('replay-viz-final').hidden===false)el('replay-final-seat-slot').innerHTML=s}).catch(()=>{
   if(el('replay-viz-final').hidden===false)el('replay-final-seat-slot').textContent='PostgreSQL 최종 의석수 조회에 실패했습니다. DB 연결 상태를 확인하세요.';
 }).finally(()=>{finalLoading=null});return finalLoading;
}
function show(evt){
 el('replay-time').textContent=evt.time;el('replay-seek').value=String(position);
 el('replay-turnout').textContent=Number(evt.turnout).toFixed(1)+'%';
 el('replay-turnout-bar').style.width=evt.turnout+'%';
 el('replay-turnout-note').textContent=evt.phase==='turnout'&&evt.time<='2024-04-10 12:00'?'당일 본투표 · 사전투표 미포함':'사전·거소·선상·재외투표 등 포함';
 el('replay-early-vote-guide').hidden=!(evt.phase==='turnout'&&evt.time>='2024-04-10 13:00');
 const counted=evt.counting!=null;
 el('replay-counting').textContent=counted?(evt.phase==='final'?'100%':Number(evt.counting).toFixed(2)+'%'):'개표 전';
 el('replay-count-bar').style.width=counted?evt.counting+'%':'0%';
 el('replay-counting-asof').textContent=evt.counting_asof?'마지막 확인 시점: '+evt.counting_asof:'당시 기록 미확인';
 const pr=evt.proportional!=null;
 el('replay-pr').textContent=pr?(evt.proportional_display||Number(evt.proportional).toFixed(2)+'%'):'개표 전';
 el('replay-pr-bar').style.width=pr?evt.proportional+'%':'0%';
 el('replay-pr-asof').textContent=evt.proportional_asof?'마지막 확인 시점: '+evt.proportional_asof:'당시 기록 미확인';
 const isFinal=evt.phase==='final'&&evt.counting===100&&evt.proportional===100;
 el('replay-final-cta').hidden=!isFinal;
 const smallMap=document.querySelector('#replay-feature-previews .map-preview img');if(smallMap)smallMap.src=isFinal?'/static/map_final_snapshot.png':'/static/map_outline_snapshot.png';
 if(isFinal){
   activate('final');
   clearIframe(el('replay-viz-count').querySelector('iframe'));
   if(!el('replay-final-map-frame').hasAttribute('src'))el('replay-final-map-frame').src='/safe2024/map?compact=1';
   void finalSeats();
 }else if(evt.phase==='turnout'){
   activate('turnout');clearIframe(el('replay-final-map-frame'));renderLine(evt);
 }else{
   activate('count');clearIframe(el('replay-final-map-frame'));
   const frame=el('replay-viz-count').querySelector('iframe');
   if(!frame.hasAttribute('src'))frame.src=frame.dataset.src;
 }
 el('replay-note').textContent=evt.note;
 el('replay-source').href=evt.source;el('replay-source').textContent=evt.source_label;
 el('replay-progress').textContent=`확인된 기록 ${position+1} / ${events.length} · `+(evt.phase==='final'?'최종 동시 완료':evt.series==='proportional'?'비례대표 개표 기록':evt.phase==='counting'?'지역구 개표 기록':'시간별 투표율');
}
function schedule(){clear();if(!playing||position>=events.length-1||document.hidden)return;timer=setTimeout(()=>{void change(position+1)},delay*1000)}
async function change(target){if(target<0||target>=events.length)return;clear();try{
 const response=await fetch('/safe2024/api/replay/'+target,{cache:'no-store'});
 if(!response.ok)throw Error(String(response.status));
 const record=await response.json();if(record.id!==events[target].id)throw Error('record mismatch');
 position=target;show(record);
 if(position===events.length-1){playing=false;el('replay-play').textContent='다시 재생'}else schedule();
 }catch(e){playing=false;el('replay-play').textContent='재생';el('replay-progress').textContent='PostgreSQL 기록 조회 실패. V5 실행기를 다시 확인하세요.'}
}
el('replay-play').addEventListener('click',()=>{if(position===events.length-1){position=0;show(events[0]);playing=true}else playing=!playing;el('replay-play').textContent=playing?'일시정지':'재생';schedule()});
el('replay-next').addEventListener('click',()=>{if(position<events.length-1)void change(position+1)});
el('replay-restart').addEventListener('click',()=>{position=0;playing=true;show(events[0]);el('replay-play').textContent='일시정지';schedule()});
el('replay-speed').addEventListener('change',e=>{delay=Number(e.target.value)||5;schedule()});
el('replay-seek').addEventListener('change',e=>{void change(Number(e.target.value))});
document.addEventListener('visibilitychange',()=>{if(document.hidden)clear();else schedule()});
show(events[0]);schedule();
})();
"""

def seed_postgres(host,port,dbname,user,password):
    """Preserve the original historical_replay_2024; use a separate verified v2 table."""
    import psycopg
    rows=_validated_rows()
    with psycopg.connect(host=host,port=port,dbname=dbname,user=user,password=password,connect_timeout=8,options='-c statement_timeout=15000') as conn:
        with conn.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS election_lab.historical_replay_2024_v2 (
                seq INTEGER PRIMARY KEY, observation_id TEXT NOT NULL, observed_time TEXT NOT NULL,
                phase TEXT NOT NULL, series TEXT NOT NULL, turnout_percent NUMERIC(5,2) NOT NULL,
                constituency_counted_percent NUMERIC(5,2),proportional_counted_percent NUMERIC(5,2),
                constituency_asof TEXT,proportional_asof TEXT,source_url TEXT NOT NULL,
                source_label TEXT NOT NULL,observation_note TEXT NOT NULL,observation_time_kind TEXT NOT NULL
            )''')
            cur.execute('DELETE FROM election_lab.historical_replay_2024_v2')
            for i,evt in enumerate(rows):
                cur.execute('''INSERT INTO election_lab.historical_replay_2024_v2
                (seq,observation_id,observed_time,phase,series,turnout_percent,constituency_counted_percent,
                 proportional_counted_percent,constituency_asof,proportional_asof,source_url,source_label,
                 observation_note,observation_time_kind)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (i,evt['id'],evt['time'],evt['phase'],evt['series'],evt['turnout'],evt['counting'],evt['proportional'],
                 evt.get('counting_asof'),evt.get('proportional_asof'),evt['source'],evt['source_label'],
                 evt['note'],evt.get('time_kind','당시 집계 기준')))
            cur.execute('SELECT seq,observation_id,proportional_counted_percent FROM election_lab.historical_replay_2024_v2 ORDER BY seq')
            saved=cur.fetchall()
            if len(saved)!=len(rows) or any(i!=a[0] or evt['id']!=a[1] or (None if a[2] is None else float(a[2]))!=evt['proportional'] for i,(a,evt) in enumerate(zip(saved,rows))):
                raise RuntimeError('PostgreSQL 기록 41건 입력 검증 실패')
    return len(rows)

def pg_replay_observation(index):
    rows=_validated_rows()
    if not isinstance(index,int) or not 0<=index<len(rows):
        raise HTTPException(status_code=404,detail='등록되지 않은 시점입니다.')
    with postgres_data._connect() as conn:
        with conn.cursor() as cur:
            cur.execute('''SELECT observation_id,observed_time,phase,series,turnout_percent,
              constituency_counted_percent,proportional_counted_percent,constituency_asof,proportional_asof,
              source_url,source_label,observation_note,observation_time_kind
              FROM election_lab.historical_replay_2024_v2 WHERE seq=%s''',(index,))
            r=cur.fetchone()
    if r is None or r[0]!=rows[index]['id']:
        raise HTTPException(503,detail='PostgreSQL 재생 기록이 현재 파일과 다릅니다. 최신 실행기를 사용하세요.')
    return {'id':r[0],'time':r[1],'phase':r[2],'series':r[3],
            'turnout':float(r[4]),'counting':None if r[5] is None else float(r[5]),
            'proportional':None if r[6] is None else float(r[6]),
            'counting_asof':r[7],'proportional_asof':r[8],
            'source':r[9],'source_label':r[10],'note':r[11],'time_kind':r[12],
            'proportional_display':rows[index].get('proportional_display')}
