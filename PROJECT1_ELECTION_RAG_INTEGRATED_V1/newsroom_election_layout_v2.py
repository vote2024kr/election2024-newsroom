"""제22대 총선 V5: 전국 확정 개표 요약과 단계별 지역구 탐색 화면.

2024년 선관위 확정 결과는 호출자가 전달하는 PostgreSQL 검증 데이터만 사용한다.
지리 경계는 기존 254개 GeoJSON을 사용한다. 모의 데이터·중간 득표수를 섞지 않는다.
"""
from __future__ import annotations

import html
import math
import re
from collections import Counter, defaultdict
from urllib.parse import urlencode

from newsroom_election_map import PARTY_COLORS, SHORT, shapes, xy_points


def esc(value):
    return html.escape(str(value), quote=True)


def href(**params):
    args = {'page': 'district'}
    args.update({key: value for key, value in params.items() if value})
    return '/safe2024?' + urlencode(args)


def cities_for(district_name):
    """공식 선거구 명칭에서 탐색용 시·군·구 명칭을 구한다.

    법정 행정경계로 사용하지 않는다. 복합 선거구는 여러 시·군에서 탐색된다.
    """
    words = re.findall(r'[가-힣]+?(?:시|군|구)', district_name)
    if any(x.endswith(('시', '군')) for x in words):
        words = [x for x in words if x.endswith(('시', '군'))]
    return list(dict.fromkeys(words)) or [district_name]


def geometry_svg(data, region='', chosen='', city='', readonly=False):
    districts = data['constituency']['districts']
    lookup = {d['id']: d for d in districts}
    fs = shapes()
    if len(lookup) != 254 or {f['properties']['id'] for f in fs} != set(lookup):
        raise ValueError('254개 선거구 원자료와 실제 지도 경계 ID 불일치')
    region_short = SHORT.get(region, region)
    fs = [f for f in fs if f['properties']['region'] == region_short] if region else fs
    if not fs:
        raise ValueError('시·도 지도 경계를 찾을 수 없습니다.')
    pts = [(lon * .8, lat) for f in fs for ring in xy_points(f['geometry']) for lon,lat in ring]
    minx,maxx = min(x for x,y in pts), max(x for x,y in pts)
    miny,maxy = min(y for x,y in pts), max(y for x,y in pts)
    width,height,pad = 860,720,28
    scale = min((width-2*pad)/max(.00001,maxx-minx),(height-2*pad)/max(.00001,maxy-miny))
    dx = (width-(maxx-minx)*scale)/2
    dy = (height-(maxy-miny)*scale)/2
    def point(lon, lat):
        return dx+(lon*.8-minx)*scale, height-dy-(lat-miny)*scale
    def path_for(geom):
        return ''.join('M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in
            (point(*xy) for xy in ring))+' Z' for ring in xy_points(geom) if len(ring)>=3)

    items=[]
    for f in fs:
        rec=lookup[f['properties']['id']]
        selected=rec['id']==chosen
        dim=bool(city and city not in cities_for(rec['district']))
        color=PARTY_COLORS.get(rec['winner']['party'], '#8291a6')
        title=f"{rec['region']} {rec['district']} · {rec['winner']['party']} {rec['winner']['name']} 당선"
        d=f'<path d="{path_for(f["geometry"])}" class="explore-shape{" picked" if selected else ""}" fill="{color}" fill-opacity="{.16 if dim else 1}" stroke="{("#fff0a8" if selected else "#0d2335")}" stroke-width="{3.4 if selected else (1.2 if region else .65)}"><title>{esc(title)}</title></path>'
        if readonly:
            items.append(d)
        else:
            link=href(region=region, district=rec['id'], area=(city if city in cities_for(rec['district']) else '')) if region else href(region=rec['region'])
            items.append(f'<a href="{esc(link)}" aria-label="{esc(title)}">{d}</a>')
    if not region:
        groups=defaultdict(list)
        for f in fs: groups[f['properties']['region']].append(f)
        for province, group in groups.items():
            rings=[ring for f in group for ring in xy_points(f['geometry']) if len(ring)>=4]
            main=max(rings,key=lambda r:(max(p[0] for p in r)-min(p[0] for p in r))*
                                           (max(p[1] for p in r)-min(p[1] for p in r)))
            centerlon=(min(p[0] for p in main)+max(p[0] for p in main))/2
            centerlat=(min(p[1] for p in main)+max(p[1] for p in main))/2
            x,y=point(centerlon,centerlat)
            label=f'<text x="{x:.1f}" y="{y:.1f}" class="explore-map-label">{esc(province)}</text>'
            if not readonly:
                full=next((k for k,v in SHORT.items() if v==province),province)
                label=f'<a href="{esc(href(region=full))}" aria-label="{esc(province)} 지도 보기">{label}</a>'
            items.append(label)
    role='전국 확정 당선 지도' if readonly else ('선택 시·도 지역구 지도' if region else '시·도 선택 전국 지도')
    return f'<svg viewBox="0 0 {width} {height}" class="explore-svg" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{role}">' + ''.join(items) + '</svg>'


def donut_svg(seats,total):
    if sum(seats.values())!=total:
        raise ValueError('정당별 의석 합계 불일치')
    dist=2*math.pi*62
    seen=0.0
    rings=[]
    for party,value in sorted(seats.items(),key=lambda a:-a[1]):
        if not value: continue
        length=dist*value/total
        rings.append(f'<circle cx="95" cy="95" r="62" fill="none" stroke="{PARTY_COLORS.get(party, "#9ba7b8")}" stroke-width="25" stroke-dasharray="{length:.3f} {dist-length:.3f}" stroke-dashoffset="{-seen:.3f}" transform="rotate(-90 95 95)"><title>{esc(party)} {value}석</title></circle>')
        seen+=length
    return '<svg viewBox="0 0 190 190" role="img" aria-label="'+str(total)+'석 도넛 그래프">'+''.join(rings)+f'<text x="95" y="94" text-anchor="middle" font-size="31" fill="white" font-weight="900">{total}</text><text x="95" y="119" text-anchor="middle" font-size="13" fill="#bad2e4">의석</text></svg>'


def semicircle_svg(seats):
    if sum(seats.values())!=300:
        raise ValueError('전체 국회의원 의석 합계가 300석이 아닙니다.')
    colors=[PARTY_COLORS.get(p,'#9ba7b8') for p,n in sorted(seats.items(),key=lambda a:-a[1]) for _ in range(n)]
    dots=[]
    for ring,count in enumerate((49,47,45,43,41,39,36)):
        r=250-ring*18
        for j in range(count):
            theta=math.pi-(j+.5)/count*math.pi
            x=310+math.cos(theta)*r; y=290-math.sin(theta)*r
            dots.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.2" fill="{colors[len(dots)]}"/>')
    return '<svg viewBox="0 0 620 310" role="img" aria-label="국회 300석 반원형 의석 그래프">'+''.join(dots)+'<text x="310" y="265" text-anchor="middle" fill="white" font-size="28" font-weight="900">300석</text></svg>'


def party_legend(seats):
    return '<div class="explore-party-legend">'+''.join(
        f'<span><i style="background:{PARTY_COLORS.get(p,"#9ba7b8")}"></i>{esc(p)} <b>{count}석</b></span>'
        for p,count in sorted(seats.items(),key=lambda a:-a[1]) if count>0)+'</div>'


def nationwide_overview(data, turnout):
    local=data['constituency']['seats_by_party']
    proportional=data['proportional']['seat_allocation']
    merged=dict(Counter(local)+Counter(proportional))
    if sum(local.values())!=254 or sum(proportional.values())!=46:
        raise ValueError('2024년 지역구 254석·비례 46석 결과 불일치')
    chart='<div class="explore-overview-grid"><div class="explore-card">'
    chart+='<h3>전국 254개 지역구 최종 당선 지도</h3>'+geometry_svg(data,readonly=True)
    chart+='<p class="explore-help">전국 결과 요약 전용입니다. 상세 지역 선택은 지역·선거구 탐색 메뉴를 이용하세요.</p></div>'
    chart+='<div><div class="explore-donut-grid"><div class="explore-card"><h3>지역구 · 254석</h3>'
    chart+=donut_svg(local,254)+party_legend(local)+'</div><div class="explore-card"><h3>비례대표 · 46석</h3>'
    chart+=donut_svg(proportional,46)+party_legend(proportional)+'</div></div>'
    chart+='<div class="explore-card"><h3>전체 국회 · 300석</h3>'+semicircle_svg(merged)+party_legend(merged)+'</div></div></div>'
    rows=''.join(f'<tr><td>{esc(p)}</td><td>{local.get(p,0)}석</td><td>{proportional.get(p,0)}석</td><td><strong>{merged.get(p,0)}석</strong></td></tr>' for p in sorted(merged,key=lambda p:-merged[p]))
    return f'<div class="explore-head"><strong>2024년 최종 선거 결과 · 300석</strong><span>전국 실제 최종 투표율 {float(turnout["national"]["final"]):.1f}% · 10:25는 보도기준 재현 시각</span></div>'+chart+'<section class="explore-card explore-table"><h3>정당별 의석 현황 · 원래 정당명 기준</h3><table><thead><tr><th>정당</th><th>지역구</th><th>비례대표</th><th>합계</th></tr></thead><tbody>'+rows+'<tr><th>전체</th><th>254석</th><th>46석</th><th>300석</th></tr></tbody></table><p class="explore-help">지역구 당선 정당과 비례 명부 정당은 이름을 임의로 합치지 않았습니다.</p></section><a class="btn" href="/safe2024?page=district">지역·선거구 탐색 열기</a>'+STYLE


def district_explorer(data, turnout, region='', district='', area='', query=''):
    districts=data['constituency']['districts']
    available={r['name']:r for r in data['constituency']['regions']}
    if region not in available: region=''
    selected_region=[d for d in districts if d['region']==region] if region else []
    city_groups=defaultdict(list)
    for d in selected_region:
        for city in cities_for(d['district']): city_groups[city].append(d)
    if area not in city_groups: area=''
    selected=next((d for d in selected_region if d['id']==district),None)
    if selected and area and area not in cities_for(selected['district']):selected=None
    searched=[d for d in (city_groups[area] if area else selected_region)
              if not query or query.casefold() in d['district'].casefold() or query.casefold() in d['winner']['name'].casefold()]
    previous=href(region=region,area=area) if selected else (href(region=region) if area else href())
    breadcrumb=['<a href="'+href()+'">전국</a>']
    if region: breadcrumb.append('<a href="'+esc(href(region=region))+'">'+esc(region)+'</a>')
    if area: breadcrumb.append('<a href="'+esc(href(region=region,area=area))+'">'+esc(area)+'</a>')
    if selected: breadcrumb.append('<b>'+esc(selected['district'])+'</b>')
    nav='<div class="explore-toolbar"><div class="explore-breadcrumb">'+' <span>›</span> '.join(breadcrumb)+'</div><div class="explore-actions">'
    nav+='<a class="explore-button" href="'+esc(previous)+'">← 이전 단계로</a>'
    nav+='<a class="explore-button explore-button-main" href="'+href()+'">⌂ 전국 지도 보기</a></div></div>'

    region_buttons=''.join('<a class="'+('active' if region==name else '')+'" href="'+esc(href(region=name))+'">'+esc(SHORT.get(name,name))+'</a>' for name in available)
    top='<div class="explore-top"><section class="explore-card explore-nation"><h3>전국 17개 시·도 선택 · 지도 확대</h3><p class="explore-help">전국 지도에서 시·도를 선택하면 가운데 지도가 변경됩니다.</p>'
    top+=geometry_svg(data)
    top+='</section><section class="explore-card explore-local"><h3>'+esc(region)+' 지역구 지도 · '+str(len(selected_region))+'개 선거구' if region else '<h3>시·도를 선택하면 지역 지도가 나타납니다'
    top+='</h3><p class="explore-help">'+('지도에서 지역구를 선택하면 상세 결과가 표시됩니다.' if region else '왼쪽 전국 지도 또는 아래 시·도 버튼을 선택하세요.')+'</p>'
    if region: top+=geometry_svg(data,region=region,chosen=(selected or {}).get('id',''),city=area)
    else: top+='<div class="explore-map-placeholder">시·도를 선택해 주세요</div>'
    top+='</section><section class="explore-card explore-result"><h3>선택 선거구 최종 결과</h3>'
    if selected:
        win=selected['winner']
        top+='<p class="explore-winner-flag">✓ 최종 당선 · 개표율 100%</p><h3>'+esc(selected['region']+' '+selected['district'])+'</h3>'
        top+='<div class="explore-winner" style="color:'+PARTY_COLORS.get(win['party'],'#cbd8e6')+'">'+esc(win['name'])+' <small>'+esc(win['party'])+'</small></div>'
        top+='<p>당선인 득표율 <strong>'+f'{win["share"]:.2f}%</strong></p>'
        registered, ballots=selected['registered'],selected['ballots']
        if registered and 0<=ballots<=registered:
            rate=ballots/registered*100
            top+='<div class="explore-turnout"><small>해당 지역구 투표율 · 선관위 지역구 원자료 계산</small><strong>'+f'{rate:.2f}%</strong><div class="explore-track"><i style="width:'+f'{rate:.2f}%'+ ';background:#23c9b6"></i></div><small>투표수 '+f'{ballots:,}'+'표 ÷ 선거인수 '+f'{registered:,}'+'명 × 100</small></div>'
        top+='<h3>후보별 최종 득표 비교</h3>'
        for candidate in sorted(selected['candidates'],key=lambda c:-c['votes']):
            color=PARTY_COLORS.get(candidate['party'],'#9ba7b8')
            top+='<div class="explore-vote"><span>'+esc(candidate['name'])+' · '+esc(candidate['party'])+'</span><b>'+f'{candidate["votes"]:,}'+'표 ('+f'{candidate["share"]:.2f}%)</b><div class="explore-track"><i style="background:'+color+';width:'+f'{candidate["share"]:.2f}%'+'"></i></div></div>'
        top+='<p class="explore-gap"><b>1·2위 득표차 '+f'{selected["margin"]:,}'+'표</b><br>유효투표 '+f'{selected["valid"]:,}'+'표 · 무효투표 '+f'{selected["invalid"]:,}'+'표</p>'
        top+='<p class="explore-help">출처: 선관위 22대 총선 지역구 개표 원자료 · 지역구 시트 '+str(selected['excel_row'])+'행 · '+esc(selected['id'])+'</p>'
    elif region:
        tally=Counter(d['winner']['party'] for d in selected_region)
        top+='<p class="explore-help">아래 시·군 또는 지역구를 선택하세요.</p>'
        rate=turnout['region_actual'].get(SHORT.get(region,''))
        if rate is not None: top+='<div class="explore-turnout"><small>선관위 시·도 전체 최종 투표율</small><strong>'+f'{rate:.1f}%</strong></div>'
        top+=party_legend(tally)
    else: top+='<p class="explore-help">전국 지도에서 시·도를 먼저 선택하세요.</p>'
    top+='</section></div>'

    bottom='<div class="explore-bottom"><section class="explore-card"><h3>시·도 선택</h3><div class="explore-provinces">'+region_buttons+'</div>'
    if region:
        rate=turnout['region_actual'].get(SHORT.get(region,''))
        bottom+='<div class="explore-regional-stats"><div>'+esc(SHORT.get(region,region))+' 지역구 <strong>'+str(len(selected_region))+'석</strong></div>'
        if rate is not None: bottom+='<div>선관위 시·도 최종 투표율 <strong>'+f'{rate:.1f}%</strong></div>'
        bottom+='</div>'
    bottom+='</section><section class="explore-card"><h3>시·군 / 지역구 목록 · 선택 및 검색</h3>'
    if region:
        city_links='<a href="'+esc(href(region=region))+'" class="'+('active' if not area else '')+'">전체 '+str(len(selected_region))+'</a>'
        for city,group in sorted(city_groups.items()):
            city_links+='<a class="'+('active' if city==area else '')+'" href="'+esc(href(region=region,area=city))+'">'+esc(city)+' '+str(len(group))+'개</a>'
        bottom+='<div class="explore-cities">'+city_links+'</div>'
        bottom+='<form action="/safe2024" method="get" class="explore-search"><input type="hidden" name="page" value="district"><input type="hidden" name="region" value="'+esc(region)+'"><input type="hidden" name="area" value="'+esc(area)+'"><input type="text" name="q" maxlength="60" value="'+esc(query[:60])+'" placeholder="지역구·당선인 검색"><button type="submit">검색</button></form>'
        bottom+='<div class="explore-district-links">'+''.join('<a href="'+esc(href(region=region,area=area,district=d['id']))+'" class="'+('active' if selected and selected['id']==d['id'] else '')+'">'+esc(d['district'])+' <span>'+esc(d['winner']['party'])+'</span></a>' for d in sorted(searched,key=lambda x:x['district']))+'</div>'
    else:
        bottom+='<p class="explore-help">시·도를 선택하면 소속 시·군과 254개 중 해당 지역구 목록이 표시됩니다.</p>'
    bottom+='</section></div>'
    return nav+top+bottom+'<p class="explore-help">시·군 구분은 선거구 공식 명칭을 통한 탐색용 분류입니다. 행정경계와 같다고 단정하지 않습니다. 시·도 투표율은 선관위 발표값, 지역구 투표율은 선거인수·투표수로 계산한 값입니다.</p>'+STYLE


STYLE = """<style>
body:has(.explore-top) main{max-width:1940px;padding:22px 18px}
.explore-card{background:#132a43;border:1px solid #315671;border-radius:11px;padding:14px;min-width:0}
.explore-card h3{font-size:16px;margin:0 0 9px}.explore-help{color:#acc8d9;font-size:12px;line-height:1.6}
.explore-head,.explore-toolbar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;background:#11263c;border:1px solid #315671;border-radius:10px;padding:12px 14px;margin:14px 0}
.explore-toolbar a{color:#a7eaf6;text-decoration:none}.explore-breadcrumb{font-size:13px}.explore-actions{display:flex;gap:8px}
.explore-button{padding:10px 15px;background:#214765;border:1px solid #4c83a2;border-radius:7px;font-size:13px}
.explore-button-main{background:#176477;border-color:#31b4c9}
.explore-top{display:grid;grid-template-columns:minmax(0,1.18fr) minmax(0,1fr) minmax(0,.89fr);gap:13px;align-items:stretch}
.explore-top .explore-svg{width:100%;height:auto;max-height:700px;display:block}.explore-nation{min-height:630px}
.explore-map-label{fill:white;font-size:12px;font-weight:800;text-anchor:middle;paint-order:stroke;stroke:#10213a;stroke-width:3px}
.explore-shape{cursor:pointer;transition:filter .15s,fill-opacity .15s}.explore-shape:hover{filter:brightness(1.25);stroke:#fff;stroke-width:3}
.explore-map-placeholder{height:480px;display:flex;align-items:center;justify-content:center;color:#b7cde3;background:#0d2236;border-radius:8px}
.explore-winner-flag{display:inline-block;background:#145c70;border-radius:20px;padding:8px;color:#bff7ff;font-size:12px}
.explore-winner{font-size:24px;font-weight:900;padding:10px 0}.explore-winner small{font-size:13px}
.explore-turnout{background:#113b4c;border:1px solid #257487;padding:14px;border-radius:10px;margin:12px 0}
.explore-turnout small{display:block;color:#b5dce6;line-height:1.5}.explore-turnout strong{display:block;font-size:29px;color:#4edbc8;margin:6px 0}
.explore-track{height:13px;background:#324c67;border-radius:12px;overflow:hidden;margin:7px 0 10px}.explore-track i{display:block;height:100%;border-radius:12px}
.explore-vote{font-size:12px;margin:13px 0}.explore-vote span,.explore-vote b{display:inline-block;max-width:100%}.explore-vote b{float:right}
.explore-gap{background:#102f41;border-left:3px solid #4bd0c6;padding:12px;line-height:1.8}
.explore-bottom{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin:14px 0}
.explore-provinces,.explore-cities{display:flex;flex-wrap:wrap;gap:6px}
.explore-provinces a,.explore-cities a,.explore-district-links a{background:#1b415d;border:1px solid #386987;border-radius:6px;color:#d7f4ff;text-decoration:none;font-size:12px;padding:10px}
.explore-provinces a.active,.explore-cities a.active,.explore-district-links a.active{background:#157993;border-color:#77edff}
.explore-regional-stats{display:flex;gap:9px;margin-top:15px}.explore-regional-stats div{background:#1a3a56;padding:15px;border-radius:8px}
.explore-regional-stats strong{display:block;font-size:22px;margin-top:5px}
.explore-search{display:flex;gap:8px;margin:12px 0}.explore-search input{flex:1}
.explore-district-links{display:grid;grid-template-columns:1fr 1fr;gap:6px;max-height:330px;overflow:auto}
.explore-district-links a span{float:right;color:#9bd1e8}
.explore-overview-grid{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:12px;margin:13px 0}
.explore-overview-grid .explore-svg{width:100%;max-height:820px}.explore-overview-grid .explore-svg path{cursor:default;pointer-events:none}
.explore-donut-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
.explore-donut-grid svg{display:block;max-width:200px;width:100%;margin:auto}
.explore-overview-grid svg[aria-label*="반원"]{width:100%;max-height:310px}
.explore-party-legend{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.explore-party-legend span{background:#24415a;border-radius:4px;padding:6px;font-size:11px}
.explore-party-legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px}
.explore-table{margin:12px 0}
@media(max-width:1390px){.explore-top{grid-template-columns:1fr 1fr}.explore-result{grid-column:1/-1}.explore-nation{min-height:0}}
@media(max-width:820px){.explore-top,.explore-bottom,.explore-overview-grid,.explore-donut-grid{grid-template-columns:1fr}.explore-result{grid-column:auto}.explore-actions{width:100%}.explore-district-links{grid-template-columns:1fr}}
</style>"""
