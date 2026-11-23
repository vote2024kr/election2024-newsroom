"""Historical 2024 election snapshot replay (archived observations only).

No fabricated intermediate candidate votes. 100% is the final official result,
not a claimed timestamp. Does not access the heavy legacy SPA or websockets.
"""
from __future__ import annotations
import json
from pathlib import Path
from fastapi.responses import HTMLResponse
from fastapi import HTTPException
from newsroom import postgres_data

ROOT=Path(__file__).resolve().parent
ARCHIVE=ROOT/'data'/'election_2024_replay_observed.json'

def dataset():
    with ARCHIVE.open(encoding='utf-8') as fp:
        return json.load(fp)

def replay_html(layout):
    data=dataset()
    first=data['events'][0]
    # Data is an immutable bundled historical archive. Escape script terminators.
    payload=json.dumps(data['events'],ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    css=r"""
    .replay-mark {display:inline-block;color:#0e1b24;background:#72dcea;border-radius:5px;padding:5px 9px;font-size:12px;font-weight:800;margin-right:8px}
    .replay-tools{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:15px 0}
    .replay-tools button{background:#19688c;color:#fff;border:1px solid #388bad;border-radius:7px;padding:10px 14px;font-weight:700}
    .replay-tools label{font-size:13px;color:#c0d6e9}
    .replay-tools select{max-width:110px}
    .replay-meters{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:16px}
    .replay-meter{background:#152943;border:1px solid #345674;padding:20px;border-radius:12px}
    .replay-meter b{display:block;font-size:36px;margin:8px 0}
    .replay-meter small{color:#b1c6de;font-size:12px}
    .replay-early-vote-guide{margin:0 0 12px;color:#bce7dc;font-size:12px;line-height:1.6;font-weight:600}
    .replay-meter .track{height:16px;margin:15px 0 5px}
    .replay-progress{font-size:12px;color:#b9cfdf}
    .replay-source{padding:12px;background:#132e3f;border-left:3px solid #4fc1d6;margin:15px 0;font-size:13px}
    .replay-caution{color:#d6dfe8;font-size:13px;line-height:1.75}
    @media(max-width:600px){.replay-meters{grid-template-columns:1fr}}
    """
    body=f"""<section class="panel" aria-label="선거 당시 보도 기록 재생">
    <div><span class="replay-mark">2024년 기록 재생</span><span class="sub">실시간 연결 아님 · 2024년 당시 공개된 수치</span></div>
    <h2 style="margin-top:16px">시각별 전국 투표율·지역구 개표율</h2>
    <p class="sub" id="replay-time">2024-04-10 07:00</p>
    <div class="replay-meters">
      <div class="replay-meter"><small>전국 투표율</small><b id="replay-turnout">1.8%</b><p id="replay-early-vote-guide" class="replay-early-vote-guide" role="note" hidden>※ 13시부터 사전투표 등이 합산되어 투표율이 크게 상승합니다.</p><div class="track"><div class="fill" id="replay-turnout-bar" style="width:1.8%;background:#3cc4a3"></div></div><small id="replay-turnout-note">당일 본투표 집계 · 사전투표 미포함</small></div>
      <div class="replay-meter"><small>전국 <strong>지역구</strong> 개표율</small><b id="replay-counting">집계 전</b><div class="track"><div class="fill" id="replay-count-bar" style="width:0%"></div></div><small>비례대표 개표율과 구분</small></div>
    </div>
    <div class="replay-tools">
      <button type="button" id="replay-play">일시정지</button>
      <button type="button" id="replay-restart">처음부터</button>
      <button type="button" id="replay-next">다음 시점</button>
      <label>자동 갱신 간격 <select id="replay-speed"><option value="5">5초</option><option value="10">10초</option><option value="15">15초</option></select></label>
    </div>
    <div class="replay-progress" id="replay-progress" aria-live="polite">기록 1 / {len(data['events'])}</div>
    <div class="replay-source"><span id="replay-note">당일 본투표 투표율 · 사전투표 등 미합산</span><br>기록 출처: <a id="replay-source" href="{data['turnout_source']}" rel="noopener noreferrer" target="_blank">중앙선관위 제공 기록 확인</a></div>
    <p class="replay-caution"><strong>자료 구분:</strong> 투표율은 선관위가 발표한 시각별 수치입니다. 개표율은 당일 기사에서 확인한 <strong>일부 시점</strong>입니다. 확인되지 않은 중간 수치는 보간하거나 실제 집계로 표시하지 않았습니다. 지역구별 중간 득표수는 확보되지 않아 최종 데이터와 섞지 않습니다. 13시부터 사전투표 등을 합산합니다.</p>
    <p><a class="btn" href="/safe2024?page=final">PostgreSQL 최종 확정 개표 결과 보기</a> <a class="btn" href="/safe2024?page=district">254개 지역구 최종 결과</a></p>
    </section>
    <script type="application/json" id="election-replay-data">{payload}</script>
    <script>{REPLAY_JS}</script>
    <style>{css}</style>
    """
    return HTMLResponse(layout('home','2024년 총선 시간별 재생','기록 시점을 일정 간격으로 자동 전환합니다. 과거 실제 보도 기록을 재생하며 실시간 선관위 서버와 연결하지 않습니다.',body,status='2024년 기록 재생'))

REPLAY_JS=r"""
(function(){'use strict';
  const events=JSON.parse(document.getElementById('election-replay-data').textContent);
  let position=0,delay=5,playing=true,timer=null;
  const $=(id)=>document.getElementById(id);
  const show=(evt)=>{
    $('replay-time').textContent=evt.time;
    $('replay-turnout').textContent=Number(evt.turnout).toFixed(1)+'%';
    $('replay-turnout-bar').style.width=evt.turnout+'%';
    $('replay-early-vote-guide').hidden = !(evt.phase==='turnout' && evt.time >= '2024-04-10 13:00');
    $('replay-turnout-note').textContent=evt.phase==='turnout' && evt.time<='2024-04-10 12:00'?'당일 본투표 집계 · 사전투표 미포함':'사전·거소·선상·재외투표 등 포함';
    const counted=evt.counting!==null;
    $('replay-counting').textContent=counted?Number(evt.counting).toFixed(evt.phase==='final'?0:2)+'%':'개표 전';
    $('replay-count-bar').style.width=counted?evt.counting+'%':'0%';
    $('replay-note').textContent=evt.note;
    $('replay-source').setAttribute('href',evt.source);
    $('replay-source').textContent=evt.source_label;
    $('replay-progress').textContent='확인된 기록 '+(position+1)+' / '+events.length+' · '+(evt.phase==='final'?'최종 확정 집계':evt.phase==='counting'?'당시 전국 지역구 개표율':'선관위 시간별 투표율');
  };
  const cancel=()=>{if(timer!==null){clearTimeout(timer);timer=null;}};
  const setPosition=async(target)=>{
    if(target>=events.length)return;
    cancel();
    try{
      const response=await fetch('/safe2024/api/replay/'+target,{cache:'no-store'});
      if(!response.ok)throw Error('HTTP '+response.status);
      const item=await response.json();
      if(item.id!==events[target].id)throw Error('시점 식별 불일치');
      position=target;show(item);
      if(position===events.length-1){playing=false;$('replay-play').textContent='다시 재생';}
      else schedule();
    }catch(err){playing=false;$('replay-play').textContent='재생';$('replay-progress').textContent='PostgreSQL 시간별 기록 조회 실패 — 서버 로그 확인 후 재생 버튼을 누르세요.';}
  };
  const schedule=()=>{
    cancel(); if(!playing||position>=events.length-1)return;
    timer=setTimeout(()=>{void setPosition(position+1);},delay*1000);
  };
  $('replay-play').addEventListener('click',()=>{
     if(position===events.length-1){position=0;show(events[0]);playing=true;}
     else playing=!playing;
     $('replay-play').textContent=playing?'일시정지':'재생';schedule();
  });
  $('replay-restart').addEventListener('click',()=>{position=0;playing=true;show(events[0]);$('replay-play').textContent='일시정지';schedule();});
  $('replay-next').addEventListener('click',()=>{if(position<events.length-1){void setPosition(position+1);}});
  $('replay-speed').addEventListener('change',(e)=>{delay=Number(e.target.value)||5;schedule();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){cancel();}else{schedule();}});
  show(events[0]);schedule();
})();
"""


def seed_postgres(host,port,dbname,user,password):
    """Add validated historical observation rows; never change original election tables."""
    import psycopg
    rows=dataset()['events']
    with psycopg.connect(host=host,port=port,dbname=dbname,user=user,password=password,connect_timeout=8,options='-c statement_timeout=15000') as conn:
        with conn.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS election_lab.historical_replay_2024 (
                seq INTEGER PRIMARY KEY,
                observation_id TEXT UNIQUE NOT NULL,
                observed_time TEXT NOT NULL,
                phase TEXT NOT NULL CHECK(phase IN ('turnout','counting','final')),
                turnout_percent NUMERIC(5,2) NOT NULL,
                constituency_counted_percent NUMERIC(5,2),
                source_url TEXT NOT NULL,
                source_label TEXT NOT NULL,
                observation_note TEXT NOT NULL
            )''')
            for i,evt in enumerate(rows):
                cur.execute('''INSERT INTO election_lab.historical_replay_2024
                    (seq,observation_id,observed_time,phase,turnout_percent,constituency_counted_percent,
                    source_url,source_label,observation_note)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (seq) DO NOTHING''',
                    (i,evt['id'],evt['time'],evt['phase'],evt['turnout'],evt['counting'],evt['source'],evt['source_label'],evt['note']))
            cur.execute('SELECT seq,observation_id,turnout_percent,constituency_counted_percent FROM election_lab.historical_replay_2024 ORDER BY seq')
            actual=cur.fetchall()
            if len(actual)!=len(rows) or any((a[0]!=i or a[1]!=e['id'] or float(a[2])!=e['turnout'] or (None if a[3] is None else float(a[3]))!=e['counting']) for i,(a,e) in enumerate(zip(actual,rows))):
                raise RuntimeError('기존 시간별 자료가 다른 버전과 충돌합니다. 데이터를 임의로 수정하지 않았습니다.')
    return len(rows)


def pg_replay_observation(index):
    if not isinstance(index,int) or not 0<=index<len(dataset()['events']):
        raise HTTPException(status_code=404,detail='등록되지 않은 시점입니다.')
    with postgres_data._connect() as conn:
        with conn.cursor() as cur:
            cur.execute('''SELECT observation_id,observed_time,phase,turnout_percent,constituency_counted_percent,source_url,source_label,observation_note
                FROM election_lab.historical_replay_2024 WHERE seq = %s''',(index,))
            r=cur.fetchone()
    if r is None:
        raise HTTPException(503,detail='PostgreSQL 시간별 기록이 없습니다. V5 실행기를 사용하세요.')
    return {'id':r[0],'time':r[1],'phase':r[2],'turnout':float(r[3]),'counting':None if r[4] is None else float(r[4]),'source':r[5],'source_label':r[6],'note':r[7]}
