"""Read the imported 2024 election from election_lab (PostgreSQL).

The imported source_documents JSONB carries provenance and stable API shape;
all election vote counts and turnout rates below are read from normalized SQL
rows. Missing or inconsistent rows are errors, never silent local JSON fallback.
"""
from __future__ import annotations

import os
from collections import defaultdict
from decimal import Decimal
from fastapi import HTTPException

SCHEMA = 'election_lab'
EXPECTED = {'district_results': 254, 'district_candidates': 693,
            'proportional_areas': 253, 'proportional_area_parties': 9614,
            'proportional_nation_parties': 38, 'region_summaries': 17,
            'turnout_rates': 106, 'source_documents': 2}


def active() -> bool:
    return os.getenv('NEWSROOM_DATA_SOURCE', '').lower() == 'postgres'


def _connect():
    try:
        import psycopg
    except ImportError as exc:
        raise HTTPException(503, 'PostgreSQL 드라이버(psycopg)가 설치되어 있지 않습니다.') from exc
    try:
        return psycopg.connect(host=os.getenv('NEWSROOM_PG_HOST', 'localhost'),
                              port=os.getenv('NEWSROOM_PG_PORT', '5432'),
                              dbname=os.getenv('NEWSROOM_PG_DB', 'Election2024'),
                              user=os.getenv('NEWSROOM_PG_USER', 'postgres'),
                              password=os.environ.get('NEWSROOM_PG_PASSWORD', ''),
                              connect_timeout=6, options='-c statement_timeout=12000',
                              autocommit=True)
    except Exception as exc:
        # Avoid returning a DSN, password or other credential in HTTP errors.
        raise HTTPException(503, 'PostgreSQL 연결에 실패했습니다. 서버 실행 여부와 접속 정보를 확인하세요.') from exc


def _fetch(cur, sql, args=()):
    try:
        cur.execute(sql, args)
        return cur.fetchall()
    except Exception as exc:
        raise HTTPException(503, 'PostgreSQL 선거 데이터 조회에 실패했습니다. election_lab 테이블을 확인하세요.') from exc


def _doc(cur, name):
    rows = _fetch(cur, 'SELECT payload FROM election_lab.source_documents WHERE dataset_name = %s', (name,))
    if len(rows) != 1 or not isinstance(rows[0][0], dict):
        raise HTTPException(503, f'PostgreSQL에 {name} 원본 JSONB가 없습니다. 데이터 입력 도구를 다시 확인하세요.')
    return rows[0][0]


def _count_check(actual, expected, label):
    if actual != expected:
        raise HTTPException(503, f'PostgreSQL {label} 자료 건수가 일치하지 않습니다. 예상 {expected}, 조회 {actual}')


def _same_keys(expected, actual, label):
    if expected != actual:
        raise HTTPException(503, f'PostgreSQL {label} 자료와 원본 색인이 불일치합니다. 입력 상태를 점검하세요.')


def _f(n):
    return float(n) if isinstance(n, Decimal) else n


def load_election():
    with _connect() as connection:
        with connection.cursor() as cur:
            data = _doc(cur, 'election_2024')
            districts = data['constituency']['districts']
            _count_check(len(districts), 254, '지역구')
            drows = _fetch(cur, '''SELECT district_id, region, district_name, registered, ballots,
                    valid_votes, invalid_votes, abstained, winner_name, winner_party, margin_votes, excel_row
                    FROM election_lab.district_results''')
            crows = _fetch(cur, '''SELECT district_id, candidate_name, party, votes, share_percent
                    FROM election_lab.district_candidates''')
            _count_check(len(drows), 254, '지역구 테이블')
            _count_check(len(crows), 693, '지역구 후보 테이블')
            district_by_id = {r[0]: r for r in drows}
            candidate_by_id = defaultdict(dict)
            for id_, name, party, votes, share in crows:
                candidate_by_id[id_][(name, party)] = (votes, _f(share))
            _same_keys(set(d['id'] for d in districts), set(district_by_id), '지역구 ID')
            for d in districts:
                r = district_by_id[d['id']]
                _, d['region'], d['district'], d['registered'], d['ballots'], d['valid'], \
                    d['invalid'], d['abstained'], winner_name, winner_party, d['margin'], d['excel_row'] = r
                original_keys = {(c['name'], c['party']) for c in d['candidates']}
                actual = candidate_by_id[d['id']]
                _same_keys(original_keys, set(actual), '지역구 후보')
                for c in d['candidates']:
                    c['votes'], c['share'] = actual[(c['name'], c['party'])]
                if sum(c['votes'] for c in d['candidates']) != d['valid']:
                    raise HTTPException(503, '지역구 득표 합계가 DB의 유효투표수와 다릅니다.')
                winners = [c for c in d['candidates'] if c['name']==winner_name and c['party']==winner_party]
                if len(winners) != 1:
                    raise HTTPException(503, '지역구 당선자 정보가 후보 테이블과 일치하지 않습니다.')
                d['winner'] = dict(winners[0])

            nrows = _fetch(cur, '''SELECT election_date, registered, ballots, valid_votes, invalid_votes,
                    abstained, excel_row FROM election_lab.proportional_nation''')
            _count_check(len(nrows), 1, '비례 전국 합계')
            n = data['proportional']['nation']
            _, n['registered'], n['ballots'], n['valid'], n['invalid'], n['abstained'], n['excel_row'] = nrows[0]
            prows = _fetch(cur, 'SELECT party, votes, share_percent FROM election_lab.proportional_nation_parties')
            _count_check(len(prows), 38, '비례 전국 정당')
            by_party = {party: (votes, _f(share)) for party,votes,share in prows}
            _same_keys({p['party'] for p in n['parties']}, set(by_party), '비례 전국 정당명')
            for p in n['parties']:
                p['votes'], p['share'] = by_party[p['party']]
            if sum(p['votes'] for p in n['parties']) != n['valid']:
                raise HTTPException(503, '비례 전국 합계가 일치하지 않습니다.')

            arows = _fetch(cur, '''SELECT region, area_name, registered, ballots, valid_votes,
                    invalid_votes, excel_row FROM election_lab.proportional_areas''')
            ap_rows = _fetch(cur, '''SELECT region, area_name, party, votes, share_percent
                    FROM election_lab.proportional_area_parties''')
            _count_check(len(arows), 253, '비례 지역 집계')
            _count_check(len(ap_rows), 9614, '비례 지역 정당')
            areas = data['proportional']['areas']
            area_map = {(r[0],r[1]):r for r in arows}
            area_party = defaultdict(dict)
            for region,area,party,votes,share in ap_rows:
                area_party[(region,area)][party] = (votes, _f(share))
            _same_keys({(a['region'], a['area']) for a in areas}, set(area_map), '비례 지역명')
            for a in areas:
                key = a['region'], a['area']; r = area_map[key]
                _, _, a['registered'],a['ballots'],a['valid'],a['invalid'],a['excel_row'] = r
                _same_keys({p['party'] for p in a['parties']}, set(area_party[key]), '비례 지역 정당명')
                for p in a['parties']:
                    p['votes'], p['share'] = area_party[key][p['party']]
                if sum(p['votes'] for p in a['parties']) != a['valid']:
                    raise HTTPException(503, '비례 지역 집계의 정당 득표 합계가 다릅니다.')

            regions = dict(_fetch(cur, 'SELECT region,payload FROM election_lab.region_summaries'))
            _count_check(len(regions), 17, '지역 요약')
            old_regions = data['constituency']['regions']
            _same_keys({r['name'] for r in old_regions}, set(regions), '지역 요약명')
            data['constituency']['regions'] = [regions[r['name']] for r in old_regions]
            seat_rows = _fetch(cur, 'SELECT seat_type,party,seats FROM election_lab.seat_totals')
            seats = defaultdict(dict)
            for typ, party, value in seat_rows: seats[typ][party] = value
            _same_keys(set(data['constituency']['seats_by_party']),set(seats['regional']),'지역구 의석 정당명')
            _same_keys(set(data['proportional']['seat_allocation']),set(seats['proportional']),'비례 의석 정당명')
            data['constituency']['seats_by_party'] = seats['regional']
            data['proportional']['seat_allocation'] = seats['proportional']
            return data


def load_turnout():
    with _connect() as connection:
        with connection.cursor() as cur:
            t = _doc(cur, 'turnout_2024')
            rows = _fetch(cur, '''SELECT metric_group, item, subgroup, rate_percent
                    FROM election_lab.turnout_rates''')
            _count_check(len(rows), 106, '투표율 테이블')
            rates = {(group,item,sub):_f(value) for group,item,sub,value in rows}
            consumed = set()
            def lookup(group,item,sub=''):
                key=(group,item,sub)
                if key not in rates:
                    raise HTTPException(503, f'PostgreSQL에 필요한 투표율 항목이 없습니다: {group}/{item}/{sub}')
                consumed.add(key)
                return rates[key]
            for key in ('final','sample','early','total_voter_early_share'):
                t['national'][key]=lookup('national',key)
            for key in t['national']['vote_method_share']:
                t['national']['vote_method_share'][key]=lookup('vote_method_share',key)
            for group in ('sex','age','early_sex','early_age','region_sample','region_actual','region_early'):
                for item in t[group]:t[group][item]=lookup(group,item)
            for sub in t['age_sex']:
                for item in t['age_sex'][sub]:t['age_sex'][sub][item]=lookup('age_sex',item,sub)
            t['election_day']['all']=lookup('election_day','all')
            for item in t['election_day']['sex']:
                t['election_day']['sex'][item]=lookup('election_day_sex',item)
            _same_keys(set(rates), consumed, '투표율 항목')
            return t


def db_status():
    if not active():return {'active':False,'backend':'local_json'}
    with _connect() as connection:
        with connection.cursor() as cur:
            counts = {}
            for table, expected in EXPECTED.items():
                counts[table] = _fetch(cur,'SELECT count(*) FROM election_lab.'+table)[0][0]
                _count_check(counts[table], expected, table)
            return {'active':True,'backend':'PostgreSQL','database':os.getenv('NEWSROOM_PG_DB','Election2024'),
                    'schema':SCHEMA,'counts':counts,'ok':True,
                    'notice':'웹 대시보드 개표·투표율은 election_lab의 SQL 테이블에서 조회합니다. 실시간 개표자료가 아닙니다.'}
