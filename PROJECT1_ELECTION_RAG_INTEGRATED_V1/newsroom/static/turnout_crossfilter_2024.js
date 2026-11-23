/* 2024 22nd Assembly election: NEC 2024 sampled regional/sex turnout.
   Source: NEC '제22대 국회의원선거 투표율 분석', printed p.29, figure 15.
   No imputed region-by-age or constituency-by-sex breakdowns. */
(() => {
  "use strict";
  const root = document.querySelector("[data-turnout-crossfilter]");
  if (!root) return;
  const regionChart = root.querySelector("#cross-region-bars");
  const sexChart = root.querySelector("#cross-sex-bars");
  const stateLabel = root.querySelector("#cross-selection");
  const msg = root.querySelector("#cross-message");
  const reset = root.querySelector("#cross-reset");
  const heading = root.querySelector("#cross-sex-title");
  const fmt = (n) => Number(n).toFixed(1) + "%";
  let sex = null, region = null, payload = null;
  const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[c]);
  function render() {
    if (!payload) return;
    stateLabel.textContent = "지역: " + (region || "전체") + " · 성별: " + (sex || "전체");
    reset.disabled = !(sex || region);
    msg.textContent = (sex && region) ? region + " " + sex + " 투표율 " + fmt(payload.regions.find(r=>r.region===region)[sex]) :
      region ? region + " 남녀 투표율을 비교합니다. 성별 막대를 선택하면 해당 성별의 지역별 비교가 표시됩니다." :
      sex ? sex + "의 지역별 투표율입니다. 지역 막대를 선택하면 해당 지역 남녀 투표율을 비교합니다." :
      "지역 또는 성별 막대를 클릭하면 두 그래프가 함께 반영됩니다.";
    regionChart.innerHTML = payload.regions.map(r => {
      const selected = region === r.region;
      const male = Number(r["남성"]), female = Number(r["여성"]);
      const cols = sex === "남성" ? [{name:"남성",value:male}] :
                   sex === "여성" ? [{name:"여성",value:female}] :
                   [{name:"남성",value:male},{name:"여성",value:female}];
      return '<div class="cross-reg-item">' +
        '<button type="button" class="cross-reg-btn' + (selected ? " is-selected" : "") + '" data-region="' + escapeHtml(r.region) +
        '" aria-pressed="' + selected + '" title="' + escapeHtml(r.region) + ' 자세히 보기">' +
        '<span class="cross-reg-name">' + escapeHtml(r.region) + '</span><span class="cross-reg-contents">' +
        cols.map(c => '<span class="cross-reg-bar ' + (c.name==="남성"?"is-male":"is-female") +
          '" style="width:' + (Number(c.value)/100*100).toFixed(1) + '%" title="' + c.name + ' '+fmt(c.value)+'"><span>'+fmt(c.value)+'</span></span>').join('') +
        '</span></button></div>';
    }).join('');
    const current = region ? payload.regions.find(r=>r.region===region) : payload.national;
    heading.textContent = region ? region + " 성별 투표율" : "전국 성별 투표율";
    sexChart.innerHTML = ["남성","여성"].map(k=>{
      const chosen=sex===k, value=Number(current[k]);
      return '<button type="button" class="cross-sex-btn'+(chosen?" is-selected":"")+'" data-sex="'+k+'" aria-pressed="'+chosen+'">'+
        '<span>'+k+'</span><span class="cross-sex-track"><span class="cross-sex-fill '+(k==="남성"?"is-male":"is-female")+'" style="width:'+value+'%"></span></span>'+
        '<strong>'+fmt(value)+'</strong></button>';
    }).join('');
    regionChart.querySelectorAll("[data-region]").forEach(b=>b.addEventListener("click",()=>{
      const val=b.dataset.region;region=region===val?null:val;render();
    }));
    sexChart.querySelectorAll("[data-sex]").forEach(b=>b.addEventListener("click",()=>{
      const val=b.dataset.sex;sex=sex===val?null:val;render();
    }));
  }
  reset.addEventListener("click",()=>{sex=null;region=null;render()});
  fetch("/static/turnout_region_sex_2024.json", {cache:"no-store"})
    .then(r=>{if(!r.ok)throw Error("원본 교차표를 불러오지 못했습니다.");return r.json()})
    .then(d=>{
      if(!Array.isArray(d.regions)||d.regions.length!==17||
         d.regions.some(x=>typeof x["남성"]!=="number" || typeof x["여성"]!=="number")) throw Error("원본 교차표 형식 검증 실패");
      payload=d;render();
    })
    .catch(err=>{msg.textContent=err.message; regionChart.textContent="교차 통계를 표시할 수 없습니다."});
})();
