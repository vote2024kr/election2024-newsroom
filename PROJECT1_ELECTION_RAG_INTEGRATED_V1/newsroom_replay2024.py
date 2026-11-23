"""Historical 2024 election snapshot replay (archived observations only).

No fabricated intermediate candidate votes. Final 10:25 is a cited replay
label based on contemporary reports (not a certified NEC minute).
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
    .replay-meters{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:16px}
    .replay-finale[hidden]{display:none}.replay-finale{margin:18px 0 0}
    .replay-finale iframe{width:100%;height:830px;border:1px solid #315174;border-radius:12px;background:#101e32}
    .replay-meter{background:#152943;border:1px solid #345674;padding:20px;border-radius:12px}
    .replay-meter b{display:block;font-size:36px;margin:8px 0}
    .replay-meter small{color:#b1c6de;font-size:12px}
    .replay-early-vote-guide{margin:0 0 12px;color:#bce7dc;font-size:12px;line-height:1.6;font-weight:600}
    .replay-meter .track{height:16px;margin:15px 0 5px}
    .replay-progress{font-size:12px;color:#b9cfdf}
    .replay-source{padding:12px;background:#132e3f;border-left:3px solid #4fc1d6;margin:15px 0;font-size:13px}
    .replay-caution{color:#d6dfe8;font-size:13px;line-height:1.75}
    @media(max-width:820px){.replay-meters{grid-template-columns:1fr}}
    """
    body=f"""<section class="panel" aria-label="선거 당시 보도 기록 재생">
    <div><span class="replay-mark">2024년 시간대별 기록</span><span class="sub">실시간 연결 아님 · 2024년 당시 공개된 수치</span></div>
    <h2 style="margin-top:16px">전국 투표율·지역구·비례대표 개표율</h2>
    <p class="sub" id="replay-time">2024-04-10 07:00</p>
    <div class="replay-meters">
      <div class="replay-meter"><small>전국 투표율</small><b id="replay-turnout">1.8%</b><p id="replay-early-vote-guide" class="replay-early-vote-guide" role="note" hidden>※ 13시부터 사전투표 등이 합산되어 투표율이 크게 상승합니다.</p><div class="track"><div class="fill" id="replay-turnout-bar" style="width:1.8%;background:#3cc4a3"></div></div><small id="replay-turnout-note">당일 본투표 집계 · 사전투표 미포함</small></div>
      <div class="replay-meter"><small>전국 지역구 개표율</small><b id="replay-counting">집계 전</b><div class="track"><div class="fill" id="replay-count-bar" style="width:0%"></div></div><small id="replay-counting-asof">기록 없음</small></div>
      <div class="replay-meter"><small>전국 비례대표 개표율</small><b id="replay-pr">집계 전</b><div class="track"><div class="fill" id="replay-pr-bar" style="width:0%;background:#da8053"></div></div><small id="replay-pr-asof">기록 없음</small></div>
    </div>
    <div class="replay-tools">
      <button type="button" id="replay-play">일시정지</button>
      <button type="button" id="replay-restart">처음부터</button>
      <button type="button" id="replay-next">다음 시점</button>
      <label>자동 갱신 간격 <select id="replay-speed"><option value="5">5초</option><option value="10">10초</option><option value="15">15초</option></select></label>
    </div>
    <div class="replay-progress" id="replay-progress" aria-live="polite">기록 1 / {len(data['events'])}</div>
    <div class="replay-source"><span id="replay-note">당일 본투표 투표율 · 사전투표 등 미합산</span><br>기록 출처: <a id="replay-source" href="{data['turnout_source']}" rel="noopener noreferrer" target="_blank">중앙선관위 제공 기록 확인</a></div>
    <p class="replay-caution"><strong>자료 구분:</strong> 투표율은 선관위 발표 수치이며 개표율은 당시 보도에서 확인된 <strong>일부 시점</strong>만 표시합니다. 확인되지 않은 중간 개표율과 지역구별 중간 득표수는 임의로 만들지 않았습니다.</p>
    <section id="replay-final-map" class="replay-finale" hidden><h2>2024.04.11 10:25 | 전국 개표 완료 100%</h2><p class="sub">지역구 254개 최종 결과 · 10:25는 당시 보도에 근거한 재현용 시각이며 중앙선관위의 분 단위 공식 종료 인증 시각은 아닙니다.</p><a class="btn" href="#replay-final-map" id="replay-map-scroll">최종 개표 결과 보기</a><iframe id="replay-map-frame" title="최종 전국 지도 · 시도 및 선거구 탐색" loading="lazy"></iframe></section>
    <p><a class="btn" href="/safe2024?page=final">최종 지도·확정 개표 보기</a> <a class="btn" href="/safe2024?page=district">지역구 상세 목록</a></p>
    </section>
    <script type="application/json" id="election-replay-data">{payload}</script>
    <script>{REPLAY_JS}</script>
    <style>{css}</style>
    """
    return HTMLResponse(layout('home','2024년 22대 국회의원 선거 시간대별 투·개표 현황','기록 시점을 일정 간격으로 자동 전환합니다. 과거 실제 보도 기록을 재생하며 실시간 선관위 서버와 연결하지 않습니다.',body,status='2024년 시간대별 기록'))

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
    const counted=evt.counting!=null;
    $('replay-counting').textContent=counted?Number(evt.counting).toFixed(evt.phase==='final'?0:2)+'%':'개표 전';
    $('replay-count-bar').style.width=counted?evt.counting+'%':'0%';
    $('replay-counting-asof').textContent=evt.counting_asof?'마지막 확인 시점: '+evt.counting_asof:'당시 기록 미확인';
    const prop=evt.proportional!=null;
    $('replay-pr').textContent=prop?Number(evt.proportional).toFixed(evt.phase==='final'?0:2)+'%':'기록 전';
    $('replay-pr-bar').style.width=prop?evt.proportional+'%':'0%';
    $('replay-pr-asof').textContent=evt.proportional_asof?'마지막 확인 시점: '+evt.proportional_asof:'당시 기록 미확인';
    const completed=evt.phase==='final'&&evt.counting===100&&evt.proportional===100;
    $('replay-final-map').hidden=!completed;
    if(completed && !$('replay-map-frame').getAttribute('src')) $('replay-map-frame').src='/safe2024/map';
    if(!completed) $('replay-map-frame').removeAttribute('src');
    $('replay-note').textContent=evt.note;
    $('replay-source').setAttribute('href',evt.source);
    $('replay-source').textContent=evt.source_label;
    $('replay-progress').textContent='확인된 기록 '+(position+1)+' / '+events.length+' · '+(evt.phase==='final'?'최종 확정 집계':evt.series==='proportional'?'당시 비례대표 개표율':evt.phase==='counting'?'당시 전국 지역구 개표율':'선관위 시간별 투표율');
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
  $('replay-map-scroll').addEventListener('click',(evt)=>{evt.preventDefault();$('replay-final-map').scrollIntoView({behavior:'smooth',block:'start'});});
  $('replay-speed').addEventListener('change',(e)=>{delay=Number(e.target.value)||5;schedule();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){cancel();}else{schedule();}});
  show(events[0]);schedule();
})();
"""


def _validated_rows():
    rows=dataset()['events']
    seen=set()
    previous={'constituency':-1.0,'proportional':-1.0}
    if len(rows)<24 or rows[-1]['id']!='final':
        raise ValueError('시간별 개표 기록 개수 또는 최종 단계가 일치하지 않습니다.')
    for i,evt in enumerate(rows):
        if evt['id'] in seen or not evt['source'].startswith('https://'):
            raise ValueError('기록 중복 또는 원문 출처 누락')
        seen.add(evt['id'])
        if i and rows[i-1]['time']>evt['time']:
            raise ValueError('시간순 정렬 오류')
        for series,field in [('constituency','counting'),('proportional','proportional')]:
            if evt.get('series')==series:
                val=float(evt[field])
                if not 0<=val<=100 or val<previous[series]:
                    raise ValueError('개표율이 이전 시점보다 감소하거나 범위를 벗어남')
                previous[series]=val
    return rows


def seed_postgres(host,port,dbname,user,password):
    """Create an additive v2 replay table, preserving all historical election tables."""
    import psycopg
    rows=_validated_rows()
    # The original historical_replay_2024 is preserved; the new table is an
    # immutable verified replay cache rebuilt atomically from the source archive.
    with psycopg.connect(host=host,port=port,dbname=dbname,user=user,password=password,
                        connect_timeout=8,options='-c statement_timeout=15000') as conn:
        with conn.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS election_lab.historical_replay_2024_v2 (
                seq INTEGER PRIMARY KEY,
                observation_id TEXT NOT NULL,
                observed_time TEXT NOT NULL,
                phase TEXT NOT NULL,
                series TEXT NOT NULL,
                turnout_percent NUMERIC(5,2) NOT NULL,
                constituency_counted_percent NUMERIC(5,2),
                proportional_counted_percent NUMERIC(5,2),
                constituency_asof TEXT,
                proportional_asof TEXT,
                source_url TEXT NOT NULL,
                source_label TEXT NOT NULL,
                observation_note TEXT NOT NULL,
                observation_time_kind TEXT NOT NULL
            )''')
            # v2 contains only data derived from this versioned JSON archive.
            cur.execute('DELETE FROM election_lab.historical_replay_2024_v2')
            for i,evt in enumerate(rows):
                cur.execute('''INSERT INTO election_lab.historical_replay_2024_v2
                    (seq,observation_id,observed_time,phase,series,turnout_percent,
                     constituency_counted_percent,proportional_counted_percent,
                     constituency_asof,proportional_asof,source_url,source_label,
                     observation_note,observation_time_kind)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (i,evt['id'],evt['time'],evt['phase'],evt['series'],
                     evt['turnout'],evt['counting'],evt['proportional'],
                     evt.get('counting_asof'),evt.get('proportional_asof'),
                     evt['source'],evt['source_label'],evt['note'],
                     evt.get('time_kind','당시 집계 기준')))
            cur.execute('SELECT seq,observation_id,proportional_counted_percent FROM election_lab.historical_replay_2024_v2 ORDER BY seq')
            saved=cur.fetchall()
            if len(saved)!=len(rows) or any(a[0]!=i or a[1]!=evt['id'] or
                (None if a[2] is None else float(a[2]))!=evt['proportional']
                for i,(a,evt) in enumerate(zip(saved,rows))):
                raise RuntimeError('추가 개표 재생 기록 DB 검증 실패')
    return len(rows)


def pg_replay_observation(index):
    if not isinstance(index,int) or not 0<=index<len(_validated_rows()):
        raise HTTPException(status_code=404,detail='등록되지 않은 시점입니다.')
    with postgres_data._connect() as conn:
        with conn.cursor() as cur:
            cur.execute('''SELECT observation_id,observed_time,phase,series,
                turnout_percent,constituency_counted_percent,proportional_counted_percent,
                constituency_asof,proportional_asof,source_url,source_label,
                observation_note,observation_time_kind
                FROM election_lab.historical_replay_2024_v2 WHERE seq = %s''',(index,))
            row=cur.fetchone()
    if row is None:
        raise HTTPException(503,detail='PostgreSQL 재생 기록이 없습니다. 최신 V5 실행기를 사용해 주세요.')
    return {
        'id':row[0],'time':row[1],'phase':row[2],'series':row[3],
        'turnout':float(row[4]),
        'counting':None if row[5] is None else float(row[5]),
        'proportional':None if row[6] is None else float(row[6]),
        'counting_asof':row[7],'proportional_asof':row[8],
        'source':row[9],'source_label':row[10],'note':row[11],
        'time_kind':row[12]
    }
