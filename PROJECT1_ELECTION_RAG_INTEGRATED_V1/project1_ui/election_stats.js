// Additive, independent election-only analysis panel. Existing newsroom UI untouched.
(()=>{'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const fmt=n=>typeof n==='number'?n.toLocaleString('ko-KR',{maximumFractionDigits:3}):String(n??'—');
let methods=[],districts=[];
async function get(url){const r=await fetch(url);let body;try{body=await r.json()}catch{throw Error('분석 응답을 읽을 수 없습니다.')}if(!r.ok)throw Error(typeof body.detail==='string'?body.detail:'분석 요청 실패');return body}
function method(){return methods.find(x=>x.id===$('analysisMethod').value)}
function regionChanged(){const r=$('analysisRegion').value;const selected=$('analysisDistrict').value;const items=districts.filter(d=>d.region===r);
 $('analysisDistrict').innerHTML='<option value="">전체 선거구</option>'+items.map(d=>`<option value="${esc(d.district)}">${esc(d.district)}</option>`).join('');
 if(items.some(d=>d.district===selected))$('analysisDistrict').value=selected;
}
function methodChanged(){const m=method();const final=m?.source==='final_csv';$('analysisScope').hidden=!final;
 $('analysisStatus').textContent=final?'최종 결과 CSV는 실시간 개표 이력이 아닙니다. 업로드 출처는 독립 검증되지 않았습니다.':
 '실시간처럼 갱신되는 교육용 난수 개표만 분석합니다. 실제 당선 예측이 아닙니다.';
}
function plotBar(chart){const vals=chart.series?.[0]?.values||[];const top=Math.max(1,...vals.map(v=>Math.abs(Number(v)||0)));return chart.labels.slice(0,18).map((lab,i)=>{
 const v=Number(vals[i])||0;const width=Math.min(100,Math.abs(v)/top*100);return `<div class="analysis-bar"><div class="analysis-bar-head"><span>${esc(lab)}</span><b>${esc(fmt(v))}${esc(chart.unit||'')}</b></div><div class="analysis-bar-track"><i style="width:${width.toFixed(2)}%"></i></div></div>`;
 }).join('')}
function plotLine(chart){const labels=chart.labels||[],series=chart.series||[];const all=series.flatMap(s=>s.values||[]).filter(v=>v!==null&&Number.isFinite(Number(v))).map(Number);
 if(!labels.length||!all.length)return '<p>그릴 수 있는 단계별 값이 없습니다.</p>';
 let min=Math.min(...all),max=Math.max(...all);if(min===max){min-=1;max+=1}const W=560,H=190,pad=25;
 const x=i=>pad+(labels.length<=1?.5:i/(labels.length-1))*(W-2*pad);
 const y=v=>pad+(max-v)/(max-min)*(H-2*pad);const colors=['#57ddea','#ffbf7e','#9ceb9e'];
 let content=`<svg class="analysis-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="모의 개표 단계 추세 그래프"><line x1="25" x2="535" y1="165" y2="165" stroke="#7199ab"/>`;
 for(const [j,s] of series.entries()){let part='',paths=[];(s.values||[]).forEach((v,i)=>{if(v===null||!Number.isFinite(Number(v))){if(part)paths.push(part);part='';return}part+=(part?' L':'M')+x(i).toFixed(2)+','+y(Number(v)).toFixed(2)});if(part)paths.push(part);
 for(const path of paths)content+=`<path d="${path}" stroke="${colors[j%colors.length]}" stroke-width="2.7" fill="none"/>`;
 content+=`<text x="${30+j*180}" y="14" fill="${colors[j%colors.length]}" font-size="11">${esc(s.name)}</text>`;
 }
 content+=`<text x="25" y="185" fill="#afc2d9" font-size="10">${esc(labels[0])}</text><text x="530" y="185" fill="#afc2d9" text-anchor="end" font-size="10">${esc(labels[labels.length-1])}</text></svg>`;return content;
}
function show(d){const r=d.result;let chart,cols,rows;
 if(d.method.startsWith('final_')){rows=r.rows||[];cols=['label','value','unit'];chart={kind:'bar',labels:rows.map(x=>x.label),series:[{name:d.name,values:rows.map(x=>x.value)}],unit:rows[0]?.unit||''};}
 else{rows=r.rows||[];cols=(r.columns||[]).map(x=>Array.isArray(x)?x[0]:x);chart=r.chart||{};}
 const headers=(r.columns||[]).map(x=>Array.isArray(x)?x:[x,x]);const labels=d.method.startsWith('final_')?cols.map(x=>[x,({label:'대상',value:'값',unit:'단위'})[x]]):headers;
 const table=rows.slice(0,18).map(row=>`<tr>${labels.map(([key])=>`<td>${esc(fmt(row[key]))}</td>`).join('')}</tr>`).join('');
 $('analysisResults').innerHTML=`<b>${esc(d.name)}</b><p>${esc(d.source_label)}</p>`+
 (chart.kind==='line'?plotLine(chart):plotBar(chart))+
 `<table class="analysis-table"><thead><tr>${labels.map(([,title])=>`<th>${esc(title)}</th>`).join('')}</tr></thead><tbody>${table}</tbody></table>`+
 `<p class="analysis-note">※ ${esc(d.warning)}</p>`;
 $('analysisStatus').textContent=`${rows.length}개 결과 · 외부 공식 원본 검증 안 됨 · ${d.source_mode}`;
}
async function run(){const m=method();if(!m)return;$('analysisRun').disabled=true;$('analysisStatus').textContent='분석 계산 중…';try{
 const qs=new URLSearchParams({method:m.id,limit:'20'});
 if(m.source==='final_csv') {if($('analysisRegion').value)qs.set('region',$('analysisRegion').value);if($('analysisDistrict').value)qs.set('district',$('analysisDistrict').value);}
 const d=await get('/api/project1/election/analyze?'+qs.toString());show(d);
 }catch(e){$('analysisStatus').textContent=e.message;$('analysisResults').textContent='분석 조건을 다시 확인해 주세요.';}finally{$('analysisRun').disabled=false}}
async function init(){try{
 const [catalog,status]=await Promise.all([get('/api/project1/election/methods'),get('/api/official/status')]);methods=catalog.methods;
 $('analysisMethod').innerHTML=methods.map(m=>`<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('');
 districts=status.districts||[];
 $('analysisRegion').innerHTML='<option value="">전국</option>'+(status.regions||[]).map(r=>`<option value="${esc(r)}">${esc(r)}</option>`).join('');
 regionChanged();methodChanged();
 }catch(e){$('analysisStatus').textContent=e.message;}}
 $('analysisMethod').addEventListener('change',methodChanged);$('analysisRegion').addEventListener('change',regionChanged);$('analysisRun').addEventListener('click',run);
 init();
})();
