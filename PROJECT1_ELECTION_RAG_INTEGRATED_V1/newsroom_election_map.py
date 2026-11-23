"""2024 final constituency election map. Server-side SVG, no remote scripts.

All 254 constituency results must come from the existing validated PostgreSQL
adapter. Only polygon geometry and shape IDs come from OhmyNews' MIT GeoJSON.
"""
from __future__ import annotations

import html
import json
from collections import Counter, defaultdict
from functools import lru_cache
from math import cos, radians
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent
GEOMETRY = ROOT / 'newsroom' / 'static' / 'map_22nd_2024.geojson'
MAP_ROUTE = '/safe2024/map'
SHORT = {
    '서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구',
    '인천광역시': '인천', '광주광역시': '광주', '대전광역시': '대전',
    '울산광역시': '울산', '세종특별자치시': '세종', '경기도': '경기',
    '강원특별자치도': '강원', '충청북도': '충북', '충청남도': '충남',
    '전북특별자치도': '전북', '전라남도': '전남', '경상북도': '경북',
    '경상남도': '경남', '제주특별자치도': '제주'
}
PARTY_COLORS = {
    '더불어민주당': '#246fcc', '국민의힘': '#d4475d',
    '개혁신당': '#ec8c32', '새로운미래': '#2db0c5',
    '진보당': '#a463d5'
}

def e(s):
    return html.escape(str(s), quote=True)

@lru_cache(maxsize=1)
def shapes():
    payload = json.loads(GEOMETRY.read_text(encoding='utf-8'))
    features = payload['features']
    ids = [f['properties']['id'] for f in features]
    if len(ids) != 254 or len(set(ids)) != 254:
        raise ValueError('254개 지역구 지도 ID가 완전하지 않습니다.')
    return features

def xy_points(geometry):
    """Return all rings; do not turn holes into fictional districts."""
    kind = geometry['type']
    coords = geometry['coordinates']
    if kind == 'Polygon':
        return coords
    if kind == 'MultiPolygon':
        return [ring for polygon in coords for ring in polygon]
    raise ValueError('지원하지 않는 지도 경계 유형')

def election_result_map(data, region='', district=''):
    districts = data['constituency']['districts']
    if len(districts) != 254:
        raise ValueError('지역구 원자료가 254건이 아닙니다.')
    by_id = {d['id']: d for d in districts}
    if len(by_id) != 254 or set(by_id) != set(f['properties']['id'] for f in shapes()):
        raise ValueError('지역구 선거 결과와 지도 경계 ID가 일치하지 않습니다.')

    features = shapes()
    available = sorted(set(f['properties']['region'] for f in features))
    if region and region not in available:
        region = ''
    visible = [f for f in features if f['properties']['region'] == region] if region else features
    selected = by_id.get(district)
    if selected and (not region or SHORT.get(selected['region'], selected['region']) != region):
        selected = None

    bounds = []
    for feature in visible:
        for ring in xy_points(feature['geometry']):
            for lon, lat in ring:
                bounds.append((lon * 0.8, lat))
    lo_x = min(p[0] for p in bounds); hi_x = max(p[0] for p in bounds)
    lo_y = min(p[1] for p in bounds); hi_y = max(p[1] for p in bounds)
    pad = 36
    view_w, view_h = 860, 700
    scale = min((view_w - pad * 2) / max(0.00001, hi_x - lo_x),
                (view_h - pad * 2) / max(0.00001, hi_y - lo_y))
    extra_x = (view_w - (hi_x - lo_x) * scale) / 2
    extra_y = (view_h - (hi_y - lo_y) * scale) / 2

    def point(lon, lat):
        return (extra_x + (lon * 0.8 - lo_x) * scale,
                view_h - extra_y - (lat - lo_y) * scale)

    def path_for(geom):
        out = []
        for ring in xy_points(geom):
            if len(ring) < 3:
                continue
            coords = [point(*p) for p in ring]
            out.append('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in coords) + 'Z')
        return ''.join(out)

    p_count = Counter(by_id[f['properties']['id']]['winner']['party'] for f in visible)
    paths, provinces = [], defaultdict(list)
    for f in visible:
        props = f['properties']
        d = by_id[props['id']]
        winner = d['winner']
        party = winner['party']
        color = PARTY_COLORS.get(party, '#7287a5')
        link = (MAP_ROUTE + '?' + urlencode({'region': region, 'district': props['id']})) if region else (MAP_ROUTE + '?' + urlencode({'region': props['region']}))
        title = f"{props['name']} · {winner['name']} · {party} · {winner['share']:.2f}%"
        paths.append(
            f'<a href="{e(link)}" aria-label="{e(title)}"><path d="{path_for(f["geometry"])}" '
            f'fill="{color}" stroke="#0a2033" stroke-width="{1.4 if region else 0.8}" '
            f'class="district-shape{" picked" if selected and selected["id"] == d["id"] else ""}">'
            f'<title>{e(title)}</title></path></a>')
        provinces[props['region']].append(f)

    labels = []
    if not region:
        for p, fs in provinces.items():
            # Label centers are placed on the largest component of a province.
            rings = [r for f in fs for r in xy_points(f['geometry']) if len(r) > 3]
            main_ring = max(rings, key=lambda r: (
                max(x[0] for x in r) - min(x[0] for x in r)) *
                (max(x[1] for x in r) - min(x[1] for x in r)))
            x = (max(z[0] for z in main_ring) + min(z[0] for z in main_ring)) / 2
            y = (max(z[1] for z in main_ring) + min(z[1] for z in main_ring)) / 2
            px, py = point(x, y)
            link = MAP_ROUTE + '?' + urlencode({'region': p})
            labels.append(f'<a href="{e(link)}" aria-label="{e(p)} 지역 지도 열기">'
                          f'<text x="{px:.1f}" y="{py:.1f}" class="region-label">{e(p)}</text></a>')

    tally = ''.join(f'<div><span class="dot" style="background:{PARTY_COLORS.get(p,"#7287a5")}"></span>{e(p)}<strong>{n}석</strong></div>'
                    for p, n in sorted(p_count.items(), key=lambda x: -x[1]))
    controls = ('<p class="navlinks"><a href="' + MAP_ROUTE + '">◀ 전국 지도</a></p>') if region else ''
    if region:
        district_rows = sorted((by_id[f['properties']['id']] for f in visible), key=lambda d: d['district'])
        options = ''.join('<a class="' + ('active' if selected and selected['id'] == d['id'] else '') +
                          '" href="' + MAP_ROUTE + '?' + urlencode({'region': region, 'district': d['id']}) +
                          '">' + e(d['district']) + '</a>' for d in district_rows)
        chooser = f'<div class="district-list" aria-label="지역구 선택">{options}</div>'
    else:
        chooser = '<div class="province-list">' + ''.join(
            '<a href="' + MAP_ROUTE + '?' + urlencode({'region': p}) + '">' + e(p) + '</a>'
            for p in available) + '</div>'

    if selected:
        cand = sorted(selected['candidates'], key=lambda x: -x['votes'])
        rows = ''.join(
            f'<tr><td>{e(c["name"])}</td><td>{e(c["party"])}</td>'
            f'<td class="num">{c["votes"]:,}</td><td class="num">{c["share"]:.2f}%</td></tr>'
            for c in cand)
        detail = f'<section class="details"><h3>{e(selected["region"])} {e(selected["district"])}</h3>' + (
            f'<p><strong>당선: {e(selected["winner"]["name"])} ({e(selected["winner"]["party"])})</strong></p>'
            f'<p>1·2위 득표차: {selected["margin"]:,}표 · 유효투표: {selected["valid"]:,}표</p>'
            f'<div class="table-scroll"><table><thead><tr><th>후보</th><th>정당</th><th>득표수</th><th>득표율</th></tr></thead><tbody>{rows}</tbody></table></div></section>')
    else:
        detail = '<p class="muted">' + ('왼쪽 지도나 지역구 이름을 클릭하면 후보별 득표수를 확인할 수 있습니다.' if region else '지도에서 시·도를 선택하면 지역구별 당선 정당 지도와 후보별 결과가 나타납니다.') + '</p>'

    h = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>2024년 제22대 총선 개표 결과 지도</title>
    <style>
      :root{{font-family:"Malgun Gothic",system-ui,sans-serif;color-scheme:dark}}
      *{{box-sizing:border-box}}body{{margin:0;background:#101e32;color:#f1f6ff}}
      h2{{margin:4px 0 8px;font-size:23px}}h3{{font-size:17px}}
      a{{color:#b4e6fb}}.muted{{color:#a9bdd4;font-size:13px;line-height:1.65}}
      .wrap{{padding:14px}}.grid{{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(300px,1fr);gap:16px}}
      .mapbox{{border:1px solid #2d4e65;border-radius:12px;background:#0b192b;min-width:0}}
      svg{{width:100%;height:auto;max-height:760px;display:block}}
      .district-shape{{transition:stroke-width .12s,filter .12s;cursor:pointer}}
      .district-shape:hover,.district-shape:focus,.district-shape.picked{{stroke:#fff;stroke-width:3;filter:brightness(1.3)}}
      .region-label{{fill:#fff;paint-order:stroke;stroke:#15243c;stroke-width:3px;font-weight:800;font-size:13px;text-anchor:middle;cursor:pointer}}
      .aside{{border:1px solid #2d4e65;border-radius:12px;padding:17px;background:#132a42}}
      .seat-summary{{display:grid;gap:7px}}.seat-summary div{{display:flex;gap:8px;align-items:center;font-size:13px}}
      .seat-summary strong{{margin-left:auto}}.dot{{width:12px;height:12px;display:inline-block;border-radius:2px}}
      .province-list,.district-list{{display:flex;flex-wrap:wrap;gap:5px;max-height:180px;overflow-y:auto;padding:7px 0}}
      .province-list a,.district-list a{{border:1px solid #476079;border-radius:5px;padding:7px 9px;text-decoration:none;font-size:12px}}
      .district-list a.active,.province-list a:hover,.district-list a:hover{{background:#1e6f8f}}
      .navlinks{{margin:0 0 7px}}.details{{border-top:1px solid #355572;margin-top:12px;padding-top:10px}}
      table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{padding:8px 5px;border-bottom:1px solid #36516b;text-align:left}}
      .num{{text-align:right;white-space:nowrap}}.table-scroll{{overflow-x:auto}}
      @media(max-width:760px){{.grid{{grid-template-columns:1fr}}.wrap{{padding:7px}}.aside{{padding:13px}}}}
    </style></head><body><main class="wrap">
    {controls}<h2>{e(region + " 지역구 최종 개표" if region else "전국 254개 지역구 최종 개표")}</h2>
    <p class="muted">2024년 제22대 총선 확정 결과 · 지도 색상은 지역구 당선 정당 · 실시간 중계 아님</p>
    <div class="grid"><section class="mapbox" aria-label="선거구 지도">
       <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 700" role="img" aria-label="지역구 당선 정당별 개표 결과 지도">
       {''.join(paths)}{''.join(labels)}</svg>
       </section><aside class="aside"><h3>{e(region) + " " if region else ""}지역구 의석</h3><div class="seat-summary">{tally}</div>
       <h3>{'지역구 선택' if region else '시·도 선택'}</h3>{chooser}{detail}
       </aside></div>
    <p class="muted">득표수·당선자는 기존 선관위 확정 개표자료(PostgreSQL) · 254개 선거구 지도 경계: 오마이뉴스 2024_22_elec_map(MIT).</p>
    </main></body></html>"""
    return h

def map_frame(height=870):
    return (f'<iframe title="제22대 총선 지역구 확정 개표 지도" '
            f'src="{MAP_ROUTE}" style="width:100%;height:{int(height)}px;border:1px solid #315174;'
            'border-radius:12px;background:#101e32" loading="lazy"></iframe>')
