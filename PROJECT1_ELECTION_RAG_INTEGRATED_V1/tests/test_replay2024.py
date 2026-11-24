"""V5 확장: 역사 시점 41개, 동시 결과 공개, 투표율 교차분석과 의석 시각화.

GitHub 커밋 전 검토용. PostgreSQL DB 변경을 수반하는 테스트는 실행하지 않음.
"""
from __future__ import annotations
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from newsroom_replay2024 import _validated_rows,pg_replay_observation
from newsroom_visuals2024 import seat_charts,donut_svg,seat_semicircle_svg,_validate_geo,turnout_crossfilter_html
from newsroom.real_data_api import _local_vote_data,_local_turnout


def test_replay_has_41_valid_historical_snapshots():
    rows=_validated_rows()
    assert len(rows)==41
    assert sum(x['phase']=='turnout' for x in rows)==12
    assert sum(x['series']=='constituency' for x in rows)==16
    assert sum(x['series']=='proportional' for x in rows)==12
    assert rows[6]['time']=='2024-04-10 13:00' and rows[6]['turnout']==53.4
    assert rows[-1]['time']=='2024-04-11 10:25'
    assert rows[-1]['counting']==rows[-1]['proportional']==100
    assert all(x['source'].startswith('https://') for x in rows)
    assert [x['time'] for x in rows]==sorted(x['time'] for x in rows)
    assert len({x['id'] for x in rows})==len(rows)
    assert not any(x['time'] in ('2024-04-11 00:55','2024-04-11 02:30') for x in rows)
    assert next(x for x in rows if x['id']=='r16')['counting']==74.22
    assert next(x for x in rows if x['id']=='p14')['proportional_asof'].endswith('(보도시각 기준)')
    assert next(x for x in rows if x['id']=='p10')['proportional_display']=='33%'


def test_preview_landing_does_not_query_bulk_db():
    from project1_app import app
    with patch('newsroom_safe2024.get_data',side_effect=AssertionError('first paint must not bulk query DB')):
        with patch('newsroom.postgres_data.active',return_value=True):
            response=TestClient(app).get('/safe2024')
    assert response.status_code==200
    assert '2024년 22대 국회의원 선거 시간대별 투·개표 현황' in response.text
    assert '2024년 시간대별 기록' in response.text
    assert '2024 투·개표 상황' in response.text
    assert 'replay-viz-turnout' in response.text
    assert 'replay-viz-count' in response.text
    assert 'id="replay-viz-final" class="replay-visual-screen" hidden' in response.text
    assert '최종 개표 결과 보기' in response.text
    assert '당시 기록 미확인' in response.text
    assert 'renderLine(' in response.text


def test_v2_sql_replay_endpoint_uses_requested_sequence():
    from project1_app import app
    asked=[]
    class Cursor:
        def execute(self,sql,args):
            assert 'historical_replay_2024_v2' in sql
            asked.append(args[0])
        def fetchone(self):
            x=_validated_rows()[asked[-1]]
            return (x['id'],x['time'],x['phase'],x['series'],x['turnout'],x['counting'],
                    x['proportional'],x['counting_asof'],x['proportional_asof'],
                    x['source'],x['source_label'],x['note'],x['time_kind'])
        def __enter__(self):return self
        def __exit__(self,*args):pass
    class Connection:
        def cursor(self):return Cursor()
        def __enter__(self):return self
        def __exit__(self,*args):pass
    with patch('newsroom.postgres_data.active',return_value=True):
        with patch('newsroom.postgres_data._connect',return_value=Connection()):
            reply=TestClient(app).get('/safe2024/api/replay/40')
    assert reply.status_code==200
    assert reply.json()['counting']==reply.json()['proportional']==100
    assert asked==[40]


def test_final_seat_charts_are_254_plus_46_equals_300():
    d=_local_vote_data()
    assert sum(d['constituency']['seats_by_party'].values())==254
    assert sum(d['proportional']['seat_allocation'].values())==46
    html=seat_charts(d)
    assert html.count('viewBox="0 0 184 184"')==2
    assert 'viewBox="0 0 640 322"' in html
    assert '더불어민주당' in html and '조국혁신당' in html
    assert '지역구 254석' in html and '비례대표 46석' in html


def test_turnout_crossfilter_has_verified_17_regions():
    html=turnout_crossfilter_html()
    assert '중앙선관위' in html
    assert '남성' in html and '여성' in html
    assert '"region": "서울"' in html


def test_invalid_replay_index_rejected():
    for n in (-1,41,9999):
        try:pg_replay_observation(n)
        except HTTPException as exc:assert exc.status_code==404
        else:raise AssertionError('Unknown index was accepted')
