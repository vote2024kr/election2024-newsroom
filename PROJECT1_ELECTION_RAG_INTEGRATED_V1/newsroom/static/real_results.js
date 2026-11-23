/* V1.2: historical 2024 real data view, additive. Original simulation and remaining menus unchanged. */
(()=>{'use strict';
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=x=>Number(x||0).toLocaleString('ko-KR');
const pct=x=>Number(x||0).toFixed(2);
const SHORT={'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','광주광역시':'광주','대전광역시':'대전','울산광역시':'울산','세종특별자치시':'세종','경기도':'경기','강원특별자치도':'강원','충청북도':'충북','충청남도':'충남','전북특별자치도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남','제주특별자치도':'제주'};
const P_COLORS={'더불어민주당':'#428ded','더불어민주연합':'#428ded','국민의힘':'#f36281','국민의미래':'#f36281','조국혁신당':'#bca0ff','개혁신당':'#ffab55','새로운미래':'#51c9bb','진보당':'#d374d3'};
const colors=['#48cde6','#fbad5c','#ed759c','#ad92f4','#69c09e','#bbc9e4'];
const color=(name,i)=>P_COLORS[name]||colors[i%colors.length];
let data=null;let real=true;let reg='서울특별시';let district=null;let prRegion='서울특별시';let prArea='';let chartGroup='overview';let chartRegion='';
let originalTitle={};
const chartItem=(name,v,max,suffix,clr,i)=>`<div class="real-bar-row"><div class="real-bar-name" title="${esc(name)}">${esc(name)}</div><div class="real-bar-track"><div class="real-bar-fill" style="background:${clr||color(name,i)};width:${max?Math.min(100,Math.max(0,100*Number(v)/max)):0}%"></div></div><strong class="real-bar-number">${esc(suffix)}</strong></div>`;
function barList(items,unit='표',max=null){const vmax=max??Math.max(1,...items.map(x=>Number(x.v)||0));return `<div class="real-bar-list">${items.map((x,i)=>chartItem(x.name,x.v,vmax,x.label??(unit==='%'?pct(x.v)+'%':fmt(x.v)+' '+unit),x.color,i)).join('')}</div>`;}
function sourceNote(text){return `<div class="real-chart-note">${esc(text)}</div>`;}
function chartCard(title,subtitle,items,unit='%',note=''){return `<div class="panel real-chart-card"><div class="panel-head"><div><span class="panel-kicker">${esc(subtitle)}</span><h2>${esc(title)}</h2></div></div>${barList(items,unit,unit==='%'?100:null)}${sourceNote(note)}</div>`;}
function top(list,n=8){return list.slice(0,n)}
function view(){return document.querySelector('.nav.active')?.dataset.view||'dashboard';}
function seatLabel(party){return party==='더불어민주당'?'더불어민주당':party}
function renderHeader(){
 $('.header-middle b').textContent='2024 총선 확정 개표 결과';
 $('.topbar .simulation-pill').textContent='● 실제 2024년 최종 개표 자료 · 실시간 아님';
 $('.ticker-label').textContent='FINAL RESULTS · 개표 완료';
 $('#tickerText').textContent='제22대 국회의원선거 · 2024년 4월 10일  |  지역구 254석 · 비례대표 46석  |  개표 완료 100%  |  시각별 개표 기록은 포함되지 않았습니다.';
 $('#connectStatus').textContent='● 과거 확정 자료';
 $('#clock').textContent='선거일 2024-04-10 · 확정 결과';
 $('#realModeBtn').classList.add('selected');$('#mockModeBtn').classList.remove('selected');
 $('.sidebar .sidebar-foot p').textContent='2024년 총선 개표결과 엑셀 · 중앙선관위 투표율 분석 PDF 기준 (업로드 사본)';
 $('.sidebar .sidebar-foot .status-tag').textContent='● FINAL 2024';
 $('.sidebar .sidebar-foot .version').textContent='NEWSROOM LAB · DATA V1.2';
 $('.footerline span:last-child').textContent='2024 확정 결과 · 시각별 기록 없음 · 원본 교차검증 필요';
}
function renderDashboard(){
 if(!data)return;
 const s=data.constituency,p=data.proportional,t=data.turnout;
 const h=$('#view-dashboard .page-heading');h.querySelector('.eyebrow').textContent='2024 · ELECTION FINAL RESULTS';h.querySelector('h1').textContent='전국 개표 종합상황';
 h.querySelector('p').textContent='지역구 254석 + 비례대표 46석 · 제22대 국회의원선거 최종 집계';
 h.querySelector('.data-source').textContent='◈ 자료: 개표결과 엑셀 / 선관위 투표율 분석'+(data.data_backend==='PostgreSQL'?' · PostgreSQL DB 조회':'');$('#stepHeader').textContent='2024.04.10 최종';
 const cards=$$('#view-dashboard .metrics .metric');
 cards[0].querySelector('span').textContent='전국 개표 완료';$('#metricProgress').innerHTML='100.00<em>%</em>';$('#progressFill').style.width='100%';$('#metricProgressSub').textContent='254개 지역구 · 46석 비례';
 cards[1].querySelector('span').textContent='비례대표 투표수';$('#metricCounted').textContent=fmt(p.nation.ballots);cards[1].querySelector('.metric-foot small').textContent='업로드 엑셀 비례대표 전국 합계';cards[1].querySelector('.metric-up').textContent='✓ 확정 결과';
 cards[2].querySelector('span').textContent='국회의원 정수';$('#metricLeader').textContent='300석';$('#metricLead').textContent='지역구 254석 + 비례 46석';
 cards[3].querySelector('span').textContent='전국 투표율';$('#metricConstituency').innerHTML=t.national.final.toFixed(1)+'<em>%</em>';cards[3].querySelector('.metric-foot small').textContent='전국 실제 투표율 · 전체 선거인 기준';cards[3].querySelector('.mini-live').textContent='확정';
 $('#nationalUpdated').textContent='2024.04.10 최종 개표';
 $('#view-dashboard .panel-national h2').textContent='전국 정당별 의석 · 비례대표 득표';
 const sarr=Object.entries(s.seats_by_party).sort((a,b)=>b[1]-a[1]);
 const parr=Object.entries(p.seat_allocation).sort((a,b)=>b[1]-a[1]);
 const combined=[
 {name:'더불어민주당 + 더불어민주연합',v:(s.seats_by_party['더불어민주당']||0)+(p.seat_allocation['더불어민주연합']||0),color:'#428ded'},
 {name:'국민의힘 + 국민의미래',v:(s.seats_by_party['국민의힘']||0)+(p.seat_allocation['국민의미래']||0),color:'#f36281'},
 {name:'조국혁신당',v:p.seat_allocation['조국혁신당']||0,color:'#bca0ff'},
 {name:'개혁신당',v:(s.seats_by_party['개혁신당']||0)+(p.seat_allocation['개혁신당']||0),color:'#ffab55'},
 {name:'새로운미래',v:s.seats_by_party['새로운미래']||0,color:'#51c9bb'},
 {name:'진보당',v:s.seats_by_party['진보당']||0,color:'#d374d3'}];
 $('#nationalVotes').innerHTML=`<div class="real-national-grid"><div><div class="real-section-subtitle">지역구 당선 의석 (${s.total_seats}석)</div>${barList(sarr.map(([name,v])=>({name,v,label:fmt(v)+'석'})),'석',161)}</div><div><div class="real-section-subtitle">비례대표 배분 의석 (${p.seat_count}석)</div>${barList(parr.map(([name,v])=>({name,v,label:fmt(v)+'석'})),'석',18)}</div></div><div class="real-section-subtitle">지역구 + 비례대표 종합 의석 (총 300석 · 연계 정당 별도 표기)</div>${barList(combined.map(x=>({...x,label:fmt(x.v)+'석'})),'석',175)}<div class="real-section-subtitle">비례대표 전국 정당 득표율 · 유효표 ${fmt(p.nation.valid)}표</div>${barList(top(p.nation.parties,5).map(x=>({name:x.party,v:x.share,label:pct(x.share)+'% · '+fmt(x.votes)+'표'})),'%')}`;
 $('#view-dashboard .panel-national .panel-note').textContent='지역구 의석은 254개 선거구의 최다 득표자 기준. 종합 의석은 더불어민주당·더불어민주연합, 국민의힘·국민의미래를 각각 연계 정당으로 합산했습니다. 비례대표 의석 배분은 별도 확정 발표 기준입니다.';
 $('#view-dashboard .map-panel .map-foot').textContent='전국 → 시·도 → 실제 지역구 254개 · 비례대표 구·시·군 단위';
 $('#regionTiles').innerHTML=s.regions.map(x=>`<button class="region-tile hot" data-real-region="${esc(x.name)}"><strong>${esc(SHORT[x.name]||x.name)}</strong><small>지역구 ${x.district_count}석 · 개표 완료</small></button>`).join('');
 const head=$('#view-dashboard .regional-panel thead tr');head.innerHTML='<th>시·도</th><th>지역구</th><th>개표율</th><th>지역구 1위 정당</th><th>당선 의석</th><th></th>';
 $('#regionRows').innerHTML=s.regions.map(x=>{let a=Object.entries(x.seats).sort((u,v)=>v[1]-u[1]);return `<tr><td>${esc(x.name)}</td><td>${x.district_count}석</td><td>100.0%</td><td>${esc(a[0]?.[0]||'-')}</td><td>${esc(a.map(([k,v])=>`${k} ${v}석`).join(' · '))}</td><td><button data-real-region="${esc(x.name)}">상세 →</button></td></tr>`}).join('');
}
function regionsSelect(select,first='전국'){let old=select.value;select.innerHTML=`<option value="">${esc(first)}</option>`+data.constituency.regions.map(r=>`<option value="${esc(r.name)}">${esc(r.name)}</option>`).join('');if(old&&[...select.options].some(x=>x.value===old))select.value=old;}
function renderDistrictList(){
 const all=data.constituency.districts.filter(x=>(!reg||x.region===reg)&&(!$('#districtSearch').value||`${x.region} ${x.district}`.includes($('#districtSearch').value.trim())));
 $('#districtCountLabel').textContent=all.length+'개 선거구';
 $('#districtList').innerHTML=all.map(x=>`<button class="district-item ${district===x.id?'active':''}" data-real-district="${esc(x.id)}"><span class="left"><strong>${esc(x.district)}</strong><small>${esc(x.winner.party)} ${esc(x.winner.name)} 당선</small></span><span class="right">100.0%<small>개표 완료</small></span></button>`).join('');
}
function renderDistrict(){
 if(!data)return;
 $('#view-district .page-heading p').textContent='실제 지역구 254개 결과 및 지역별 비례대표 득표 · 최종 개표';
 $('#view-district .district-detail-panel .panel-kicker').textContent='CONSTITUENCY · FINAL';
 const s=$('#regionSelect');if(!s.querySelector(`[value="${reg}"]`))regionsSelect(s);s.value=reg;
 let d=data.constituency.districts.find(x=>x.id===district);
 if(!d ||(reg&&d.region!==reg)){d=data.constituency.districts.find(x=>!reg||x.region===reg);if(!d)return;district=d.id}
 renderDistrictList();
 $('#districtTitle').textContent=d.region+' '+d.district;$('#districtRegion').textContent='지역구 · 개표 완료';
 $('#districtProgress').textContent='100.0%';$('#districtTotal').textContent=fmt(d.ballots);
 $('#view-district .district-hero .round-counter small').textContent='표 · 실제 투표수';
 $('#districtBar').style.width='100%';
 $('#districtVotes').innerHTML=`<div class="real-winner">🏆 당선 <b>${esc(d.winner.name)}</b> (${esc(d.winner.party)}) · ${fmt(d.winner.votes)}표 (${pct(d.winner.share)}%)</div>`+
 barList(d.candidates.map((c,i)=>({name:c.name+' ('+c.party+')',v:c.share,label:pct(c.share)+'% · '+fmt(c.votes)+'표',color:color(c.party,i)})),'%');
 $('#view-district .district-detail-panel .subtle-box').textContent='유효투표 '+fmt(d.valid)+'표 · 무효표 '+fmt(d.invalid)+'표 · 1·2위 표차 '+fmt(d.margin)+'표. 출처: 개표결과.xlsx / 지역구 시트 '+d.excel_row+'행';
 $('#draftDistrict').textContent='이 실제 결과로 기사 초안 작성 →';
 renderPR();
}
function renderPR(){
 const all=data.proportional.areas;
 let regSelect=$('#realPrRegion'), areaSelect=$('#realPrArea');
 regSelect.innerHTML=data.constituency.regions.map(x=>`<option value="${esc(x.name)}">${esc(x.name)}</option>`).join('');
 if(!data.constituency.regions.some(x=>x.name===prRegion))prRegion=data.constituency.regions[0].name;
 regSelect.value=prRegion;
 const areas=all.filter(x=>x.region===prRegion);
 areaSelect.innerHTML='<option value="">시·도 전체</option>'+areas.map(x=>`<option value="${esc(x.area)}">${esc(x.area)}</option>`).join('');
 if(!areas.some(x=>x.area===prArea))prArea='';areaSelect.value=prArea;
 const agg=prArea?areas.find(x=>x.area===prArea):data.constituency.regions.find(x=>x.name===prRegion);
 let items=prArea?agg.parties:agg.proportional_parties;
 const total=prArea?agg.valid:agg.proportional_valid;
 $('#realPrDistrictChart').innerHTML=`<div class="real-caption">${esc(prRegion)} ${esc(prArea||'전체')} · 비례대표 유효표 ${fmt(total)}표 · 득표율 분모는 해당 지역 비례 유효표</div>`+barList(top(items,12).map((x,i)=>({name:x.party,v:x.share,label:pct(x.share)+'% · '+fmt(x.votes)+'표',color:color(x.party,i)})),'%');
}
function renderArticles(){
 if(!data)return;
 $('#view-articles .page-heading p').textContent='실제 개표 엑셀과 선관위 투표율 PDF의 근거를 확인하고 기사 초안을 작성합니다.';
 $('#view-articles .workflow-tag').textContent='원문 확인 → 초안 → 사람 검수';
}
function makeDraft(){
 const kind=$('#realDraftType').value;let s='',proof='';
 if(kind==='district'){
  const d=data.constituency.districts.find(x=>x.id===district)||data.constituency.districts[0];
  const second=d.candidates[1];
  s=`[검토 전 기사 초안] ${d.region} ${d.district}에서는 ${d.winner.party} ${d.winner.name} 후보가 ${fmt(d.winner.votes)}표(${pct(d.winner.share)}%)로 최다 득표했습니다. ${second?`${second.party} ${second.name} 후보는 ${fmt(second.votes)}표(${pct(second.share)}%)를 얻어 두 후보 간 격차는 ${fmt(d.margin)}표입니다.`:''} 개표자료에 기록된 유효투표수는 ${fmt(d.valid)}표입니다.\n\n[출처] 제22대 국회의원선거 개표결과.xlsx · 지역구 시트 ${d.excel_row}행`;
  proof=`지역구 시트 ${d.excel_row}행 · 득표 합계 재계산 완료 · 미승인 기사 초안`;
 }else if(kind==='proportional'){
  const p=data.proportional;const names=p.nation.parties.slice(0,4);
  s=`[검토 전 기사 초안] 제22대 국회의원선거 비례대표 개표에서 ${names.map(x=>`${x.party} ${fmt(x.votes)}표(${pct(x.share)}%)`).join(', ')} 순으로 득표했습니다. 비례대표 전국 유효투표수는 ${fmt(p.nation.valid)}표입니다. 비례 의석은 국민의미래 18석, 더불어민주연합 14석, 조국혁신당 12석, 개혁신당 2석으로 집계됐습니다.\n\n[출처] 제22대 국회의원선거 개표결과.xlsx · 비례대표 시트 3행. 의석 배분: 개표 결과 별도 자료`;
  proof='비례대표 시트 3행 · 38개 정당 유효표 합계 일치 · 비례 의석은 별도 근거';
 }else{
  s='[검토 전 기사 초안] 중앙선거관리위원회의 제22대 국회의원선거 투표율 분석에 따르면 최종 전국 투표율은 67.0%였습니다. 전체 선거인 표본조사에서 남성 투표율은 66.5%, 여성은 67.9%로 나타났습니다. 연령별로는 20대가 52.4%로 가장 낮았고 70대가 84.7%로 가장 높았습니다. 반면 사전투표는 통합선거인명부를 이용한 전수조사로 남성 33.2%, 여성 29.4%였습니다.\n\n[출처] 중앙선관위 투표율 분석 PDF 인쇄 4쪽, 6쪽, 7쪽, 22~23쪽, 35쪽. 성별·연령별 전체 투표율은 표본조사입니다.';
  proof='PDF 4, 6, 7, 22, 23, 35쪽 · 전수·표본조사 분리 필요';
 }
 $('#realDraftText').value=s;$('#realDraftEvidence').textContent=proof+' · 자동 송고·승인 없음';
}
async function ask(){const q=$('#realQaQuestion').value.trim();if(!q){$('#realQaOutput').textContent='질문을 입력해주세요.';return}
 $('#realQaOutput').textContent='원자료 조회 중…';
 try{const r=await fetch('/api/real/ask?'+new URLSearchParams({q,region:reg,district:data.constituency.districts.find(x=>x.id===district)?.district||''}));if(!r.ok)throw Error('검색 서버 오류');const x=await r.json();
 $('#realQaOutput').innerHTML=`<div>${esc(x.answer)}</div><div class="real-evidence"><b>근거</b>${x.evidence.map(e=>`<div>${e.url?`<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.source)} · 원문 열기</a>`:esc(e.source)}</div>`).join('')||'<div>직접 일치하는 근거 없음</div>'}<small>※ ${esc(x.method)} · 자동 기사 승인 아님</small></div>`;
 }catch(err){$('#realQaOutput').textContent='근거 검색 실패: '+err.message}
}
function renderAnalytics(){
 if(!data)return;
 $('#view-analytics .page-heading p').textContent='연령·성별 투표율(표본조사)과 사전투표(전수조사), 지역구·비례대표 개표 결과를 비교합니다.';
 $('#view-analytics .page-heading .workflow-tag').textContent='2024 확정 결과 · 표본/전수 구분';
 const t=data.turnout, d=data.constituency, p=data.proportional;
 $('#realChartGroup').value=chartGroup;
 const cr=$('#realChartRegion');cr.innerHTML='<option value="">전국</option>'+d.regions.map(x=>`<option value="${esc(x.name)}">${esc(x.name)}</option>`).join('');cr.value=chartRegion;
 const age=chartCard('연령별 전체 투표율','전체 선거인 · 표본 10.1%',Object.entries(t.age).map(([name,v])=>({name,v})),'%', '선관위 PDF 인쇄 23쪽 · 1,505개 투표구 표본조사');
 const sex=chartCard('성별 전체 투표율','표본조사 · 67.2% 기준',Object.entries(t.sex).map(([name,v])=>({name,v})),'%', '선관위 PDF 인쇄 22쪽 · 여성 67.9% / 남성 66.5%');
 const early=chartCard('사전투표 성별 투표율','통합명부 · 전수조사',Object.entries(t.early_sex).map(([name,v])=>({name,v})),'%', '선관위 PDF 인쇄 35쪽 · 남성 33.2% / 여성 29.4%');
 const earlyAge=chartCard('연령별 사전투표율','전국 · 전수조사',Object.entries(t.early_age).map(([name,v])=>({name,v})),'%', '선관위 PDF 인쇄 35쪽 · 전체 선거인 대비 비율');
 const method=chartCard('전체 투표자의 투표방법별 구성','전체 투표자 100% 기준',Object.entries(t.national.vote_method_share).map(([name,v])=>({name,v})),'%', '선관위 PDF 인쇄 22쪽 · 본투표 비중 52.7% / 사전투표 46.7%');
 const region=chartCard('시·도별 전체 투표율','실제 집계 · 표본과 구분',Object.entries(t.region_actual).map(([name,v])=>({name,v})),'%', '선관위 PDF 인쇄 20쪽 · 실제 집계 기준');
 const rs=chartCard('시·도별 표본 투표율','전체 선거인 · 표본조사',Object.entries(t.region_sample).map(([name,v])=>({name,v})),'%', '선관위 PDF 인쇄 25쪽 · 실제 지역별 확정 투표율과 다를 수 있음');
 let px=chartRegion?d.regions.find(x=>x.name===chartRegion)?.proportional_parties:p.nation.parties;
 const pr=chartCard('비례대표 정당별 득표율',chartRegion?(SHORT[chartRegion]||chartRegion)+' · 비례 유효표':'전국 · 비례 유효표',top(px||[],9).map(x=>({name:x.party,v:x.share,label:pct(x.share)+'%'})),'%', '개표결과.xlsx / 비례대표 · 전국 3행 또는 선택 시·도 구·시·군 합계');
 const districtSeats=chartCard('지역구 정당별 당선 의석','전국 · 254석',Object.entries(d.seats_by_party).sort((a,b)=>b[1]-a[1]).map(([name,v])=>({name,v,label:fmt(v)+'석'})),'석', '지역구 시트 · 254개 선거구별 1위 후보');
 const totalSeats=chartCard('지역구 + 비례 종합 의석','총 300석 · 연계 정당별 합산',[{name:'더불어민주당 + 더불어민주연합',v:175,label:'175석'},{name:'국민의힘 + 국민의미래',v:108,label:'108석'},{name:'조국혁신당',v:12,label:'12석'},{name:'개혁신당',v:3,label:'3석'},{name:'새로운미래',v:1,label:'1석'},{name:'진보당',v:1,label:'1석'}],'석','지역구 집계 + 비례대표 의석 · 연계 정당 합산');
 const prSeats=chartCard('비례대표 정당별 배분 의석','전국 · 46석',Object.entries(p.seat_allocation).sort((a,b)=>b[1]-a[1]).map(([name,v])=>({name,v,label:fmt(v)+'석'})),'석', '의석은 득표수로 단순 계산하지 않고 별도 확정 의석 자료를 사용');
 const chtml={overview:[age,sex,pr],ages:[age,sex,chartCard('20대 남녀 세부 비교','표본조사',[
   {name:'20대 후반 남성',v:45.6},{name:'20대 후반 여성',v:58.2},{name:'20대 초반 남성',v:50.1},{name:'20대 초반 여성',v:57.0}],'%', 'PDF 인쇄 28쪽 · 20대 후반 남녀 차이 12.6%p')], early:[early,earlyAge,method],regional:[region,rs],pr:[pr,prSeats],seats:[totalSeats,districtSeats,prSeats]}[chartGroup]||[age,sex,pr];
 $('#realChartGrid').innerHTML=chtml.join('');
 $('#realMethodsNote').innerHTML=`<p><b>① 개표결과</b> 지역구 254개 선거구와 비례대표 253개 구·시·군 합계행 및 전국 합계행에서 추출했습니다. 후보 득표율은 해당 지역구 유효표 기준입니다.</p><p><b>② 투표율</b> 전체·연령·성별 표본조사와 사전투표 전수조사를 구분합니다. 표본의 전국 투표율은 67.2%, 실제 최종 투표율은 67.0%입니다.</p><p><b>③ 해석 주의</b> 연령별 투표율로 특정 정당에 투표했는지 판단할 수 없습니다. 실제 시각별 개표 기록은 없으므로 최종 결과만 표시합니다.</p><p><a href="/api/real/turnout-report.pdf" target="_blank" rel="noopener">선관위 투표율 분석 PDF 원문 보기</a> · 2024 제22대 총선 개표결과.xlsx (사용자 제공)</p>`;
}
function renderActual(){
 if(!real||!data)return;
 // A PostgreSQL payload can be complete while the browser is still painting.
 // Render the visible section first; render other sections on demand.
 renderHeader();
 const selected=view();
 if(selected==='dashboard')renderDashboard();
 else if(selected==='district')renderDistrict();
 else if(selected==='articles')renderArticles();
 else if(selected==='analytics')renderAnalytics();
}

function changeMode(toReal){real=toReal;window.REAL_NEWSROOM_ACTIVE=toReal;document.body.classList.toggle('real-mode',toReal);document.body.classList.toggle('real-data-ready',toReal&&!!data);
 $('#realModeBtn').classList.toggle('selected',toReal);$('#mockModeBtn').classList.toggle('selected',!toReal);
 if(toReal){if(data){try{renderActual();}catch(e){handleRealError(e);}}else if(!loadingRealData){loadRealData();}}else{
  $('.header-middle b').textContent='LIVE SIMULATION';$('.topbar .simulation-pill').textContent='● 교육용 모의 개표 · 실제 선거와 무관';
  $('.ticker-label').textContent='COUNTING NOW';
  const h=$('#view-dashboard .page-heading');h.querySelector('.eyebrow').textContent='2026 · ELECTION BROADCAST SIMULATOR';h.querySelector('p').textContent='전국 현황에서 시·도, 개별 모의 선거구까지 실시간으로 확인합니다.';
  h.querySelector('.data-source').textContent='◈ 자료 출처: 가상 난수 생성기';
  const cards=$$('#view-dashboard .metrics .metric');cards[0].querySelector('span').textContent='전국 모의 개표율';cards[1].querySelector('span').textContent='집계된 모의 표수';cards[2].querySelector('span').textContent='전국 선두 후보';cards[3].querySelector('span').textContent='현재 집계 상황';
  cards[1].querySelector('.metric-foot small').textContent='실시간 시뮬레이션 누적값';
  cards[2].querySelector('.metric-foot small').textContent='2위와 격차 계산 중';
  cards[3].querySelector('.metric-foot small').textContent='254개 가상 선거구';
  $('#view-dashboard .panel-national h2').textContent='전국 후보별 득표 현황';
  $('#view-dashboard .panel-national .panel-note').textContent='* 모든 후보와 수치는 교육용 가상 데이터입니다. 예측·당선 판정이 아닙니다.';
  $('#view-dashboard .map-panel .map-foot').textContent='전국 → 시·도 → 모의 선거구 순으로 상세 보기';
  $('#view-dashboard .regional-panel thead tr').innerHTML='<th>지역</th><th>모의 선거구</th><th>개표율</th><th>선두 후보</th><th>표 차이</th><th></th>';
  $('#view-district .page-heading p').textContent='시·도를 선택하고 해당 지역의 개별 모의 선거구를 비교합니다.';
  $('#view-district .district-detail-panel .panel-kicker').textContent='DISTRICT COUNT REPORT';
  $('#districtBar').style.width='0%';$('#regionSelect').innerHTML='<option value="">전국 전체</option>';
  $('#view-district .district-hero .round-counter small').textContent='표 · 모의 집계';
  $('#view-district .district-detail-panel .subtle-box').textContent='모의 자료입니다. 실제 결과와 무관합니다.';
  $('#connectStatus').textContent='● WebSocket 모의 개표';
  $('#draftDistrict').textContent='이 선거구로 기사 초안 생성 →';
  $('#view-articles .page-heading p').textContent='근거 ID가 연결된 모의 기사 초안을 만들고, 불일치가 있으면 승인을 차단합니다.';
  $('#view-articles .workflow-tag').textContent='DRAFT → CHECK → HUMAN APPROVAL';
  $('#view-analytics .page-heading p').textContent='모의 개표 스냅샷을 이용하는 교육용 통계 분석실입니다.';
  $('#view-analytics .page-heading .workflow-tag').textContent='SIMULATION STATISTICS · NO FORECAST';
  $('.sidebar .sidebar-foot p').textContent='공식 개표 결과와 연결되지 않습니다. 가상의 후보와 난수로 생성한 데이터입니다.';
  $('.sidebar .sidebar-foot .status-tag').textContent='● DEMO MODE ONLY';
  $('.sidebar .sidebar-foot .version').textContent='AI NEWSROOM · EDUCATION V0.7';
  $('.footerline span:last-child').textContent='NO REAL VOTES · NO OFFICIAL API · NO PREDICTIONS';
  if(typeof window.__activateSimulation==='function')window.__activateSimulation();
 }
}
function navigateDistrict(newReg,id=null){if(newReg!==null){reg=newReg;prRegion=newReg||prRegion}district=id||data.constituency.districts.find(x=>!reg||x.region===reg)?.id;renderDistrict();const btn=$('.nav[data-view="district"]');btn?.click();}
function hook(){
 $('#realModeBtn').addEventListener('click',()=>changeMode(true));$('#mockModeBtn').addEventListener('click',()=>changeMode(false));
 document.querySelectorAll('.nav').forEach(b=>b.addEventListener('click',()=>{if(real)setTimeout(renderActual,0)}));
 $('#regionTiles').addEventListener('click',e=>{if(!real)return;const a=e.target.closest('[data-real-region]');if(a){e.preventDefault();e.stopImmediatePropagation();navigateDistrict(a.dataset.realRegion);}},true);
 $('#regionRows').addEventListener('click',e=>{if(!real)return;const a=e.target.closest('[data-real-region]');if(a){e.preventDefault();e.stopImmediatePropagation();navigateDistrict(a.dataset.realRegion);}},true);
 $('#regionSelect').addEventListener('change',e=>{if(!real)return;e.stopImmediatePropagation();reg=e.target.value;district=null;prRegion=reg||'서울특별시';prArea='';renderDistrict();},true);
 $('#districtSearch').addEventListener('input',e=>{if(!real)return;e.stopImmediatePropagation();renderDistrictList();},true);
 $('#districtList').addEventListener('click',e=>{if(!real)return;const a=e.target.closest('[data-real-district]');if(a){e.stopImmediatePropagation();district=a.dataset.realDistrict;renderDistrict();}},true);
 $('#allRegionsBtn').addEventListener('click',e=>{if(!real)return;e.stopImmediatePropagation();reg='';district=null;renderDistrict();},true);
 $('#goDistrict').addEventListener('click',e=>{if(!real)return;e.preventDefault();e.stopImmediatePropagation();navigateDistrict('');},true);
 $('#draftDistrict').addEventListener('click',e=>{if(!real)return;e.preventDefault();e.stopImmediatePropagation();$('#realDraftType').value='district';$('.nav[data-view="articles"]')?.click();setTimeout(makeDraft,0);},true);
 $('#realPrRegion').addEventListener('change',e=>{prRegion=e.target.value;prArea='';renderPR()});
 $('#realPrArea').addEventListener('change',e=>{prArea=e.target.value;renderPR()});
 $('#realQaAsk').addEventListener('click',ask);$('#realQaQuestion').addEventListener('keydown',e=>{if(e.key==='Enter')ask()});
 document.querySelectorAll('[data-real-question]').forEach(b=>b.addEventListener('click',()=>{$('#realQaQuestion').value=b.dataset.realQuestion;ask()}));
 $('#realMakeDraft').addEventListener('click',makeDraft);
 $('#realCopyDraft').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('#realDraftText').value);$('#realDraftEvidence').textContent+=' · 복사 완료';}catch{alert('브라우저가 복사를 허용하지 않았습니다.')}});
 $('#realChartGroup').addEventListener('change',e=>{chartGroup=e.target.value;renderAnalytics()});
 $('#realChartRegion').addEventListener('change',e=>{chartRegion=e.target.value;renderAnalytics()});
}
let loadingRealData=false;
function renderLoadStatus(message,isError=false){
 const panel=$('#realLoadStatus');
 if(panel){
  panel.hidden=false;
  panel.classList.toggle('is-error',isError);
  const status=panel.querySelector('.real-load-message');
  const retry=panel.querySelector('.real-load-retry');
  if(status)status.textContent=message;
  if(retry)retry.hidden=!isError;
 }
}
function handleRealError(error){
 console.error('2024 실제 자료 화면 전환 실패',error);
 document.body.classList.remove('real-data-ready');
 const detail=error?.message||'알 수 없는 오류';
 const msg='2024 확정 결과를 표시하지 못했습니다: '+detail;
 renderLoadStatus(msg,true);
 $('#tickerText').textContent=msg;
 $('#connectStatus').textContent='● 자료 표시 오류';
 $('#clock').textContent='다시 시도 버튼을 누르세요';
}
async function loadRealData(){
 if(loadingRealData)return;
 loadingRealData=true;
 document.body.classList.remove('real-data-ready');
 renderLoadStatus('PostgreSQL에서 2024년 개표·투표율 자료를 읽고 있습니다…');
 $('#tickerText').textContent='실제 개표 결과 데이터를 불러오고 있습니다. 완료 전 가상 개표 수치는 표시하지 않습니다.';
 $('#connectStatus').textContent='● 자료 조회 중';
 const abort=new AbortController();
 const timeout=setTimeout(()=>abort.abort(),20000);
 try{
  const response=await fetch('/api/real/data',{cache:'no-store',signal:abort.signal});
  if(!response.ok)throw Error('DB 자료 요청 실패 (HTTP '+response.status+')');
  const incoming=await response.json();
  if(!incoming?.constituency?.districts||!incoming?.proportional?.areas||!incoming?.turnout?.national)throw Error('선거 데이터 구조가 예상과 다릅니다.');
  if(incoming.constituency.districts.length!==254||incoming.proportional.areas.length!==253)throw Error('지역구 254개·비례 지역 253개 자료 건수가 일치하지 않습니다.');
  if(incoming.data_backend!=='PostgreSQL')throw Error('PostgreSQL이 아닌 자료가 반환됐습니다.');
  data=incoming;
  district=data.constituency.districts.find(x=>x.region===reg)?.id;
  if(real){
   // Let the browser paint loading state before the first real-data DOM update.
   await new Promise(resolve=>setTimeout(resolve,0));
   renderActual();
   document.body.classList.add('real-data-ready');
   $('#connectStatus').textContent='● PostgreSQL 연결됨';
  }
  const panel=$('#realLoadStatus');if(panel)panel.hidden=true;
 }catch(error){
  if(error?.name==='AbortError')error=new Error('20초 이내 DB 응답을 받지 못했습니다. 서버 창에서 오류를 확인하고 다시 시도하세요.');
  handleRealError(error);
 }finally{clearTimeout(timeout);loadingRealData=false;}
}
function init(){
 // A verified result must replace the default simulation placeholders.
 // Even when the browser has yet to receive the SQL response, label this as loading real data.
 try{
  hook();
  $('#realLoadRetry')?.addEventListener('click',loadRealData);
  $('.header-middle b').textContent='2024 총선 · 확정 결과 조회 중';
  $('#clock').textContent='PostgreSQL 자료 확인 중';
  $('.ticker-label').textContent='DATA LOADING';
  $('#view-dashboard .page-heading .eyebrow').textContent='2024 · FINAL RESULTS · LOADING';
  $('#view-dashboard .page-heading .data-source').textContent='◈ PostgreSQL 자료 조회 중';
  loadRealData();
 }catch(error){handleRealError(error);}
}
init();
})();
