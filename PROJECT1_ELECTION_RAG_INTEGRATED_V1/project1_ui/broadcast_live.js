// Reuses the existing Project 1 WebSocket snapshots. No official live feed.
(()=>{'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const fmt=n=>Math.round(Number(n)||0).toLocaleString('ko-KR');
const names=['모의 후보 A','모의 후보 B','모의 후보 C'];
let lastStep=null,lastCount=null;
function clock(){$('broadcastClock').textContent=new Date().toLocaleTimeString('ko-KR',{hour12:false,timeZone:'Asia/Seoul'})}
function render(s){if(!s||s.mode!=='SIMULATION_ONLY')return;
 const votes=(s.national?.votes||[]).map(v=>Math.max(0,Number(v)||0));const counted=votes.reduce((a,b)=>a+b,0);
 const max=Math.max(1,...votes);const leader=votes.length&&counted>0?votes.indexOf(max):-1;
 const paused=!s.running;
 $('broadcastHeadline').textContent=paused?'모의 개표 일시정지 · 마지막 집계 결과':
  leader<0?'전국 모의 개표를 준비하고 있습니다':`${names[leader]} · 전국 모의 집계 선두`;
 $('broadcastUpdate').textContent=`${s.step}회 · ${s.updated_at||'갱신시각 미확인'}`;
 $('broadcastCandidates').innerHTML=names.map((name,i)=>{
   const v=votes[i]||0,pct=counted?v/counted*100:0;
   return `<div class="candidate-row"><div class="candidate-label">${esc(name)}</div><div class="candidate-bar"><i style="width:${Math.max(0,Math.min(100,pct)).toFixed(2)}%"></i></div><div class="candidate-number"><strong>${esc(pct.toFixed(2))}%</strong><small>${esc(fmt(v))}표</small></div></div>`;
 }).join('');
 const progress=Math.max(0,Math.min(100,Number(s.national?.progress_pct)||0));
 $('broadcastPct').textContent=progress.toFixed(2)+'%';$('broadcastProgressBar').style.width=progress+'%';
 const regions=(s.regions||[]).slice().sort((a,b)=>(Number(b.counted)||0)-(Number(a.counted)||0)).slice(0,6);
 $('broadcastRegions').innerHTML=regions.map(x=>`<div class="region-row"><strong>${esc(x.full_name||x.name||x.id)}</strong><span>${esc(fmt(x.counted))}표</span><small>가상 집계 진행 ${esc(Number(x.progress_pct||0).toFixed(2))}%</small></div>`).join('');
 const changed=lastStep!==null&&s.step>lastStep?Math.max(0,Number(s.national?.counted||0)-Number(lastCount||0)):0;
 const hint=paused?'모의 방송 일시정지':`모의 집계 ${s.step}회차 갱신`;
 $('broadcastTicker').textContent=`${hint}  ·  전국 가상 집계표 ${fmt(s.national?.counted)}표`+(changed?`  ·  직전 단계 대비 +${fmt(changed)}표`:'')+
   `  ·  교육용 시뮬레이션  ·  실제 선거 결과·당선 예측이 아닙니다  ·  기사 검증과 사람 승인 후에만 보도 가능`;
 lastStep=s.step;lastCount=s.national?.counted;
}
document.addEventListener('project1:snapshot',e=>render(e.detail));
clock();setInterval(clock,1000);
// Populate the studio immediately; all subsequent refreshes use the existing socket.
fetch('/api/snapshot').then(r=>r.ok?r.json():null).then(x=>{if(x)render(x)}).catch(()=>{});
})();
