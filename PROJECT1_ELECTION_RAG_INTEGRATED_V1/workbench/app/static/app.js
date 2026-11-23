(()=>{
'use strict';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const e=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>(typeof n==='number'?n.toLocaleString('ko-KR',{maximumFractionDigits:4}):String(n??'—'));
const state={catalog:[],dataset:null,method:null,result:null,filterIndex:0,busy:false};
const palette=['#11a2ba','#eb9f51','#7054bf','#57bd91','#ca6989','#637e9a','#bdba55','#d77a47'];
const opts=['xCol','yCol','groupCol','dateCol','textCol'];
function showToast(t){const el=$('#toast');el.textContent=t;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),3000)}
async function api(url,params={}){const r=await fetch(url,params);let body;try{body=await r.json()}catch{throw Error('서버 응답을 읽을 수 없습니다.')};if(!r.ok){const detail=body.detail??body.error??'요청 실패';throw Error(typeof detail==='string'?detail:JSON.stringify(detail))};return body}
function selectedColumns(){if(!state.dataset)return[];return state.dataset.profile.columns}
function selectOptions(select,columns,numericOnly=false){const previous=select.value;const fields=numericOnly?columns.filter(c=>c.kind==='numeric'):columns;
 select.innerHTML='<option value="">선택 안 함</option>'+fields.map(c=>`<option value="${e(c.column)}">${e(c.column)} (${c.kind==='numeric'?'숫자':c.kind==='datetime_hint'?'날짜':'범주'})</option>`).join('');
 if(fields.some(c=>c.column===previous))select.value=previous;
}
function fillSelectors(){const cols=selectedColumns();for(const id of opts)selectOptions($('#'+id),cols,id==='xCol'||id==='yCol');
 const nums=cols.filter(c=>c.kind==='numeric').map(c=>c.column);const groups=cols.filter(c=>c.kind!=='numeric').map(c=>c.column);const dates=cols.filter(c=>c.kind==='datetime_hint').map(c=>c.column);
 const prefer=(id,...names)=>{const c=names.find(n=>cols.some(x=>x.column===n));if(c)$('#'+id).value=c;};
 prefer('xCol','pm10','amount','votes','views',nums[0]);prefer('yCol','pm25','quantity',nums.find(x=>x!==$('#xCol').value));
 prefer('groupCol','region','category','topic','candidate','channel',groups[0]);prefer('dateCol','day','date','reported_at',dates[0]);prefer('textCol','title','text','body',groups[0]);
 $('#featureChips').innerHTML=cols.filter(c=>c.kind==='numeric').map(c=>`<label><input type="checkbox" class="feature" value="${e(c.column)}" ${[nums[0],nums[1]].includes(c.column)?'checked':''}>${e(c.column)}</label>`).join('')||'<span class="muted">수치 열이 없습니다.</span>';
 for(const f of $$('.filter-column'))selectOptions(f,cols);
}
function drawTable(el,columns,rows){if(!columns.length){el.innerHTML='<tbody><tr><td>표시할 계산 데이터가 없습니다.</td></tr></tbody>';return}
 el.innerHTML='<thead><tr>'+columns.map(c=>`<th>${e(c)}</th>`).join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+columns.map(c=>`<td>${e(fmt(r[c]))}</td>`).join('')+'</tr>').join('')+'</tbody>';
}
function updateDataset(d){state.dataset=d;state.result=null;$('#kindSelect').value=d.kind;$('#dataMode').textContent=d.origin==='sample'?'가상 샘플 데이터':'사용자 파일 · 미검증';$('#dataMode').style.background=d.origin==='sample'?'#21556b':'#675236';
 $('#datasetInfo').classList.remove('hidden');$('#datasetName').textContent=d.name;$('#datasetSource').textContent=d.source+' · '+d.at.slice(0,19)+' UTC · 원본 자동 검증 안 됨';
 $('#heroRows').textContent=fmt(d.profile.rows);
 $('#datasetMetrics').innerHTML=`<div class="meta-card"><strong>${fmt(d.profile.rows)}</strong><small>행</small></div><div class="meta-card"><strong>${fmt(d.profile.columns.length)}</strong><small>열</small></div>`;
 $('#columnChips').innerHTML=d.profile.columns.map(c=>`<span class="chip ${c.kind==='numeric'?'numeric':''}" title="결측 ${c.missing}">${e(c.column)} · ${c.kind==='numeric'?'숫자':c.kind==='datetime_hint'?'날짜':'문자'} (${c.distinct}종)</span>`).join('');
 drawTable($('#sourcePreview'),d.profile.column_names,d.preview);fillSelectors();renderMethods();$('#resultEmpty').classList.remove('hidden');$('#resultContent').classList.add('hidden');$('#historyList').innerHTML='<p class="muted">분석 이력이 없습니다.</p>';
 if(d.kind==='election')selectMethod('election_votes');else if(d.kind==='news')selectMethod('text_frequency');else if(d.kind==='air')selectMethod('timeseries');else selectMethod('summary');
}
function renderMethods(){let category=$('#methodCategory').value,search=$('#methodSearch').value.trim().toLowerCase();let rec=new Map((state.dataset?.recommended??[]).map(x=>[x.id,x]));
 const a=state.catalog.filter(x=>(category==='all'||x.category===category)&&(!search||[x.name,x.category,x.needs].join(' ').toLowerCase().includes(search)));
 $('#methodCount').textContent=`${a.length} / ${state.catalog.length} METHODS`;
 $('#methodCards').innerHTML=a.map(m=>{const r=rec.get(m.id);const missing=r?.missing?.join(', ');return `<button class="method-card ${state.method===m.id?'selected':''}" data-method="${e(m.id)}"><span class="mc-top"><span>${e(m.category)}</span><span class="mc-status ${missing?'needs':''}">${missing?'조건 확인':'선택 가능'}</span></span><strong>${e(m.name)}</strong><small>${e(m.chart)} · ${e(m.needs)}</small></button>`}).join('');
 $$('.method-card').forEach(b=>b.addEventListener('click',()=>selectMethod(b.dataset.method)));
}
function selectMethod(id){const m=state.catalog.find(x=>x.id===id);if(!m)return;state.method=id;renderMethods();$('#methodTitle').textContent=m.name;$('#methodNeeds').textContent='필요: '+m.needs;$('#methodCaution').textContent='해석 주의: '+m.caution;
 const sets={quality:[],summary:['xCol','bins'],frequency:['groupCol'],group_summary:['groupCol','xCol','aggregation'],histogram:['xCol','bins'],timeseries:['xCol','dateCol','aggregation','frequency','window'],correlation:['xCol','yCol'],regression:['xCol','yCol'],welch:['xCol','groupCol'],chi_square:['xCol','groupCol'],bootstrap:['xCol','bins','repeats'],kmeans:['clusters'],pca:[],text_frequency:['textCol'],election_votes:[],election_margin:[],election_progress:[]};
 const visible=new Set([...(sets[id]||[]),'missing']);for(const field of ['xCol','yCol','groupCol','dateCol','textCol','aggregation','missing','frequency','window','bins','clusters','repeats']){$('#'+field).closest('label').hidden=!visible.has(field)}
 $('.feature-panel').hidden=!['kmeans','pca'].includes(id);
 
}
function addFilter(){if($$('.filter-row').length>=4){showToast('필터는 최대 4개입니다.');return};const row=document.createElement('div');row.className='filter-row';row.innerHTML=`<select class="filter-column" aria-label="조건 열"></select><select class="filter-op" aria-label="비교 연산자"><option value="equals">같음</option><option value="not_equals">같지 않음</option><option value="contains">문자 포함</option><option value="gt">초과</option><option value="gte">이상</option><option value="lt">미만</option><option value="lte">이하</option><option value="date_from">날짜 시작</option><option value="date_to">날짜 종료</option></select><input class="filter-value" placeholder="값 · 예: 서울 또는 35" aria-label="조건 값"><button title="조건 삭제">✕ 삭제</button>`;
 $('#filters').append(row);selectOptions(row.querySelector('.filter-column'),selectedColumns());row.querySelector('button').addEventListener('click',()=>row.remove());
}
function collectFilters(){return $$('.filter-row').filter(n=>n.querySelector('.filter-column').value).map(n=>({column:n.querySelector('.filter-column').value,op:n.querySelector('.filter-op').value,value:n.querySelector('.filter-value').value.trim()}));}
function getOptions(){const get=id=>$('#'+id).value;return {x:get('xCol'),y:get('yCol'),group:get('groupCol'),date:get('dateCol'),text:get('textCol'),
  aggregation:get('aggregation'),frequency:get('frequency'),window:+get('window'),bins:+get('bins'),clusters:+get('clusters'),repeats:+get('repeats'),seed:42,features:$$('.feature:checked').map(x=>x.value)};}
function setRunning(on,msg,isError=false){state.busy=on;$('#runAnalysis').disabled=on;$('#runAnalysis').textContent=on?'분석 계산 중…':'↻ 선택 조건으로 계산하기';const el=$('#runStatus');el.textContent=msg;el.className=isError?'error':on?'':'good';}
async function run(){if(state.busy)return;if(!state.dataset){showToast('샘플 또는 파일을 먼저 불러오세요.');return}if(!state.method){showToast('통계기법을 먼저 선택하세요.');return}
 setRunning(true,'서버에서 자료를 계산하고 있습니다.');try{const q={dataset_id:state.dataset.id,method:state.method,options:getOptions(),filters:collectFilters(),missing:$('#missing').value};
 const r=await api('/workbench/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(q)});state.result=r;renderResult(r);await refreshHistory();setRunning(false,`계산 완료 · ${fmt(r.filtered_rows)}행 사용 · ${r.method_name}`);$('#resultsArea').scrollIntoView({behavior:'smooth',block:'start'});
 }catch(err){setRunning(false,err.message,true);$('#resultEmpty').classList.remove('hidden');$('#resultContent').classList.add('hidden');$('#resultEmpty').innerHTML=`<span class="empty-icon">⚠</span><h3>분석 조건을 확인하세요.</h3><p>${e(err.message)}</p>`;showToast(err.message)}
}
function renderResult(r){$('#resultEmpty').classList.add('hidden');$('#resultContent').classList.remove('hidden');$('#resultMethod').textContent=r.method_name;$('#resultSource').textContent=`${r.source.name} · 원본 ${fmt(r.input_rows)}행 / 조건 후 ${fmt(r.filtered_rows)}행 · 출처 검증: 미완료`;
 $('#resultTime').textContent=r.ran_at.replace('T',' ').slice(0,19)+' UTC';$('#summaryMetrics').innerHTML=Object.entries(r.summary).map(([k,v])=>`<div class="summary-item"><span>${e(k)}</span><strong class="${String(v).length>13?'small':''}">${e(fmt(v))}</strong></div>`).join('');
 $('#chartTitle').textContent=r.chart.title||r.method_name;$('#chartUnit').textContent=r.chart.unit||'';drawChart(r.chart,$('#chartView'));
 drawTable($('#resultsTable'),r.columns,r.rows);$('#rowCount').textContent=`결과 총 ${r.total_result_rows}행 중 ${r.rows.length}행 표시`;
 $('#warnings').innerHTML=r.warnings.map(x=>`<div class="warning">※ ${e(x)}</div>`).join('');$('#downloadCsv').disabled=false;$('#downloadJson').disabled=false;
}
function svgBase(w=960,h=350){return `<svg viewBox="0 0 ${w} ${h}" role="img" xmlns="http://www.w3.org/2000/svg">`}
function drawChart(c,el){const w=960,labels=(c.labels||[]),series=c.series||[];const unit=c.unit||'';
 if(c.kind==='bar'){const n=Math.min(labels.length,40);if(!n){el.textContent='표시할 데이터가 없습니다.';return}
 const h=Math.max(290,Math.min(1160,n*30+65)),pad=188,right=80,top=18,row=(h-top-35)/n;let content=svgBase(w,h);
 const vals=series[0]?.values||[];const valid=vals.slice(0,n).map(v=>Number(v)||0);const min=Math.min(0,...valid),max=Math.max(...valid,0.01);const span=max-min||1;const x0=pad+(0-min)/span*(w-pad-right);
 content+=`<line x1="${pad}" y1="${top}" x2="${pad}" y2="${h-30}" stroke="#cadce7"/>`;
 for(let i=0;i<n;i++){const y=top+i*row,val=valid[i],x=pad+(val-min)/span*(w-pad-right);let left=Math.min(x,x0),width=Math.max(1,Math.abs(x-x0));content+=`<text class="chart-label" x="${pad-10}" y="${y+row*.58}" text-anchor="end">${e(String(labels[i]).slice(0,25))}</text><rect x="${left}" y="${y+row*.22}" width="${width}" height="${Math.max(8,row*.55)}" fill="${palette[i%palette.length]}" rx="3"/><text class="chart-label" x="${Math.min(w-45,Math.max(x,x0)+6)}" y="${y+row*.58}">${e(fmt(val))}${e(unit)}</text>`;}
 content+=`<text class="chart-label" x="${pad}" y="${h-9}">※ 상위 ${n}개 결과 표시 · 전체 행은 아래 표에서 확인</text></svg>`;el.innerHTML=content;return;
 }
 if(c.kind==='line'){const n=labels.length;if(!n){el.textContent='표시할 시계열이 없습니다.';return}
 const L=75,R=22,T=32,B=70,h=350,pw=w-L-R,ph=h-T-B;
 const all=series.flatMap(s=>s.values||[]).filter(v=>v!==null&&Number.isFinite(Number(v))).map(Number);if(!all.length){el.textContent='수치가 없는 시계열입니다.';return}
 let min=Math.min(...all),max=Math.max(...all);if(min===max){min-=1;max+=1}const sx=i=>L+(n===1?.5:i/(n-1))*pw,sy=v=>T+(max-v)/(max-min)*ph;
 let content=svgBase(w,h);for(let i=0;i<5;i++){const y=T+ph*i/4;content+=`<line class="chart-axis" x1="${L}" y1="${y}" x2="${w-R}" y2="${y}"/><text class="chart-label" x="${L-9}" y="${y+4}" text-anchor="end">${fmt(max-(max-min)*i/4)}</text>`;}
 for(let j=0;j<series.length;j++){const s=series[j];let part='';let paths=[];for(let i=0;i<n;i++){const v=s.values?.[i];if(v===null||v===undefined||!Number.isFinite(Number(v))){if(part){paths.push(part);part=''}continue}part+=(part?' L':'M')+sx(i).toFixed(2)+','+sy(Number(v)).toFixed(2)}if(part)paths.push(part);for(const p of paths)content+=`<path d="${p}" stroke="${palette[j%palette.length]}" stroke-width="3" fill="none"/>`;
 content+=`<rect x="${L+j*185}" y="6" width="12" height="9" fill="${palette[j%palette.length]}"/><text class="chart-label" x="${L+18+j*185}" y="15">${e(s.name)}</text>`;}
 for(const i of [0,Math.floor((n-1)/2),n-1])content+=`<text class="chart-label" x="${sx(i)}" y="${h-43}" text-anchor="middle">${e(String(labels[i]).slice(0,18))}</text>`;
 content+='</svg>';el.innerHTML=content;return;
 }
 if(c.kind==='scatter'){const points=(c.points||[]).filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));if(!points.length){el.textContent='유효 산점도 값이 없습니다.';return}
 const L=69,R=28,T=25,B=55,h=350,pw=w-L-R,ph=h-T-B;let xs=points.map(p=>p.x),ys=points.map(p=>p.y),xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
 if(xmin===xmax){xmin-=1;xmax+=1}if(ymin===ymax){ymin-=1;ymax+=1}const sx=v=>L+(v-xmin)/(xmax-xmin)*pw,sy=v=>T+(ymax-v)/(ymax-ymin)*ph;
 let content=svgBase(w,h);for(let i=0;i<5;i++){const yy=T+i/4*ph,xx=L+i/4*pw;content+=`<line class="chart-axis" x1="${L}" y1="${yy}" x2="${w-R}" y2="${yy}"/><line class="chart-axis" x1="${xx}" y1="${T}" x2="${xx}" y2="${T+ph}"/><text class="chart-label" x="${L-7}" y="${yy+4}" text-anchor="end">${fmt(ymax-(ymax-ymin)*i/4)}</text><text class="chart-label" x="${xx}" y="${h-34}" text-anchor="middle">${fmt(xmin+(xmax-xmin)*i/4)}</text>`;}
 const groups=[...new Set(points.map(p=>p.group))];for(const p of points)content+=`<circle cx="${sx(p.x)}" cy="${sy(p.y)}" r="3.5" fill="${palette[Math.max(0,groups.indexOf(p.group))%palette.length]}" opacity=".65"><title>${e(p.group||'관측')}: ${p.x}, ${p.y}</title></circle>`;
 if(c.fit&&Number.isFinite(c.fit.slope)&&Number.isFinite(c.fit.intercept)){const ya=c.fit.slope*xmin+c.fit.intercept,yb=c.fit.slope*xmax+c.fit.intercept;content+=`<line x1="${sx(xmin)}" y1="${sy(ya)}" x2="${sx(xmax)}" y2="${sy(yb)}" stroke="#ec8c58" stroke-width="3"/>`;}
 content+=`<text class="chart-label" x="${L}" y="${h-8}">※ 최대 350개 관측점 시각화 · 실제 계산은 유효 행 전체</text></svg>`;el.innerHTML=content;return;
 }
 el.textContent='현재 기법의 차트 형식을 찾지 못했습니다. 아래 결과표를 확인하세요.';
}
function download(name,text,mime){const blob=new Blob([text],{type:mime}),u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1000)}
function exportCsv(){const r=state.result;if(!r)return;const q=s=>{let v=String(s??'');if(/^[\s]*[=+@\-]/.test(v))v="'"+v;return '"'+v.replace(/"/g,'""')+'"';};const csv=['\ufeff'+r.columns.map(q).join(','),...r.rows.map(row=>r.columns.map(c=>q(row[c])).join(','))].join('\r\n');download('stat_result_'+r.method+'.csv',csv,'text/csv;charset=utf-8')}
async function refreshHistory(){if(!state.dataset)return;const obj=await api('/workbench/api/datasets/'+encodeURIComponent(state.dataset.id)+'/history');const h=obj.history;$('#historyList').innerHTML=h.length?h.map((v,i)=>`<div class="history-row"><div><strong>${e(v.method_name)}</strong><small>${e(JSON.stringify(v.filters))} · 조건 후 ${fmt(v.filtered_rows)}행 · ${e(v.at)}</small></div><em>실행 ${h.length-i}</em></div>`).join(''):'<p class="muted">분석 이력이 없습니다.</p>'}
function reset(){for(const r of $$('.filter-row'))r.remove();$('#missing').value='drop';$('#aggregation').value='mean';$('#frequency').value='D';$('#window').value='3';$('#bins').value='10';$('#clusters').value='3';$('#repeats').value='500';if(state.dataset)fillSelectors();showToast('분석 조건만 초기화했습니다. 원본은 그대로입니다.')}
async function init(){try{const catalog=await api('/workbench/api/catalog');state.catalog=catalog.methods;const categories=[...new Set(state.catalog.map(m=>m.category))];$('#methodCategory').innerHTML='<option value="all">전체 분야</option>'+categories.map(c=>`<option value="${e(c)}">${e(c)}</option>`).join('');renderMethods();const samples=await api('/workbench/api/samples');$('#sampleButtons').innerHTML=samples.samples.map(s=>`<button class="sample-btn" data-sample="${e(s.name)}"><strong>${e(s.label)}</strong><small>${e(s.name)} · ${(s.size_bytes/1024).toFixed(0)} KB</small></button>`).join('');
 $$('.sample-btn').forEach(b=>b.addEventListener('click',async()=>{b.disabled=true;try{updateDataset(await api('/workbench/api/samples/'+encodeURIComponent(b.dataset.sample)+'/load',{method:'POST'}));showToast('샘플 데이터 불러오기 완료');await run()}catch(err){showToast(err.message)}finally{b.disabled=false}}));
 // Open with an immediately visible example: first run never shows a blank chart.
 const datasetFromNewsroom=new URLSearchParams(location.search).get('dataset');
 let transferred=false;
 if(datasetFromNewsroom){try{updateDataset(await api('/workbench/api/datasets/'+encodeURIComponent(datasetFromNewsroom)));transferred=true;await run();}catch(err){showToast('전달된 CSV를 열지 못했습니다: '+err.message)}}
 if(!transferred){const first=samples.samples.find(s=>s.name==='sample_election.csv')||samples.samples[0];if(first){updateDataset(await api('/workbench/api/samples/'+encodeURIComponent(first.name)+'/load',{method:'POST'}));await run();}}
 }catch(err){$('#runStatus').textContent='프로그램 초기화 오류: '+err.message;$('#runStatus').className='error'}}
$('#uploadForm').addEventListener('submit',async ev=>{ev.preventDefault();const file=$('#fileInput').files[0];if(!file){showToast('업로드할 파일을 선택하세요');return}const fd=new FormData();fd.append('file',file);fd.append('kind',$('#kindSelect').value);fd.append('source',$('#sourceName').value);fd.append('source_url',$('#sourceUrl').value);try{updateDataset(await api('/workbench/api/datasets/upload',{method:'POST',body:fd}));showToast('파일 검사 통과 · 데이터 불러오기 완료');await run()}catch(err){showToast('파일 불러오기 오류: '+err.message)}});
$('#kindSelect').addEventListener('change',async()=>{if(!state.dataset)return;try{const result=await api('/workbench/api/datasets/'+encodeURIComponent(state.dataset.id)+'/kind',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:$('#kindSelect').value})});state.dataset=result;renderMethods();showToast('현재 데이터의 분석 분야를 변경했습니다.')}catch(err){showToast(err.message)}});
$('#methodSearch').addEventListener('input',renderMethods);$('#methodCategory').addEventListener('change',renderMethods);$('#addFilter').addEventListener('click',addFilter);$('#runAnalysis').addEventListener('click',run);$('#resetConditions').addEventListener('click',reset);
$('#exportProcessed').addEventListener('click',async()=>{
 if(!state.dataset){showToast('먼저 데이터 파일이나 샘플을 불러오세요.');return}
 const button=$('#exportProcessed');button.disabled=true;$('#transformStatus').textContent='가공 처리 중…';
 try{
  const payload={dataset_id:state.dataset.id,filters:collectFilters(),missing_policy:$('#transformMissing').value,deduplicate:$('#deduplicate').checked,
    derived:$('#derivedMethod').value,new_column:$('#derivedName').value,x:$('#xCol').value,y:$('#yCol').value};
  const res=await fetch('/workbench/api/transform/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  if(!res.ok){let msg='가공 실패';try{const body=await res.json();msg=body.detail||msg}catch{}throw Error(msg)}
  const blob=await res.blob();const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download='processed_data.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1000);
  $('#transformStatus').textContent=`${res.headers.get('X-Processed-Rows')||'?'}행 가공 CSV 생성 완료. 원본 유지.`;
 }catch(err){$('#transformStatus').textContent='가공 오류: '+err.message;showToast(err.message)}finally{button.disabled=false}
});
$('#downloadCsv').addEventListener('click',exportCsv);$('#downloadJson').addEventListener('click',()=>{if(state.result)download('stat_result_'+state.result.method+'.json',JSON.stringify(state.result,null,2),'application/json;charset=utf-8')});
$('#dateClock').textContent=new Date().toLocaleDateString('ko-KR');init();
})();
