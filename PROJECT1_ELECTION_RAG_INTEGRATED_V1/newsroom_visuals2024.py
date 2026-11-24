"""근거가 있는 2024년 22대 총선 시각화 구성 요소.

실제 선거 결과는 호출자가 제공하는 PostgreSQL 결과 객체만 사용한다.
선거구 경계는 오마이뉴스 MIT 공개자료를 최초 실행 시 1회 받아 검증한 뒤 저장한다.
이 파일을 불러오는 동작만으로는 외부 통신하지 않는다.
"""
from __future__ import annotations
import html
import json
import math
import urllib.request
from collections import Counter
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent
GEOMETRY = ROOT / 'newsroom' / 'static' / 'map_22nd_2024.geojson'
GEO_URL = ('https://raw.githubusercontent.com/vote2024kr/election2024-newsroom/main/'
           'PROJECT1_ELECTION_RAG_INTEGRATED_V1/newsroom/static/map_22nd_2024.geojson')
COLORS = {
    '더불어민주당':'#287bd7', '더불어민주연합':'#61a7ef',
    '국민의힘':'#dc4e62', '국민의미래':'#ed8794',
    '조국혁신당':'#6555d8', '개혁신당':'#e99438',
    '진보당':'#af4bb5', '새로운미래':'#38b6c7', '무소속':'#93a5b8',
}
SHORT = {'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천',
         '광주광역시':'광주','대전광역시':'대전','울산광역시':'울산','세종특별자치시':'세종',
         '경기도':'경기','강원특별자치도':'강원','충청북도':'충북','충청남도':'충남',
         '전북특별자치도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남',
         '제주특별자치도':'제주'}

def esc(v):
    return html.escape(str(v), quote=True)

def _validate_geo(features):
    if len(features)!=254:
        raise ValueError('지도 경계 254개 불일치')
    ids=[x.get('properties',{}).get('id') for x in features]
    if len(set(ids))!=254 or not all(isinstance(x,str) and x.startswith('C') for x in ids):
        raise ValueError('지도 선거구 ID 불일치')
    for f in features:
        if f.get('geometry',{}).get('type') not in ('Polygon','MultiPolygon'):
            raise ValueError('지도 지리정보 형식 불일치')
    return features

@lru_cache(maxsize=1)
def load_geography():
    if GEOMETRY.exists():
        return _validate_geo(json.loads(GEOMETRY.read_text('utf-8'))['features'])
    # Existing current GitHub V5 distributes this file. The pre-design ZIP was
    # produced from an older snapshot, therefore first launch hydrates the file
    # from this verified *public* original. No fabricated polygons are used.
    request=urllib.request.Request(GEO_URL,headers={'User-Agent':'Election2024-SafeMap/1.0'})
    with urllib.request.urlopen(request,timeout=10) as r:
        content=r.read(2_000_001)
    if len(content)>2_000_000:
        raise ValueError('지도 다운로드 자료가 예상보다 큽니다.')
    decoded=json.loads(content.decode('utf-8'))
    features=_validate_geo(decoded['features'])
    GEOMETRY.parent.mkdir(parents=True,exist_ok=True)
    GEOMETRY.write_bytes(content)
    return features

def _rings(geom):
    if geom['type']=='Polygon':
        return geom['coordinates']
    return [ring for poly in geom['coordinates'] for ring in poly]

def _turnout_color(rate):
    """Five distinct shades, light for low turnout and dark for high turnout.

    Based on observed 17-region minimum/maximum rather than invented rates.
    """
    thresholds=(64.0,66.0,68.0,70.0)
    ramp=('#a5dce9','#76c2e0','#4a9dcb','#256b9f','#123c76')
    return ramp[sum(float(rate)>=x for x in thresholds)]

def _svg_shapes(features,results,region='',mode='results',regional_rates=None, navigate='map', selected_id='', full_region='', highlight_ids=None, area=''):
    valid=[f for f in features if not region or f['properties']['region']==region]
    if not valid:
        valid=features
    coords=[(float(x[0])*.80,float(x[1])) for f in valid for ring in _rings(f['geometry']) for x in ring]
    minx=min(x for x,y in coords);maxx=max(x for x,y in coords)
    miny=min(y for x,y in coords);maxy=max(y for x,y in coords)
    width,height=740,700
    k=min((width-45)/max(.001,maxx-minx),(height-35)/max(.001,maxy-miny))
    offsetx=(width-(maxx-minx)*k)/2;offsety=(height-(maxy-miny)*k)/2
    def coords_to_px(p):return offsetx+(p[0]*.80-minx)*k,height-offsety-(p[1]-miny)*k
    def path(geom):
        paths=[]
        for ring in _rings(geom):
            if len(ring)<4:continue
            points=[coords_to_px(p) for p in ring]
            paths.append('M'+' L'.join(f'{x:.1f} {y:.1f}' for x,y in points)+' Z')
        return ' '.join(paths)
    elements=[]; groups={}
    for f in valid:
        prop=f['properties'];key=prop['id'];prov=prop['region'];d=results.get(key)
        if mode=='outline':
            fill='#647e94';opacity='.28';stroke='#7690a6';link=''
        elif mode=='turnout':
            rate=(regional_rates or {}).get(prov,0)
            # Sequential light-to-dark ramp: the higher the verified final
            # regional turnout, the darker the polygon. No interpolated data.
            fill=_turnout_color(rate);opacity='1';stroke='#142c49';link='/safe2024?page=turnout&region='+esc(prov)
        else:
            fill=COLORS.get(d['winner']['party'] if d else '', '#718399');opacity='1';stroke='#122238'
            if navigate == 'explorer':
                if region:
                    link='/safe2024?'+urlencode({'page':'district','region':full_region,'district':key, **({'area':area} if area and highlight_ids and key in highlight_ids else {})})
                else:
                    link='/safe2024?'+urlencode({'page':'district','region':next((rr for rr, short in SHORT.items() if short == prov), prov)})
            elif navigate == 'static':
                link=''
            else:
                link='/safe2024/map?'+urlencode({'region':prov, 'district':key} if region else {'region':prov})
        title=(f'{prov} {prop.get("district","")} · {d["winner"]["name"]} ({d["winner"]["party"]})'
               if d and mode=='results' else (f'{prov} · 투표율 {regional_rates.get(prov,0):.1f}%' if mode=='turnout' else f'{prov} {prop.get("district", "")}'))
        active_class=' vmap-selected' if key==selected_id else ''
        dim_style='opacity:.16;' if highlight_ids and key not in highlight_ids else ''
        shape=f'<path class="vmap-region{active_class}" style="{dim_style}" data-region="{esc(prov)}" fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" stroke-width="{1.15 if region else .7}" fill-rule="evenodd" d="{path(f["geometry"])}"><title>{esc(title)}</title></path>'
        elements.append(f'<a href="{link}" aria-label="{esc(title)}">{shape}</a>' if link else shape)
        groups.setdefault(prov,[]).append(f)
    labels=[]
    if not region:
        for prov,fs in groups.items():
            # Locate the label near a large polygon's bounding box centroid.
            rings=[ring for feat in fs for ring in _rings(feat['geometry'])]
            main=max(rings,key=lambda ring:(max(p[0] for p in ring)-min(p[0] for p in ring))*(max(p[1] for p in ring)-min(p[1] for p in ring)))
            x=(min(p[0] for p in main)+max(p[0] for p in main))/2
            y=(min(p[1] for p in main)+max(p[1] for p in main))/2
            xx,yy=coords_to_px([x,y])
            labels.append(f'<text x="{xx:.1f}" y="{yy:.1f}" class="vmap-label">{esc(prov)}</text>')
    return f'<svg class="vmap-svg" viewBox="0 0 {width} {height}" role="img" aria-label="전국 지역별 선거 결과 지도">'+''.join(elements)+''.join(labels)+'</svg>'

def donut_svg(values,total,title,diameter=184):
    values=[(name,int(val)) for name,val in values if int(val)>0]
    actual=sum(v for _,v in values)
    if actual!=total:
        raise ValueError(f'의석수 검증 실패: {title} {actual}≠{total}')
    circumference=2*math.pi*60
    taken=0
    circles=[]
    for name,n in values:
        length=circumference*n/total
        color=COLORS.get(name,'#8795a5')
        circles.append(f'<circle cx="92" cy="92" r="60" fill="none" stroke="{color}" stroke-width="24" '
                       f'stroke-dasharray="{length:.3f} {circumference-length:.3f}" stroke-dashoffset="{-taken:.3f}" '
                       f'transform="rotate(-90 92 92)"><title>{esc(name)} {n}석</title></circle>')
        taken+=length
    return f'<svg viewBox="0 0 184 184" width="100%" role="img" aria-label="{esc(title)}">'+''.join(circles)+f'<text class="seat-big" x="92" y="89" text-anchor="middle">{total}</text><text class="seat-small" x="92" y="111" text-anchor="middle">의석</text></svg>'

def seat_semicircle_svg(d):
    seats=dict(Counter(d['constituency']['seats_by_party'])+Counter(d['proportional']['seat_allocation']))
    counts=[(name,n) for name,n in seats.items() if n]
    counts.sort(key=lambda x:(-x[1],x[0]))
    palette=[COLORS.get(p,'#8995a6') for p,n in counts for _ in range(n)]
    if len(palette)!=300:raise ValueError('국회 전체 의석 합계는 300석이어야 합니다.')
    rings=[49,47,45,43,41,39,36]
    dots=[];index=0
    for ring,num in enumerate(rings):
        radius=253-ring*18
        for i in range(num):
            theta=math.pi-(i+.5)/num*math.pi
            xx=320+math.cos(theta)*radius
            yy=298-math.sin(theta)*radius
            color=palette[index];index+=1
            dots.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="4.3" fill="{color}"/>')
    return '<svg class="semi-svg" viewBox="0 0 640 322" role="img" aria-label="국회의원 300석 의석 분포 반원 그래프">'+''.join(dots)+f'<text class="seat-big" x="320" y="270" text-anchor="middle">300석</text></svg>'

def _legend(seats):
    return '<div class="seat-legend">'+''.join(f'<span><i style="background:{COLORS.get(p,"#8995a6")}"></i>{esc(p)} <b>{n}석</b></span>' for p,n in seats if n)+'</div>'

def seat_charts(d):
    local=sorted(d['constituency']['seats_by_party'].items(),key=lambda a:-a[1])
    pr=sorted(d['proportional']['seat_allocation'].items(),key=lambda a:-a[1])
    merged=sorted(list(local)+list(pr),key=lambda a:-a[1])
    return f'''<section class="seats-section" aria-label="선거 결과 정당별 의석 시각화">
    <h3>2024년 제22대 국회의원선거 · 확정 의석</h3>
    <p class="vis-muted">지역구 254석 + 비례대표 46석 = 300석 · 선관위 최종 집계 자료</p>
    <div class="donut-grid">
      <div class="vis-card"><h4>지역구 당선 의석</h4>{donut_svg(local,254,'지역구 의석')}{_legend(local)}</div>
      <div class="vis-card"><h4>비례대표 배분 의석</h4>{donut_svg(pr,46,'비례대표 의석')}{_legend(pr)}</div>
    </div>
    <div class="vis-card hemi"><h4>국회 전체 의석 · 300석</h4>{seat_semicircle_svg(d)}{_legend(merged)}</div>
    </section>'''

def _winner_margin_chart(district):
    candidates=sorted(district['candidates'],key=lambda x:-x['votes'])[:2]
    if len(candidates)<2:return ''
    first,second=candidates
    maxval=max(first['votes'],second['votes'])
    items=[]
    for c in candidates:
        ratio=100*c['votes']/maxval if maxval else 0
        color=COLORS.get(c['party'],'#6d9db0')
        items.append(f'<div class="margin-who"><span>{esc(c["name"])} · {esc(c["party"])}</span><b>{c["votes"]:,}표</b></div><div class="margin-track"><div style="width:{ratio:.1f}%;background:{color}"></div></div>')
    return f'<div class="margin-visual">'+''.join(items)+f'<strong>1·2위 득표차 {district["margin"]:,}표</strong></div>'

def map_html(d,region='',district='',mode='results',turnout=None,embed=False):
    # Never produce synthetic region/district shapes when real geography is missing.
    try:
        features=load_geography()
    except Exception as err:
        # Screenshot fallback is explicitly identified, no fake selectable polygons.
        # Neutral silhouette is a mask extracted from the user's original V5 map screenshot.
        if mode=='outline':
            return '<div class="map-notready map-snapshot"><img alt="최종 결과를 드러내지 않는 무채색 대한민국 지도" src="/static/map_outline_snapshot.png"><p class="vis-muted">개표 진행 중 · 최종 정당별 당선 정보는 공개하지 않습니다.</p></div>'
        buttons=' '.join('<a class="vmap-back" href="/safe2024?page=district&region='+esc(full)+'">'+esc(short)+'</a>' for full,short in SHORT.items())
        return '<div class="map-notready map-snapshot"><img alt="기존 V5의 254개 지역구 확정 결과 캡처 (대체 이미지)" src="/static/map_final_snapshot.png"><p class="vis-muted">기존 V5 결과 지도 캡처로 임시 표시하고 있습니다. 확대 가능한 실제 선거구 지도를 보려면 최초 실행 시 GitHub 지도 경계 자료 다운로드가 필요합니다.</p><div class="vmap-choices">'+buttons+'</div><p class="vis-muted">지도 자료 진단: '+esc(type(err).__name__)+'</p></div>'
    districts=d['constituency']['districts'];byid={x['id']:x for x in districts}
    ids={f['properties']['id'] for f in features}
    if len(districts)!=254 or ids!=set(byid):
        raise ValueError('지도 선거구 254건과 실제 선거 결과가 일치하지 않음')
    regions=sorted({f['properties']['region'] for f in features})
    if region not in regions:region=''
    svg=_svg_shapes(features,byid,region,mode,turnout)
    chooser=''.join(f'<a href="/safe2024/map?region={esc(r)}">{esc(r)}</a>' for r in regions)
    rows=sorted((x for x in districts if SHORT.get(x['region'],x['region'])==region),key=lambda x:x['district']) if region else []
    selected=byid.get(district) if district else None
    if selected and SHORT.get(selected['region'],selected['region'])!=region:selected=None
    districtchooser=''.join(f'<a class="{"active" if selected and selected["id"]==x["id"] else ""}" href="/safe2024/map?{urlencode({"region":region,"district":x["id"]})}">{esc(x["district"])}</a>' for x in rows)
    results=''
    if selected:
        results=f'<section class="map-detail"><h3>{esc(selected["region"])} {esc(selected["district"])}</h3><p><b>{esc(selected["winner"]["name"])} ({esc(selected["winner"]["party"])})</b> 당선</p>'+_winner_margin_chart(selected)+'</section>'
    elif mode=='results':
        results='<p class="vis-muted">시·도 지도에서 지역구를 클릭하면 후보별 득표수와 득표차를 볼 수 있습니다.</p>'
    controls=f'<a href="/safe2024/map" class="vmap-back">← 전국 지도로</a>' if region else ''
    title=(f'{region} 지역구 확정 개표' if region else '전국 254개 지역구 최종 당선 지도')
    return f'<div class="vmap-layout">'+f'<div class="vmap-body">{controls}<h3>{esc(title)}</h3>{svg}</div>'+f'<aside class="vmap-aside">'+('<h4>지역구 선택</h4><div class="vmap-choices">'+districtchooser+'</div>' if region else '<h4>시·도 선택</h4><div class="vmap-choices">'+chooser+'</div>')+results+'</aside></div>'

def map_iframe(height=720,compact=False):
    src='/safe2024/map'+('?compact=1' if compact else '')
    return f'<iframe title="2024년 22대 총선 실제 선거구 결과 지도" src="{src}" loading="lazy" style="width:100%;height:{int(height)}px;border:1px solid #294560;border-radius:12px;background:#0d1c2e"></iframe>'

def turnout_region_table(t):
    actual=t['region_actual']
    ranked=sorted(actual.items(),key=lambda x:-x[1])
    return '<div class="turnout-rank">'+''.join(f'<button type="button" class="turnout-rank-row" data-reg="{esc(name)}" onclick="highlightTurnoutRegion(this)"><span>{esc(name)}</span><div class="rank-track"><div style="width:{100*(value/72):.1f}%"></div></div><b>{value:.1f}%</b></button>' for name,value in ranked)+'</div>'

def turnout_regions_html(t, selected_region=""):
    rates={k:v for k,v in t['region_actual'].items()}
    try:
        features=load_geography()
        map_svg=_svg_shapes(features,{},mode='turnout',regional_rates=rates)
    except Exception:
        map_svg='<div class="turnout-tiles" aria-label="지역별 투표율 색상 타일 지도 · 지도 경계 다운로드 실패 시 대체 화면">'+''.join('<a title="'+esc(region)+' '+f'{value:.1f}%'+'" style="background:'+_turnout_color(value)+'" href="/safe2024?page=turnout&region='+esc(region)+'">'+esc(region)+'<b>'+f'{value:.1f}%</b></a>' for region,value in sorted(rates.items()))+'</div><p class="vis-muted">선거구 지리경계를 불러오지 못해 시·도별 색상 타일로 대신 표시합니다. 타일은 실제 행정구역 형태가 아닙니다.</p>'
    legend='<div class="turnout-color-legend" role="img" aria-label="투표율이 낮으면 연한 파란색, 높으면 진한 파란색"><span>투표율 낮음</span>'+''.join('<i style="background:'+color+'" title="'+label+'"></i>' for color,label in zip(('#a5dce9','#76c2e0','#4a9dcb','#256b9f','#123c76'),('<64%','64~66%','66~68%','68~70%','70% 이상')))+'<span>높음</span></div>'
    return '<div class="turnout-map-grid" data-selected-region="'+esc(selected_region)+'"><div class="vmap-body"><h3>17개 시·도 실제 최종 투표율 지도</h3>'+map_svg+legend+'</div><div><h3>지역별 투표율 비교</h3>'+turnout_region_table(t)+'</div></div><p class="vis-muted">진한 파란색일수록 실제 투표율이 높은 시·도입니다. 지도 또는 목록을 선택하면 해당 지역이 강조됩니다. 수치는 중앙선관위 실제 최종 집계이며 표본조사 투표율과 다릅니다.</p><script>function highlightTurnoutRegion(btn){const reg=btn.dataset.reg;document.querySelectorAll(".turnout-rank-row").forEach(x=>x.classList.toggle("dimmed",x.dataset.reg!==reg));document.querySelectorAll(".vmap-svg [data-region]").forEach(x=>x.classList.toggle("dimmed",x.dataset.region!==reg));}(()=>{const reg=document.querySelector(".turnout-map-grid").dataset.selectedRegion;const b=[...document.querySelectorAll(".turnout-rank-row")].find(x=>x.dataset.reg===reg);if(b)highlightTurnoutRegion(b)})();</script>'

STYLE="""
.seats-section{margin:16px 0;color:#e9f2ff}.seats-section h3{font-size:20px;margin:8px 0}
.vis-muted{font-size:12px;color:#9bb7ca;line-height:1.65}.donut-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.vis-card{background:#142b45;border:1px solid #305271;border-radius:12px;padding:15px;min-width:0}
.vis-card h4{font-size:16px;margin:0 0 8px}.donut-grid .vis-card svg{height:200px;display:block;max-width:100%}
.seat-legend{display:flex;justify-content:center;gap:8px;flex-wrap:wrap;margin-top:9px;font-size:11px}
.seat-legend span{white-space:nowrap;display:inline-flex;align-items:center;gap:5px;background:#203853;padding:5px 7px;border-radius:4px}
.seat-legend i{height:9px;width:9px;border-radius:2px;display:inline-block}.seat-legend b{color:#fff}
.seat-big{font-size:24px;fill:#fff;font-weight:900}.seat-small{font-size:12px;fill:#bad3e8}.hemi{margin-top:12px}
.semi-svg{width:100%;height:auto;max-height:305px;display:block;margin:auto}
.vmap-layout{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(240px,1fr);gap:14px}
.vmap-body{background:#10263b;border:1px solid #2d4e67;border-radius:12px;padding:12px;min-width:0}
.vmap-body h3{font-size:16px}.vmap-aside{background:#142b43;border:1px solid #2d4e67;border-radius:12px;padding:14px;min-width:0}
.vmap-svg{width:100%;height:auto;max-height:720px;display:block}.vmap-svg path{transition:opacity .17s,fill-opacity .17s;cursor:pointer}
.vmap-svg path:hover{stroke:#fff;stroke-width:2.5}.vmap-svg path.dimmed{opacity:.11}.vmap-label{fill:#fff;font-size:11px;font-weight:800;stroke:#101b2e;stroke-width:3px;paint-order:stroke;text-anchor:middle;pointer-events:none}
.vmap-choices{display:flex;flex-wrap:wrap;gap:6px;max-height:195px;overflow-y:auto}
.vmap-choices a,.vmap-back{display:inline-block;font-size:12px;border:1px solid #3a6383;color:#b3eaff;text-decoration:none;padding:7px;border-radius:5px}
.vmap-choices a:hover,.vmap-choices a.active{background:#235979}.map-detail{margin-top:14px;border-top:1px solid #305271}
.map-notready{border:1px dashed #49657e;padding:20px;background:#12283c;border-radius:9px;line-height:1.7}
.margin-visual{padding:15px;background:#172d45;border-radius:10px}.margin-who{display:flex;justify-content:space-between;gap:15px;font-size:12px}
.margin-track{height:13px;background:#29415b;border-radius:12px;overflow:hidden;margin:7px 0 13px}.margin-track>div{height:100%;border-radius:12px}
.turnout-map-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(280px,1fr);gap:15px}
.turnout-rank{height:570px;overflow:auto;display:flex;flex-direction:column;gap:4px}
.turnout-rank-row{display:grid;grid-template-columns:34px minmax(0,1fr) 48px;gap:8px;width:100%;align-items:center;background:#18314a;border:1px solid #2c4f6a;border-radius:5px;color:#e2f6ff;padding:8px;text-align:left;font-size:12px;cursor:pointer}
.rank-track{background:#38506b;border-radius:8px;height:10px;overflow:hidden}.rank-track>div{height:100%;background:#45bed2}.turnout-rank-row.dimmed{opacity:.22}
.turnout-color-legend{display:flex;align-items:center;justify-content:center;gap:3px;flex-wrap:wrap;margin:10px 4px;color:#c4d8e8;font-size:11px}
.turnout-color-legend span{padding:0 8px}.turnout-color-legend i{width:27px;height:14px;border:1px solid #c7e1ed36}
.turnout-tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;padding:20px 4px}
.turnout-tiles a{color:#fff;min-height:86px;display:flex;flex-direction:column;justify-content:center;gap:7px;align-items:center;text-decoration:none;border-radius:8px;border:1px solid #789bb0;font-weight:800;text-shadow:0 1px 4px #142336}
.turnout-tiles a b{font-size:14px}.turnout-tiles a:hover{outline:3px solid #ffedac;outline-offset:1px}
@media(max-width:600px){.turnout-tiles{grid-template-columns:repeat(3,minmax(0,1fr))}}

@media(max-width:820px){.vmap-layout,.turnout-map-grid,.donut-grid{grid-template-columns:1fr}.turnout-rank{height:280px}}
"""

def turnout_crossfilter_html():
    data=json.loads((ROOT/'newsroom'/'static'/'turnout_region_sex_2024.json').read_text('utf-8'))
    payload=json.dumps(data,ensure_ascii=False).replace('</','<\\/')
    return '''<section id="v5-crossfilter" class="cross-v5" aria-label="지역·성별 투표율 교차 분석">
    <div class="cross-v5-controls"><strong>지역·성별 선택으로 비교</strong><button type="button" data-sex="남성">남성</button><button type="button" data-sex="여성">여성</button><button type="button" data-reset="1">전체 보기</button></div>
    <p class="vis-muted" id="v5-cross-selection">전국 17개 시·도 · 남녀 모두</p>
    <div class="cross-v5-bars" id="v5-cross-bars"></div>
    <p class="vis-muted">중앙선관위 2024년 투표율 분석 인쇄 29쪽 그림15 · 전체 선거인 표본조사입니다. 시도별 실제 확정 투표율 지도와 조사방법이 다릅니다.</p>
    </section>
    <script type="application/json" id="v5-cross-data">'''+payload+'''</script>
    <script>(()=>{'use strict';const root=document.getElementById('v5-crossfilter');if(!root)return;
      const data=JSON.parse(document.getElementById('v5-cross-data').textContent);
      const regionNode=root.querySelector('#v5-cross-bars'),label=root.querySelector('#v5-cross-selection');
      let selectedRegion='',selectedSex='';const sexColors={'남성':'#2da0d1','여성':'#f3a65b'};
      const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
      function render(){label.textContent='지역: '+(selectedRegion||'전체 17개 시·도')+' · 성별: '+(selectedSex||'남녀 모두');
        root.querySelectorAll('[data-sex]').forEach(btn=>btn.classList.toggle('selected',btn.dataset.sex===selectedSex));
        regionNode.innerHTML=data.regions.map((rec,i)=>{const dim=selectedRegion&&selectedRegion!==rec.region;
          const gender=['남성','여성'].map(sex=>{const opacity=selectedSex&&selectedSex!==sex?'opacity:.16;':'';
            return `<span class="cross-sex-line" style="${opacity}"><i style="background:${sexColors[sex]};width:${rec[sex]/75*100}%"></i><b>${sex} ${rec[sex].toFixed(1)}%</b></span>`}).join('');
          return `<button type="button" class="cross-region-btn ${dim?'dimmed':''}" data-region="${escapeHtml(rec.region)}" aria-label="${escapeHtml(rec.region)} 남녀 투표율 보기"><strong>${escapeHtml(rec.region)}</strong><span class="cross-sex-stack">${gender}</span></button>`;
        }).join('')}
      root.addEventListener('click',e=>{const t=e.target.closest('button');if(!t)return;
         if(t.dataset.sex){selectedSex=selectedSex===t.dataset.sex?'':t.dataset.sex;render()}
         else if(t.dataset.region){selectedRegion=selectedRegion===t.dataset.region?'':t.dataset.region;render()}
         else if(t.dataset.reset){selectedSex='';selectedRegion='';render()}});
      render();
    })()</script>'''

STYLE += """
.map-snapshot{text-align:center;background:#0e2035!important}.map-snapshot img{display:block;max-height:550px;max-width:100%;width:auto;height:auto;object-fit:contain;margin:auto}
.cross-v5{background:#132b42;border:1px solid #2e536d;padding:16px;border-radius:10px}
.cross-v5-controls{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.cross-v5-controls strong{margin-right:auto}.cross-v5-controls button{border:1px solid #3e7795;background:#1b4561;color:#e0f9ff;border-radius:6px;padding:8px 12px;cursor:pointer}
.cross-v5-controls button.selected{background:#237c9d;outline:2px solid #8ce6f5}
.cross-v5-bars{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px}
.cross-region-btn{display:grid;grid-template-columns:40px 1fr;align-items:center;gap:8px;padding:7px;background:#18364d;border:1px solid #30516a;color:#e7f4ff;text-align:left;border-radius:6px;cursor:pointer}
.cross-region-btn strong{font-size:12px}.cross-region-btn.dimmed{opacity:.2}.cross-region-btn:hover{border-color:#62d6e7}
.cross-sex-stack{display:flex;flex-direction:column;gap:5px}.cross-sex-line{display:flex;align-items:center;gap:5px;font-size:10px;color:#c0dbeb}
.cross-sex-line i{height:7px;border-radius:8px;min-width:5px;max-width:48%}.cross-sex-line b{font-size:10px;white-space:nowrap}
@media(max-width:720px){.cross-v5-bars{grid-template-columns:1fr}}
"""


# The final-result menu intentionally does not navigate: only the district
# explorer has geographic drilldown. This prevents duplicated menu behavior.
def final_static_map(d):
    try:
        features=load_geography()
        actual={x['id']:x for x in d['constituency']['districts']}
        if {f['properties']['id'] for f in features}!=set(actual):
            raise ValueError('254개 선거구 지리정보 및 선관위 결과 불일치')
        svg=_svg_shapes(features,actual,mode='results',navigate='static')
        return '<div class="vmap-body final-map-static"><h3>전국 254개 지역구 당선 정당 지도</h3>'+svg+'<p class="vis-muted">지역구별 최종 당선 정당 색상 · 이 화면은 전국 결과 요약 전용이며 상세 탐색은 「지역·선거구 탐색」 메뉴에서 할 수 있습니다.</p></div>'
    except Exception as exc:
        return '<div class="vmap-body final-map-static"><h3>전국 지역구 당선 지도</h3><img style="display:block;max-width:100%;margin:auto" src="/static/map_final_snapshot.png" alt="V5 실제 결과 지도 검증용 캡처"><p class="vis-muted">실제 지역구 지도 경계 파일을 아직 연결하지 못해 기존 화면 캡처를 보여줍니다. 원본 지도 연결 시 색상 지도로 전환됩니다. ('+esc(type(exc).__name__)+')</p></div>'

STYLE += """
.final-summary-grid{display:grid;grid-template-columns:minmax(320px,.95fr) minmax(400px,1.3fr);gap:14px;align-items:start}
.final-map-static{position:sticky;top:12px}
.final-map-static .vmap-svg{max-height:880px}
.final-map-static path{cursor:default;pointer-events:none}
.final-summary-grid .seats-section{margin:0}
.final-summary-grid .hemi{margin-top:10px}
.final-summary-grid .semi-svg{max-height:250px}
.final-combined{margin-top:16px}
.explore-breadcrumb{display:flex;align-items:center;gap:10px;flex-wrap:wrap;color:#bbd9ee;margin:5px 0 12px;font-size:13px}
.explore-breadcrumb a{color:#5de3f0;text-decoration:none}
.explore-nav-actions{display:flex;align-items:center;justify-content:flex-end;gap:10px;flex-wrap:wrap;margin:3px 0 15px}
.explore-nav-actions a{display:inline-flex;align-items:center;justify-content:center;min-height:41px;padding:9px 15px;border-radius:8px;background:#1c4562;border:1px solid #5486a5;color:#f1faff;font-size:13px;font-weight:750;text-decoration:none;white-space:nowrap}
.explore-nav-actions .explore-nav-national{background:#146074;border-color:#4cc9d3}
.explore-nav-actions a:hover,.explore-nav-actions a:focus-visible{background:#21859c;outline:2px solid #8de4f0;outline-offset:1px}
@media(max-width:730px){.explore-nav-actions{justify-content:flex-start}.explore-nav-actions a{flex:1;white-space:normal;text-align:center}}
.explore-grid{display:grid;grid-template-columns:minmax(0,1.18fr) minmax(0,1.03fr) minmax(0,.88fr);gap:12px;align-items:stretch}
.explore-bottom-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:start;margin-top:13px}
.explore-national-map{width:100%;min-width:0;display:flex;align-items:center;justify-content:center;min-height:520px;background:#0e2035;border:1px solid #385c77;border-radius:10px;padding:8px}
.explore-national-map .vmap-svg{width:100%;max-height:none;height:auto;display:block}
.explore-national-map .map-notready{width:100%}
.explore-center .vmap-svg{max-height:none;height:auto}
.explore-center{min-height:520px}
.explore-map-placeholder{min-height:420px;display:grid;place-items:center;text-align:center;color:#b0cddd;background:#0d2236;border:1px dashed #3a566d;border-radius:9px;padding:24px}
.explore-list .explore-city-list{display:flex;flex-wrap:wrap;max-height:180px;gap:7px;overflow-y:auto}
.explore-list .explore-district-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));max-height:270px;overflow:auto;gap:7px}
.explore-province-chooser .explore-provinces{display:flex;flex-wrap:wrap;gap:7px}
.explore-province-chooser .explore-provinces a{min-width:70px}
.explore-grid .explore-result{height:100%}
body:has(.explore-grid) main{max-width:none;width:100%;padding:18px 15px}
.explore-map{background:#122840;border:1px solid #35566e;border-radius:12px;padding:12px;min-width:0}
.explore-map svg{max-height:650px;width:100%;display:block}
.explore-map h3{font-size:15px;line-height:1.3}
.explore-map .vmap-svg a{cursor:pointer}
.explore-map .vmap-svg .vmap-selected{stroke:#f8e774;stroke-width:4;filter:drop-shadow(0 0 3px #e9e689)}
.explore-side{background:#152c44;border:1px solid #35566e;border-radius:12px;padding:14px;min-width:0}
.explore-side h3{font-size:16px}
.explore-city-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;max-height:340px;overflow:auto;padding:4px}
.explore-city-list a,.explore-district-list a{display:flex;align-items:center;justify-content:space-between;gap:5px;border:1px solid #395a75;color:#d5f3ff;text-decoration:none;background:#1a3854;border-radius:6px;padding:8px 10px;font-size:12px}
.explore-city-list a:hover,.explore-district-list a:hover,.explore-city-list a.selected,.explore-district-list a.selected{border-color:#64dbe9;background:#135775;color:white}
.explore-district-list{display:flex;flex-direction:column;gap:6px;max-height:430px;overflow:auto;margin-top:12px}
.explore-district-list a{padding:10px}
.explore-district-list small{color:#b3d3e8}
.explore-summary-stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin:10px 0}
.explore-stat{background:#1a3854;border:1px solid #385b76;border-radius:7px;padding:12px}
.explore-stat small{display:block;color:#bed3e7;font-size:11px}
.explore-stat strong{font-size:21px;display:block;margin-top:8px;color:#effbff}
.explore-result{background:#162c45;border:1px solid #355771;border-radius:12px;padding:14px;min-width:0}
.explore-result .winner-flag{display:inline-block;background:#1c6f86;padding:5px 10px;border-radius:40px;color:#ecffff;font-size:12px}
.explore-result .winner-name{font-size:24px;font-weight:900;margin:8px 0}
.explore-result .winner-votes{font-size:28px;font-weight:900}
.explore-vote-row{margin:12px 0}
.explore-vote-name{display:flex;justify-content:space-between;font-size:12px;gap:8px}
.explore-vote-name b{white-space:nowrap}
.explore-vote-track{width:100%;height:16px;border-radius:10px;background:#324a64;overflow:hidden;margin-top:6px}
.explore-vote-track i{display:block;height:100%;border-radius:10px}
.explore-turnout{border:1px solid #296a76;background:#123c4d;border-radius:10px;padding:13px;margin:12px 0}
.explore-turnout strong{font-size:28px;color:#64e9da}
.explore-turnout .track{margin:8px 0;height:13px}
.explore-turnout .fill{background:#25c8b2}
.explore-search{display:flex;gap:6px;margin-bottom:8px}
.explore-search input{min-width:0;flex:1}
.explore-search button{background:#176b88;border:1px solid #60c0d8;color:white;border-radius:6px;padding:6px 10px}
.explore-label{font-size:11px;line-height:1.6;color:#b5d2e6}
@media(max-width:1120px){.explore-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.explore-grid .explore-result{grid-column:1/-1}.explore-national-map,.explore-center{min-height:390px}.final-summary-grid{grid-template-columns:1fr}}
@media(max-width:750px){.explore-grid,.explore-bottom-grid{grid-template-columns:1fr}.explore-grid .explore-result{grid-column:auto}.explore-national-map,.explore-center{min-height:0}.explore-list .explore-district-list{grid-template-columns:1fr}}

"""
