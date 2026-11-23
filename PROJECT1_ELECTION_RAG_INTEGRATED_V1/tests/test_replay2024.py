"""2024 election replay v2: historical observations, map, and UI regression."""
from __future__ import annotations

from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from newsroom_replay2024 import dataset, pg_replay_observation, _validated_rows
from newsroom_election_map import shapes, election_result_map
from newsroom.real_data_api import _local_vote_data


def test_archive_uses_real_snapshots_only():
    rows = _validated_rows()
    assert len(rows) == 40
    assert sum(x['phase'] == 'turnout' for x in rows) == 12
    assert sum(x['series'] == 'constituency' for x in rows) == 15
    assert sum(x['series'] == 'proportional' for x in rows) == 12
    assert rows[0]['time'] == '2024-04-10 07:00' and rows[0]['turnout'] == 1.8
    assert next(x for x in rows if x['time']=='2024-04-10 23:30' and x['series']=='proportional')['proportional'] == 10.6
    assert next(x for x in rows if x['time']=='2024-04-11 00:30' and x['series']=='proportional')['proportional'] == 20.56
    assert next(x for x in rows if x['time']=='2024-04-11 01:30' and x['series']=='proportional')['proportional_display'] == '33%'
    assert next(x for x in rows if x['time']=='2024-04-11 02:33' and x['series']=='proportional')['proportional'] == 48.75
    reported=next(x for x in rows if x['id']=='p14')
    assert reported['time']=='2024-04-11 03:37' and reported['proportional']==59.18
    assert reported['time_kind'].startswith('보도시각 기준')
    assert reported['proportional_asof'].endswith('(보도시각 기준)')
    assert not any(x['time'] in ('2024-04-11 00:55','2024-04-11 02:30') for x in rows)
    assert rows[6]['time'] == '2024-04-10 13:00' and rows[6]['turnout'] == 53.4
    assert rows[-1]['time'] == '2024-04-11 10:25'
    assert rows[-1]['counting'] == rows[-1]['proportional'] == 100
    assert len({x['id'] for x in rows}) == len(rows)
    assert all(x['source'].startswith('https://') and x['source_label'] for x in rows)
    assert all(x['counting'] is None and x['proportional'] is None for x in rows[:12])
    assert [x['time'] for x in rows] == sorted(x['time'] for x in rows)
    for field in ('counting', 'proportional'):
        series = [x[field] for x in rows if x[field] is not None]
        assert series == sorted(series)


def test_landing_page_avoids_bulk_db_and_hides_final_map():
    from project1_app import app
    with patch('newsroom_safe2024.get_data', side_effect=AssertionError('bulk DB on landing')):
        with patch('newsroom.postgres_data.active', return_value=True):
            html = TestClient(app).get('/safe2024')
    assert html.status_code == 200
    assert '2024년 22대 국회의원 선거 시간대별 투·개표 현황' in html.text
    assert '2024년 시간대별 기록' in html.text
    assert '2024 투개표 상황' in html.text
    assert 'id="replay-final-map" class="replay-finale" hidden' in html.text
    assert 'id="replay-pr"' in html.text
    assert 'id="replay-pr">개표 전' in html.text
    assert '당시 기록 미확인' in html.text
    assert '/safe2024/api/replay/' in html.text


def test_db_endpoint_reads_v2_sequence():
    from project1_app import app
    requests = []
    class Cursor:
        def execute(self, sql, args):
            assert 'historical_replay_2024_v2' in sql
            requests.append(args[0])
        def fetchone(self):
            x = _validated_rows()[requests[-1]]
            return (x['id'], x['time'], x['phase'], x['series'], x['turnout'],
                    x['counting'], x['proportional'], x['counting_asof'],
                    x['proportional_asof'], x['source'], x['source_label'],
                    x['note'], x['time_kind'])
        def __enter__(self): return self
        def __exit__(self, *args): pass
    class Connection:
        def cursor(self): return Cursor()
        def __enter__(self): return self
        def __exit__(self, *args): pass
    with patch('newsroom.postgres_data.active', return_value=True):
        with patch('newsroom.postgres_data._connect', return_value=Connection()):
            response = TestClient(app).get('/safe2024/api/replay/12')
    assert response.status_code == 200
    assert response.json()['counting'] == 16.14
    assert response.json()['proportional'] is None
    assert requests == [12]


def test_map_geometry_matches_254_real_district_ids():
    data = _local_vote_data()
    geo = shapes()
    assert len(geo) == 254
    assert len({f['properties']['region'] for f in geo}) == 17
    ids = {f['properties']['id'] for f in geo}
    assert ids == {d['id'] for d in data['constituency']['districts']}
    nationwide = election_result_map(data)
    assert '전국 254개 지역구 최종 개표' in nationwide
    assert '경기 지역 지도 열기' in nationwide
    province = election_result_map(data, '경기')
    assert '지역구 선택' in province
    assert province.count('class="cross-reg-item"') == 0
    sample = next(d for d in data['constituency']['districts'] if d['region'] == '경기도')
    detail = election_result_map(data, '경기', sample['id'])
    assert sample['winner']['name'] in detail
    assert f"{sample['margin']:,}표" in detail


def test_invalid_sequence_rejected():
    for n in (-1, 40, 9999):
        try:
            pg_replay_observation(n)
        except HTTPException as exc:
            assert exc.status_code == 404
        else:
            raise AssertionError('Unknown snapshot was accepted')
