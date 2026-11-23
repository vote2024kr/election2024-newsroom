/* NEWSROOM 2024 patch. Only adds panels and makes the integrated room mode-aware.
   Does not delete or replace the original UI or WebSocket simulator. */
(()=>{'use strict';
const $=(q,ctx=document)=>ctx.querySelector(q), $$=(q,ctx=document)=>[...ctx.querySelectorAll(q)];
const esc=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const fmt=x=>Number(x||0).toLocaleString('ko-KR');
let data=null, currentDraft=null;
async function api(path,options={}){const resp=await fetch(path,{cache:'no-store',...options});let j=await resp.json();if(!resp.ok)throw Error(typeof j.detail==='string'?j.detail:'요청 실패');return j}
function div(cls,html){const d=document.createElement('div');d.className=cls;d.innerHTML=html;return d}
function infoBar(){return `<p class="ne-footnote">출처: 중앙선거관리위원회 「제22대 국회의원선거 투표율 분석」 · <a href="/api/v2/report.pdf" target="_blank" rel="noopener">PDF 원문 보기</a> · <a href="https://www.data.go.kr/data/15025527/fileData.do" target="_blank" rel="noopener">지역구 개표자료</a> · <a href="https://www.data.go.kr/data/15144273/fileData.do" target="_blank" rel="noopener">비례대표 개표자료</a><br>실제 확정 자료이며 시간대별 개표 기록이 아닙니다. 표본조사 수치는 전수집계로 표시하지 않습니다.</p>`}
function seatBars(){return data.party_seats.map((x,i)=>`<div class="ne-seat-row"><span>${esc(x.party)}</span><div class="ne-track"><i style="width:${x.total/300*100}%;background:${['#35c6e5','#f16b90','#9785ed','#ecad5d','#69bda0','#9aaacc'][i]}"></i></div><strong>${x.total}석</strong><small>지역구 ${x.constituency} · 비례 ${x.proportional}</small></div>`).join('')}
function bars(obj){return Object.entries(obj).map(([k,v])=>`<div class="ne-minirow"><span>${esc(k)}</span><div class="ne-track"><i style="width:${v}%;background:#40c4e3"></i></div><b>${Number(v).toFixed(1)}%</b></div>`).join('')}
function methodological(){return `<div class="ne-methods"><h3>집계·조사 기준을 정확히 구분합니다</h3><div class="ne-methodgrid">${data.methodology.map(x=>`<div class="ne-method"><b>${esc(x.label)} <small>(${esc(x.method)})</small></b><p>${esc(x.denominator)}</p><small>선관위 PDF 인쇄 ${esc(x.pages)}</small></div>`).join('')}</div><p class="ne-amber">※ '전국 1,505개'는 국회의원 지역구가 아니라 <b>투표구</b>입니다. 전체 선거인 표본조사에는 선정 투표구의 사전투표 참여 기록도 포함됩니다. 선거일 투표율 51.8%는 '이미 다른 방식으로 투표한 사람을 제외한 표본 선거인'이 분모입니다.</p>${infoBar()}</div>`}
function eHead(t,sub=''){return `<div class="ne-hd"><h2>${esc(t)}</h2>${sub?`<p>${esc(sub)}</p>`:''}</div>`}
function qnaHtml(){return `<section class="ne-card ne-qa">${eHead('선관위 자료에 자유롭게 질문하기','원본에서 확인되는 사실만 답합니다. 확인되지 않은 질문은 확인 불가로 표시합니다.')}
<div class="ne-quick">${['사전투표는 전수조사인가요?','선거일 투표율 51.8%의 기준은?','20대 후반 남녀 투표율 격차는?','비례대표 의석수는?','253개와 254개는 왜 다른가요?'].map(q=>`<button type="button" class="ne-example" data-ne-q="${esc(q)}">${esc(q)}</button>`).join('')}</div>
<div class="ne-qline"><input class="ne-question" type="text" aria-label="선거 데이터 자유 질문" placeholder="질문을 직접 입력하세요. 예: 사전투표는 전수조사인가?" maxlength="350"><button class="ne-ask" type="button">근거 질문하기</button></div><div class="ne-answer" aria-live="polite">질문을 입력하면 중앙선관위 보고서·확인된 개표 결과를 검색합니다.</div><p class="ne-footnote">규칙 기반 원문 검색형 질의응답입니다. 외부 LLM·벡터 RAG를 사용했다고 주장하지 않습니다.</p></section>`}
function articleHtml(){return `<section class="ne-card ne-story">${eHead('실제 자료에서 기사 초안 만들기','확인된 수치를 주제로 선택하면 기사 제목·리드문·본문과 근거를 생성합니다. 사람이 검수한 후 승인합니다.')}
<div class="ne-formrow"><label>자료 주제 <select class="ne-topic"><option value="overall">전체 투표율·이전 총선 비교</option><option value="age">연령별 투표율</option><option value="gender">성별 투표율</option><option value="early">사전투표·선거일 투표</option><option value="overseas">재외·국외부재자 투표</option><option value="seats">최종 정당별 의석(지역구+비례)</option></select></label><button type="button" class="ne-draft">근거 기사 초안 생성</button></div>
<div class="ne-storyfields" hidden><label>제목 <input class="ne-title" maxlength="350"></label><label>리드문 <textarea class="ne-lead" rows="3"></textarea></label><label>본문 <textarea class="ne-body" rows="5"></textarea></label><p class="ne-evidence"></p><div class="ne-formrow"><label>검수자 <input class="ne-editor" placeholder="검수자 식별자"></label><label>검수 내용 <input class="ne-reason" placeholder="원문 수치와 출처를 대조했는지 기재"></label></div><div class="ne-formrow"><button class="ne-review" type="button">검수 전 내용 저장</button><button class="ne-approve" type="button">편집자 승인</button></div><div class="ne-result" aria-live="polite"></div></div>${infoBar()}</section>`}
function wireQA(root){$$('.ne-qa',root).forEach(box=>{const input=$('.ne-question',box),out=$('.ne-answer',box),btn=$('.ne-ask',box);const ask=async()=>{const q=input.value.trim();if(!q){out.textContent='질문을 입력하세요.';return}out.textContent='원문 확인 중…';try{const d=await api('/api/v2/question',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});out.innerHTML=`<b>${esc(d.status)}</b><p>${esc(d.answer)}</p>`+(d.evidence.length?d.evidence.map(x=>`<small>근거: ${esc(x.source)} ${esc(x.pages)} · <a href="${esc(x.url)}" target="_blank" rel="noopener">원문 열기</a></small>`).join('<br>'):'<small>현재 제공된 자료에서 근거를 찾지 못했습니다.</small>')}catch(e){out.textContent=e.message}};btn.onclick=ask;input.onkeydown=e=>{if(e.key==='Enter')ask()};$$('[data-ne-q]',box).forEach(b=>b.onclick=()=>{input.value=b.dataset.neQ;ask()})})}
function wireStories(root){$$('.ne-story',root).forEach(box=>{const f=$('.ne-storyfields',box),res=$('.ne-result',box);$('.ne-draft',box).onclick=async()=>{try{const d=await api('/api/v2/draft',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic:$('.ne-topic',box).value,mode:'real'})});currentDraft=d;f.hidden=false;$('.ne-title',box).value=d.title;$('.ne-lead',box).value=d.lead;$('.ne-body',box).value=d.body;$('.ne-evidence',box).innerHTML=`근거: ${esc(d.source)} · ${esc(d.source_pages)} · <a href="${esc(d.source_url)}" target="_blank" rel="noopener">원문 확인</a> · 기사 상태: 검수 전`;res.textContent='원문 수치를 확인하고 편집자가 검수하세요.';}catch(e){res.textContent=e.message}};async function review(approve){if(!currentDraft){res.textContent='먼저 기사 초안을 생성하세요.';return}try{const d=await api('/api/v2/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({article_id:currentDraft.article_id,title:$('.ne-title',box).value,lead:$('.ne-lead',box).value,body:$('.ne-body',box).value,editor:$('.ne-editor',box).value,reason:$('.ne-reason',box).value,approve})});res.textContent=d.status+' · '+d.notice;}catch(e){res.textContent='검증/승인 보류: '+e.message}}$('.ne-review',box).onclick=()=>review(false);$('.ne-approve',box).onclick=()=>review(true)})}
function realPanelHtml(){return `<div class="ne-real-head">${eHead('2024년 제22대 국회의원선거 확정 결과','이 화면은 확정 집계 자료를 사용합니다. 시간대별 실시간 개표를 재현하지 않습니다.')}<span class="ne-chip">개표 완료</span></div><div class="ne-kpis"><div>최종 전체 투표율<strong>67.0%</strong><small>중앙선관위 확정 집계</small></div><div>전체 의석<strong>300석</strong><small>지역구 254석 · 비례 46석</small></div><div>사전투표율<strong>31.3%</strong><small>통합선거인명부 전수조사</small></div><div>분석 표본<strong>10.1%</strong><small>1,505개 투표구 · 448만 811명</small></div></div>
<section class="ne-card">${eHead('정당별 의석 현황 · 지역구 + 비례대표')}<div class="ne-seats">${seatBars()}</div><p class="ne-footnote">의석수는 최종 선거 결과에 관한 통계이며 정당별 득표율이 아닙니다. 출처: 중앙선관위 개표 결과와 2024년 4월 11일 개표완료 보도.</p></section>
<div class="ne-duo"><section class="ne-card">${eHead('연령별 전체 선거인 투표율','전국 1,505개 투표구의 전체 선거인 표본조사')}${bars(data.age_total_sample)}</section><section class="ne-card">${eHead('성별 투표율 · 서로 다른 조사기준')}<h3>전체 선거인 투표율 (표본조사)</h3>${bars(data.gender_total_sample)}<h3>사전투표율 (전수조사)</h3>${bars({'남성':data.early.male,'여성':data.early.female})}<p class="ne-footnote">두 그래프는 조사 대상과 분모가 다릅니다.</p></section></div>
<section class="ne-card">${eHead('지역별 실제 최종 투표율','전체 선거인 기준 · 실제 확정 집계')}${bars(data.regional_final_turnout)}</section>
<section class="ne-card">${eHead('비례대표 개표와 지역구 개표의 단위') }<p>${esc(data.aggregation_notice)}</p>${infoBar()}</section>${methodological()}${articleHtml()}${qnaHtml()}`}
function correctionText(){
 const replacements=[
  [/개표결과\.xlsx\s*\(사용자 제공\)/g,'개표결과.xlsx (원자료 생산: 중앙선거관리위원회)'],
  [/시[·ㆍ]도별 표본 투표율/g,'시·도별 전체 선거인 투표율 (1,505개 투표구 · 선거인 10.1% 표본조사)'],
  [/비례대표 253개 구[·ㆍ]시[·ㆍ]군 합계행 및 전국 합계행/g,'비례대표 구·시·군 합계행 253개 및 전국 합계행 (지역구 선거구 254개와 단위가 다름)'],
  [/전국 1505개 선거구/g,'전국 1,505개 투표구'],
 ];
 // Only existing explanatory text nodes: never interfere with field content, code, control values or mock mode.
 const host=$('.workspace')||$('#view-analytics')||document.body;
 const walker=document.createTreeWalker(host,NodeFilter.SHOW_TEXT);let n,limit=0;
 while((n=walker.nextNode())&&limit++<20000){if(!n.parentElement||/^(SCRIPT|STYLE|TEXTAREA|INPUT|OPTION)$/.test(n.parentElement.tagName))continue;
  if(!/개표결과\.xlsx|253개 구|1505개 선거구|시[·ㆍ]도별 표본 투표율/.test(n.nodeValue))continue;
  for(const [re,rep] of replacements)n.nodeValue=n.nodeValue.replace(re,rep)
 }
}
function standaloneMain(){
 const workspace=$('.workspace'), article=$('#view-articles'), analytic=$('#view-analytics');
 if(!workspace)return;
 const modeControls=div('ne-mode-controls',`<span>선거 데이터 확인</span><a href="/project1?mode=real">2024 실제 확정 결과 · 통합운영실</a><a href="/project1?mode=demo">교육용 모의 개표 · 통합운영실</a>`);
 const link=$('.project1-integrated-link');if(link){link.insertAdjacentElement('afterend',modeControls);link.href='/project1?mode=real';link.textContent='✦ 프로젝트 1 · 실제 확정 결과 / 통합 운영실'}
 if(article){const group=div('ne-extension',articleHtml()+qnaHtml());article.appendChild(group);wireStories(group);wireQA(group)}
 if(analytic){const group=div('ne-extension',`<section class="ne-card"><h2>중앙선관위 성별·연령별 투표율 (원본 구분)</h2>${methodological()}<div class="ne-duo"><div><h3>전체 선거인 (표본조사)</h3>${bars(data.gender_total_sample)}</div><div><h3>사전투표 (전수조사)</h3>${bars({'남성':data.early.male,'여성':data.early.female})}</div></div></section>`);analytic.appendChild(group)}
 const official=$('#view-official');if(official)official.appendChild(div('ne-extension',`<section class="ne-card"><h2>개표 결과의 집계 단위 확인</h2><p>${esc(data.aggregation_notice)}</p><p>두 선거의 원본 출처는 중앙선거관리위원회입니다. 파일을 로컬로 전달한 사람을 데이터 생산 기관으로 표시하지 않습니다.</p>${infoBar()}</section>`));
 const studio=$('#view-studio');if(studio)studio.appendChild(div('ne-extension',`<section class="ne-card"><h2>실제 2024년 총선 CG용 정당별 의석</h2><div class="ne-seats">${seatBars()}</div><p class="ne-footnote">원래의 모의 개표 CG도 보존합니다. 이 블록은 2024년 최종 의석 기준입니다.</p></section>`));
 correctionText();
 // Avoid a full workspace TreeWalker on every chart/table DOM change. In 2024
 // PostgreSQL mode the labels are already corrected when the page is built.
 // For demo mode the corrections are batched rather than repeatedly scanning.
 let scheduled=false;
 const observer=new MutationObserver(()=>{
  if(window.REAL_NEWSROOM_ACTIVE||scheduled)return;
  scheduled=true;
  setTimeout(()=>{scheduled=false;if(!window.REAL_NEWSROOM_ACTIVE)correctionText()},250);
 });
 observer.observe(workspace,{subtree:true,childList:true,characterData:true});
}
function integratedMain(){
 const main=$('main');if(!main)return;
 const warning=$('.warning');
 const bar=div('ne-integrated-mode',`<span>표시할 데이터:</span> <button class="ne-mode-real">2024 실제 확정 결과</button><button class="ne-mode-demo">기존 교육용 모의 개표</button>`);
 if(warning)warning.insertAdjacentElement('afterend',bar);else main.insertAdjacentElement('beforebegin',bar);
 const full=div('ne-integrated-actual',realPanelHtml());main.insertBefore(full,main.firstChild);
 const saved=(new URLSearchParams(location.search).get('mode')||localStorage.getItem('ne24_mode')||'real');
 function setMode(mode){const isReal=mode==='real';localStorage.setItem('ne24_mode',mode);full.hidden=!isReal;
   $$('.stats,.broadcast,.grid,.limits',main).forEach(x=>x.hidden=isReal);
   $('.ne-mode-real',bar).classList.toggle('chosen',isReal);$('.ne-mode-demo',bar).classList.toggle('chosen',!isReal);
   if(warning)warning.innerHTML=isReal?'<b>2024 제22대 총선 확정 결과 · 중앙선거관리위원회 자료</b> | 실시간 개표 아님 · 표본과 전수조사 구분 · 기존 모의자료는 별도 보존': '<b>교육용 모의 개표 · 실제 선거와 무관</b> | 후보 A/B/C와 표수는 난수로 생성됩니다.';
   const header=$('header p');if(header)header.textContent=isReal?'확정 결과 → 원문 근거 → 기사 초안 → 사람 검수':'모의 개표 → 데이터 분석 → 근거 검색 → 기사 → 규칙 검증 → 사람 승인';
 }
 $('.ne-mode-real',bar).onclick=()=>setMode('real');$('.ne-mode-demo',bar).onclick=()=>setMode('demo');setMode(saved==='demo'?'demo':'real');wireQA(full);wireStories(full);
}
async function init(){try{data=await api('/api/v2/summary');if(location.pathname==='/project1'||location.pathname==='/project1/'){integratedMain()}else{standaloneMain()} }catch(e){console.warn('선관위 자료 보완 패치 확인 필요:',e)}}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
