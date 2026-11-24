"""지역·선거구 전용 탐색 UI. 모든 수치는 기존 2024년 선관위 결과에서 조회한다.

시·군 이름은 공식 선거구 명칭에서 추출한 탐색용 분류일 뿐 GIS 행정경계가
아니다. 시·군 통합 선거구는 각 시·군 목록에서 동일 지역구로 연결된다.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import re
from urllib.parse import urlencode
from newsroom_visuals2024 import (
    load_geography, _svg_shapes, final_static_map, esc, COLORS, SHORT,
    _winner_margin_chart, seat_charts,
)


def url(**args):
    return '/safe2024?' + urlencode({'page':'district', **{k:v for k,v in args.items() if v}})


def municipalities(district_name: str) -> list[str]:
    """선거구명에 포함된 시·군, 또는 광역시의 구를 탐색 인덱스로 사용."""
    found=re.findall(r'[가-힣]+?(?:시|군|구)', district_name)
    # 시·군 선거구의 관할 구(성남시중원구)는 시 단위에 통합해 표시한다.
    if any(x.endswith('시') or x.endswith('군') for x in found):
        found=[x for x in found if x.endswith(('시','군'))]
    return list(dict.fromkeys(found)) or [district_name]


def _parties_table(data):
    local=data['constituency']['seats_by_party']
    prop=data['proportional']['seat_allocation']
    seats=sorted(set(local)|set(prop),key=lambda k:-(local.get(k,0)+prop.get(k,0)))
    rows=''.join('<tr><td><span class="party-sw" style="background:'+COLORS.get(p,'#8193a9')+'"></span>'+esc(p)+'</td>'
        f'<td class="number">{local.get(p,0)}석</td><td class="number">{prop.get(p,0)}석</td>'
        f'<td class="number"><strong>{local.get(p,0)+prop.get(p,0)}석</strong></td></tr>' for p in seats)
    return '''<section class="panel final-combined"><h2>정당별 최종 의석수 · 원 정당명 기준</h2>
       <p class="note">지역구 당선 정당과 비례대표 명부 정당의 법적 명칭을 그대로 구분합니다. 연계 정당을 임의로 합산하지 않았습니다.</p>
       <div class="table-wrap"><table><thead><tr><th>정당</th><th>지역구</th><th>비례대표</th><th>합계</th></tr></thead><tbody>'''+rows+'''
       <tr class="final-total"><th>전체</th><td class="number">254석</td><td class="number">46석</td><td class="number">300석</td></tr>
       </tbody></table></div></section>'''


def final_summary(data,turnout):
    """전국 확정 개표 = 클릭 탐색 없는 전국 결과 정적 요약."""
    national=turnout['national']['final']
    result=f'<div class="final-headline"><span class="final-badge">● 개표 완료 · 2024.04.11 10:25</span><strong>전국 최종 결과</strong>' \
           f'<span>국회 총 300석 · 최종 투표율 {national:.1f}%</span></div>'
    result+='<div class="final-summary-grid">'+final_static_map(data)+seat_charts(data)+'</div>'
    result+=_parties_table(data)
    result+='<p class="box-note">이 화면은 전국 최종 결과만 요약합니다. 시·도·시·군을 확대해 후보별 득표를 살펴보려면 <a href="/safe2024?page=district">지역·선거구 탐색</a> 메뉴를 선택하세요. 10:25는 당시 보도를 기반으로 채택한 재생 시각입니다.</p>'
    return result


def _fallback_photo(nationwide=False):
    if nationwide:
        return '<div class="map-notready map-snapshot"><img src="/static/map_final_snapshot.png" alt="254개 지역구 실제 지도 캡처"><p class="vis-muted">지도 원본을 연결하기 전에는 기존 개표 지도 캡처를 표시합니다. 아래 시·도 목록으로 상세 탐색은 가능합니다.</p></div>'
    return '<div class="map-notready map-snapshot"><img src="/static/map_outline_snapshot.png" alt="전국 지도 참고 그림"><p class="vis-muted">선택한 시·도의 지도 경계는 최초 실행 시 공개 지리자료를 받아 표시합니다. 아래 시·군·지역구 목록과 최종 개표 결과는 원본 데이터로 이용할 수 있습니다.</p></div>'


def district_explorer(data,turnout,region='',district='',area='',query=''):
    all_d=data['constituency']['districts']
    provs={x['name']:x for x in data['constituency']['regions']}
    if region not in provs:region=''
    region_short=SHORT.get(region,'')
    selected_ds=[d for d in all_d if d['region']==region] if region else []
    grouping=defaultdict(list)
    for rec in selected_ds:
        for city in municipalities(rec['district']):grouping[city].append(rec)
    if area not in grouping:area=''
    active=next((x for x in selected_ds if x['id']==district),None)
    if active and area and area not in municipalities(active['district']):active=None
    filtered=(grouping.get(area,[]) if area else selected_ds)
    if query.strip():
        search=query.strip().casefold()[:60]
        filtered=[x for x in filtered if search in x['district'].casefold() or search in x['winner']['name'].casefold()]
    chosen_ids={x['id'] for x in (grouping[area] if area else [])}
    region_rate=turnout['region_actual'].get(region_short)
    count_by_party=Counter(x['winner']['party'] for x in selected_ds)

    try:
        geo=load_geography()
        by_id={x['id']:x for x in all_d}
        if len(geo)!=254 or {f['properties']['id'] for f in geo}!=set(by_id):
            raise ValueError('선거구 ID 불일치')
        map_national=_svg_shapes(geo,by_id,mode='results',navigate='explorer',highlight_ids={x['id'] for x in selected_ds} if region else None)
        map_region=_svg_shapes(geo,by_id,region=region_short,mode='results',navigate='explorer',
                               selected_id=(active or {}).get('id',''),full_region=region,highlight_ids=chosen_ids,area=area) if region else ''
    except Exception:
        map_national=_fallback_photo(True)
        map_region=_fallback_photo(False) if region else ''

    provinces=''.join('<a class="'+('selected' if region==r else '')+'" href="'+esc(url(region=r))+'">'+esc(SHORT.get(r,r))+'</a>' for r in provs)
    intro='<div class="explore-breadcrumb"><a href="'+url()+'">전국</a>'
    if region:intro+=' <span>›</span> <a href="'+esc(url(region=region))+'">'+esc(region)+'</a>'
    if area:intro+=' <span>›</span> <a href="'+esc(url(region=region,area=area))+'">'+esc(area)+'</a>'
    if active:intro+=' <span>›</span> <strong>'+esc(active['district'])+'</strong>'
    intro+='</div>'
    # Hierarchical navigation is explicit, so browser-history or other-menu
    # navigation isn't required to return to a parent geographic level.
    if region:
        if active:
            parent=url(region=region, area=area) if area else url(region=region)
        elif area:
            parent=url(region=region)
        else:
            parent=url()
        intro += ('<nav class="explore-nav-actions" aria-label="지역 탐색 이동">'
                  '<a class="explore-nav-back" href="'+esc(parent)+'">← 이전 단계로</a>'
                  '<a class="explore-nav-national" href="'+esc(url())+'">⌂ 전국 지도 보기</a>'
                  '</nav>')

    # The top row is a LARGE nationwide map, the selected province map, and
    # the final candidate results. Province/municipality selectors move BELOW.
    left='<section class="explore-side explore-national"><h3>전국 17개 시·도 선택</h3><p class="explore-label">전국 지도에서 시·도를 선택하면 가운데 지도가 변경됩니다.</p>'
    left+='<div class="explore-national-map">'+map_national+'</div></section>'

    mid='<section class="explore-map explore-center">'
    if region:
        mid+='<h3>선택 지역 지도 · '+esc(region)+'</h3><p class="explore-label">'+str(len(selected_ds))+'개 지역구 · 당선 정당별 색상 지도</p>'+map_region
    else:
        mid+='<h3>선택 지역 지도</h3><p class="explore-label">왼쪽 전국 지도 또는 아래 시·도 목록에서 지역을 선택하세요.</p>'
        mid+='<div class="explore-map-placeholder">시·도를 선택하면 해당 지역의 지역구 지도가 나타납니다.</div>'
    mid+='</section>'

    left_bottom='<section class="explore-side explore-province-chooser"><h3>시·도 선택</h3>'
    left_bottom+='<div class="explore-provinces">'+provinces+'</div>'
    if region:
        left_bottom+='<div class="explore-summary-stats">'
        left_bottom+='<div class="explore-stat"><small>'+esc(region_short)+' 지역구</small><strong>'+str(len(selected_ds))+'석</strong></div>'
        if region_rate is not None:
            left_bottom+='<div class="explore-stat"><small>시·도 실제 최종 투표율</small><strong>'+f'{region_rate:.1f}%</strong></div>'
        left_bottom+='</div><p class="explore-label">시·도 투표율은 선관위가 발표한 최종 집계입니다.</p>'
    left_bottom+='</section>'

    mid_bottom='<section class="explore-side explore-list"><h3>시·군 / 지역구 목록 · 선택 및 검색</h3>'
    if not region:
        mid_bottom+='<p class="note">위쪽 전국 지도나 왼쪽 시·도 목록에서 시·도를 선택하세요.</p>'
    else:
        mid_bottom+='<p class="explore-label">선거구 이름으로 시·군을 분류한 탐색 목록입니다. 복수 시·군으로 이뤄진 선거구는 각 지역에 함께 표시됩니다.</p>'
        city_rows=''.join('<a href="'+esc(url(region=region,area=city))+'" class="'+('selected' if city==area else '')+'"><span>'+esc(city)+'</span><small>'+str(len(rows))+'개 지역구</small></a>' for city,rows in sorted(grouping.items()))
        mid_bottom+='<div class="explore-city-list"><a href="'+esc(url(region=region))+'" class="'+('selected' if not area else '')+'">전체 <small>'+str(len(selected_ds))+'</small></a>'+city_rows+'</div>'
        mid_bottom+='<form class="explore-search" action="/safe2024" method="get"><input type="hidden" name="page" value="district"><input type="hidden" name="region" value="'+esc(region)+'"><input type="hidden" name="area" value="'+esc(area)+'"><input name="q" aria-label="지역구 또는 당선인 이름 검색" placeholder="지역구·당선인 검색" value="'+esc(query[:60])+'"><button type="submit">검색</button></form>'
        selected_summary=esc(area) if area else esc(region_short)
        mid_bottom+='<p class="explore-label">'+selected_summary+' · 검색 결과 '+str(len(filtered))+'개 지역구</p><div class="explore-district-list">'
        for x in sorted(filtered,key=lambda z:z['district']):
            mid_bottom+='<a class="'+('selected' if active and active['id']==x['id'] else '')+'" href="'+esc(url(region=region,area=area,district=x['id'],q=query[:60]))+'"><span>'+esc(x['district'])+'</span><small style="color:'+COLORS.get(x['winner']['party'],'#bccddd')+'">'+esc(x['winner']['party'])+'</small></a>'
        mid_bottom+='</div>'
    mid_bottom+='</section>'

    right='<div class="explore-result">'
    if active:
        win=active['winner'];valid=int(active['valid']);votes=int(active['ballots']);reg=int(active['registered'])
        turnout_rate=votes/reg*100 if reg>0 and 0<=votes<=reg else None
        right+='<span class="winner-flag">✓ 최종 당선 · 개표율 100%</span>'
        right+='<h3 style="font-size:19px;margin-top:12px">'+esc(active['region'])+' '+esc(active['district'])+'</h3>'
        right+='<div class="winner-name" style="color:'+COLORS.get(win['party'],'#d5f1ff')+'">'+esc(win['name'])+' <small style="font-size:12px">'+esc(win['party'])+'</small></div>'
        right+='<p>당선인 득표율 <strong class="winner-votes">'+f'{win["share"]:.2f}%</strong></p>'
        if turnout_rate is not None:
            right+='<div class="explore-turnout"><small>해당 지역구 투표율 · 선관위 지역구 개표 원자료에서 계산</small><br><strong>'+f'{turnout_rate:.2f}%</strong><div class="track"><div class="fill" style="width:{turnout_rate:.2f}%"></div></div><small>투표수 '+f'{votes:,}'+'표 ÷ 선거인수 '+f'{reg:,}'+'명 × 100</small></div>'
        else:
            right+='<p class="note">해당 지역구의 투표율을 산출할 수 없습니다. 선거인수 또는 투표수를 확인해 주세요.</p>'
        right+='<h3>후보별 최종 득표 비교</h3>'
        for candidate in sorted(active['candidates'],key=lambda x:-x['votes']):
            col=COLORS.get(candidate['party'],'#84a3be')
            right+='<div class="explore-vote-row"><div class="explore-vote-name"><span>'+esc(candidate['name'])+' · '+esc(candidate['party'])+'</span><b>'+f'{candidate["votes"]:,}'+'표 ('+f'{candidate["share"]:.2f}'+'%)</b></div><div class="explore-vote-track"><i style="width:'+f'{candidate["share"]:.2f}'+'%;background:'+col+'"></i></div></div>'
        right+='<div class="box-note"><strong>1·2위 득표차 '+f'{active["margin"]:,}'+'표</strong><p style="margin:6px 0 0">유효투표 '+f'{valid:,}'+'표 · 무효투표 '+f'{active["invalid"]:,}'+'표</p></div>'
        right+='<p class="explore-label">출처: 선관위 제22대 총선 지역구 개표 결과 · 원자료 지역구 시트 '+str(active['excel_row'])+'행 · 지역구 ID '+esc(active['id'])+'<br>투표율은 개표 원자료에서 계산한 비율이며 선관위 발표 시·도 전체 투표율과 구분됩니다.</p>'
    elif region:
        right+='<h3>'+esc(area or region)+' 최종 결과 안내</h3>'
        right+='<p class="note">가운데에서 시·군 또는 지역구를 선택하면 후보별 실제 득표율·득표수·득표차와 지역구 투표율을 볼 수 있습니다.</p>'
        if region_rate is not None:right+='<div class="explore-turnout"><small>'+esc(region_short)+' 시·도 전체 실제 투표율</small><br><strong>'+f'{region_rate:.1f}%</strong></div>'
        right+='<h3>지역구 당선 정당별 현황</h3>'
        for party,num in count_by_party.most_common():
            right+='<div class="explore-vote-row"><div class="explore-vote-name"><span>'+esc(party)+'</span><b>'+str(num)+'석</b></div><div class="explore-vote-track"><i style="background:'+COLORS.get(party,'#91aac1')+';width:'+f'{num/len(selected_ds)*100:.1f}'+'%"></i></div></div>'
    else:
        right+='<h3>지역구별 상세 자료</h3><p class="note">전국 지도를 클릭해 시·도를 선택하면 지역별 당선인과 투표율을 탐색할 수 있습니다.</p>'
        right+='<div class="explore-summary-stats"><div class="explore-stat"><small>전체 지역구</small><strong>254석</strong></div><div class="explore-stat"><small>전국 실제 투표율</small><strong>'+f'{turnout["national"]["final"]:.1f}%</strong></div></div>'
    right+='</div>'

    return (intro+'<div class="explore-grid">'+left+mid+right+'</div>'
            +'<div class="explore-bottom-grid">'+left_bottom+mid_bottom+'</div>'
            +'<p class="note">자료 범위: 제22대 국회의원선거 확정 지역구 개표 결과. 시·군 목록은 선거구 명칭 기반 분류이며 행정구역 경계 자료가 아닙니다. 후보 사진이나 확인되지 않은 투표율은 사용하지 않습니다.</p>')
