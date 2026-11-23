(() => {
'use strict';
const el=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
const number=n=>Number(n||0).toLocaleString('ko-KR',{maximumFractionDigits:3});
let meta=null,analysis=null,replayTimer=null;
const GUIDES={
 region_votes:'빈도·합계: 시도별 각 선거구 후보들의 득표 합계(표).',
 district_votes:'집단별 합계: 선거구별 유효 후보 득표 합계(표).',
 candidate_share:'비율 분석: 한 선거구의 후보 득표수 ÷ 해당 선거구 후보 합계 × 100. 반드시 시도와 선거구 선택.',
 lead_margin:'격차 분석: 각 선거구의 1·2위 표차 ÷ 후보 유효 득표 합계 × 100 (%p).',
 candidate_count:'빈도 분석: 각 선거구에서 확인된 후보자의 수.',
 vote_distribution:'분포 분석: 선거구별 후보 득표 합계를 10구간 히스토그램으로 요약.',
 region_district_count:'집단 빈도: 지역별로 집계된 선거구 수.',
 region_avg_votes:'기술통계 평균: 시도 후보 득표 합계 ÷ 그 시도에서 포함된 선거구 수.',
 candidate_vote_distribution:'분포 분석: 원본 후보·투표구별 득표 행 값의 10구간 빈도.',
 margin_distribution:'히스토그램: 각 선거구에서 선두 두 후보의 득표율 차이 10%p 단위 빈도.',
 close_races:'순위 분석: 각 선거구에서 1·2위 격차가 작은 순서.',
 district_leader_share:'비율 분석: 각 선거구의 최다 득표자 득표율.'
};
function showGuide(){el('ofMethodGuide').textContent=GUIDES[el('ofMethod').value]||'선택한 기법의 데이터 조건을 확인하세요.';}
function status(message,isError=false){el('ofStatus').textContent=message;el('ofStatus').classList.toggle('of-error',isError);}
async function getJson(url,options){const r=await fetch(url,options);const data=await r.json();if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data;}
function resetSelectors(){
 const reg=el('ofRegion'),dis=el('ofDistrict');reg.innerHTML='<option value="">전국</option>';dis.innerHTML='<option value="">전체 선거구</option>';
 if(!meta)return;
 for(const name of meta.regions){const o=document.createElement('option');o.value=o.textContent=name;reg.append(o);}
}
function updateDistrict(){const reg=el('ofRegion').value,dis=el('ofDistrict');dis.innerHTML='<option value="">전체 선거구</option>';
 if(!meta||!reg)return;
 for(const d of meta.districts.filter(x=>x.region===reg)){const o=document.createElement('option');o.value=o.textContent=d.district;dis.append(o);}
}
function showSummary(){
 if(!meta)return;
 el('ofSummary').innerHTML=[['자료 구분',meta.is_demo?'교육용 가상 샘플 · 실제 개표 아님':'사용자 제공 CSV · 독립 원본 대조 안 됨'],['실제 인증 여부','미인증 · 원본과 독립 대조 필요'],['원본 제공처',meta.is_demo?'LOCAL_SYNTHETIC_DEMO':meta.source_url],['파일 해시 SHA-256',meta.sha256.slice(0,20)+'…'],['자료 구분','과거 최종 결과 (실시간 아님)'],['사용 행 수',number(meta.rows)],['합계 행 제외',number(meta.summary_rows_excluded)],['시도 / 선거구',`${meta.region_count} / ${meta.district_count}`],['파일 인코딩',meta.encoding]].map(([k,v])=>`<div class="of-summary-row"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');
}
function renderReport(data){
 analysis=data;el('ofTitle').textContent=data.method_label;el('ofRowsCount').textContent=`${data.all_rows}개 결과 · 화면 최대 ${data.rows.length}개`;
 const values=data.rows.filter(r=>r.value!==null&&Number.isFinite(Number(r.value)));const max=Math.max(1,...values.map(r=>Number(r.value)));
 el('ofChart').innerHTML=values.length?values.map((r,i)=>`<div class="of-bar-row"><div class="of-bar-label" title="${esc(r.label)}">${esc(r.label)}</div><div class="of-bar-track"><div class="of-bar-fill" style="width:${Math.max(0,Math.min(100,Number(r.value)/max*100))}%"></div></div><strong>${number(r.value)} ${esc(r.unit)}</strong></div>`).join(''):'<p>유효한 분석 값이 없습니다.</p>';
 el('ofTable').innerHTML=data.rows.map(r=>`<tr><td>${esc(r.label)}</td><td>${r.value===null?'계산 불가':number(r.value)}</td><td>${esc(r.unit)}</td></tr>`).join('');
 el('ofCaveat').textContent=data.caution;showGuide();
}
async function refresh(){if(!meta)return status('샘플이 표시되지 않으면 샘플 불러오기 버튼을 눌러 주세요.',true);
 if(el('ofMethod').value==='candidate_share'&&(!el('ofRegion').value||!el('ofDistrict').value)){
  if(!el('ofRegion').value&&meta.regions.length){el('ofRegion').value=meta.regions[0];updateDistrict();}
  if(!el('ofDistrict').value&&el('ofDistrict').options.length>1){el('ofDistrict').selectedIndex=1;}
  status('후보별 득표율은 한 선거구에서 계산하므로 첫 번째 선거구를 자동 선택했습니다. 다른 선거구도 선택할 수 있어요.');
 }
 try{const q=new URLSearchParams({method:el('ofMethod').value,region:el('ofRegion').value,district:el('ofDistrict').value,limit:'30'});
  renderReport(await getJson('/api/official/analyze?'+q));
 }catch(e){status('계산 중단: '+e.message,true);el('ofChart').replaceChildren();el('ofTable').replaceChildren();}
}
async function loadStatus(){try{const r=await getJson('/api/official/status');if(r.loaded){meta=r;resetSelectors();showSummary();showGuide();status(r.is_demo?'전국 17개 시·도 / 모의 68개 선거구 샘플이 표시됩니다. 실제 선거 결과가 아닙니다.':'사용자 제공 CSV를 분석 중입니다. 공식 원본과 독립 대조한 결과가 아닙니다.');refresh();}}catch(e){status(e.message,true);}}
el('ofDemo').addEventListener('click',async()=>{try{meta=await getJson('/api/official/load-demo',{method:'POST'});resetSelectors();el('ofMethod').value='region_votes';showSummary();showGuide();status('교육용 가상 선거 샘플로 돌아왔습니다. 실제 결과가 아닙니다.');refresh();}catch(err){status(err.message,true);}});
el('ofImport').addEventListener('click',async()=>{
 const file=el('ofFile').files?.[0],url=el('ofUrl').value.trim();
 if(!file)return status('먼저 공식 결과 CSV 파일을 선택해 주세요.',true);
 if(!file.name.toLowerCase().endsWith('.csv')||file.size>35*1024*1024)return status('CSV 35MiB 이하만 입력 가능해.',true);
 if(!url)return status('공식 원본 데이터 URL을 입력해 주세요.',true);
 el('ofImport').disabled=true;status('CSV 구조 및 중복·합계 행 검증 중…');
 try{
  const q=new URLSearchParams({source_url:url,election_name:el('ofName').value.trim()});
  meta=await getJson('/api/official/import?'+q,{method:'POST',body:await file.arrayBuffer(),headers:{'Content-Type':'text/csv'}});
  resetSelectors();showSummary();status(`입력 완료 · ${number(meta.rows)}행 검증 · ${number(meta.summary_rows_excluded)}개 합계 행 제외 · 원본 인증 미완료`);
  el('ofMethod').value='region_votes';refresh();
 }catch(e){status('입력 오류: '+e.message,true)}finally{el('ofImport').disabled=false;}
});
el('ofRegion').addEventListener('change',()=>{updateDistrict();refresh();});
el('ofDistrict').addEventListener('change',refresh);
el('ofMethod').addEventListener('change',()=>{showGuide();refresh();});el('ofRun').addEventListener('click',refresh);
el('ofDownload').addEventListener('click',()=>{
 if(!analysis)return status('먼저 분석 결과를 계산하세요.',true);
 const lines=[['label','value','unit'],...analysis.rows.map(x=>[x.label,x.value??'',x.unit])].map(row=>row.map(x=>'"'+String(x).replaceAll('"','""')+'"').join(','));
 const blob=new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'});const uri=URL.createObjectURL(blob);
 const a=document.createElement('a');a.href=uri;a.download='election_analysis_user_upload_unverified.csv';a.click();URL.revokeObjectURL(uri);
});
function drawReplay(data,step){
 let rows=data.series.map((s,i)=>({name:s.candidate,v:s.points[step],final:s.final_votes,color:['#43d1e9','#f6b45c','#bc9efc','#4fd0a1'][i%4]}));
 let max=Math.max(1,...data.series.map(x=>x.final_votes));
 el('ofReplayChart').innerHTML=rows.map(x=>`<div class="of-bar-row"><div class="of-bar-label">${esc(x.name)}</div><div class="of-bar-track"><div class="of-bar-fill" style="width:${x.v/max*100}%;background:${x.color}"></div></div><strong>${number(x.v)} 표</strong></div>`).join('');
 el('ofReplayStage').textContent=`가상 단계 ${step}/${data.stages} · 실제 개표 시각 아님`;
}
function stopReplay(){if(replayTimer){clearInterval(replayTimer);replayTimer=null;}}
el('ofReplayStop').addEventListener('click',()=>{stopReplay();el('ofReplayStage').textContent='가상 재생 중지';});
el('ofReplay').addEventListener('click',async()=>{
 const reg=el('ofRegion').value,dis=el('ofDistrict').value;
 if(!reg||!dis)return status('가상 재생하려면 시도와 개별 선거구를 선택하세요.',true);
 stopReplay();try{
  const q=new URLSearchParams({region:reg,district:dis,stages:20});const d=await getJson('/api/official/replay?'+q);let step=0;drawReplay(d,step);
  replayTimer=setInterval(()=>{step++;drawReplay(d,step);if(step>=d.stages)stopReplay();},550);
  status('주 의: 가상 재생 중. 시각별 실제 개표 기록이 아니라 난수로 나눈 최종 결과야.');
 }catch(e){status(e.message,true)}
});
showGuide();loadStatus();
})();
