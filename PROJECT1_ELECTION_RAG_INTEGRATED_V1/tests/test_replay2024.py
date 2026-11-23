"""Archived 2024 replay must not masquerade as live counting."""
from __future__ import annotations

import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from newsroom_replay2024 import dataset, pg_replay_observation


def test_snapshot_archival_data_provenance():
    rows=dataset()['events']
    assert len(rows)==20
    assert len([x for x in rows if x['phase']=='turnout'])==12
    assert len([x for x in rows if x['phase']=='counting'])==7
    assert rows[0]['time']=='2024-04-10 07:00' and rows[0]['turnout']==1.8
    assert rows[6]['time']=='2024-04-10 13:00' and rows[6]['turnout']==53.4
    assert rows[-1]['counting']==100 and rows[-1]['time']=='최종 확정 (시각 미확인)'
    assert all(x['source'].startswith('https://') and x['source_label'] for x in rows)
    assert all(x['counting'] is None for x in rows[:12])
    assert [x['counting'] for x in rows[12:]]==sorted(x['counting'] for x in rows[12:])


def test_first_page_does_not_wait_for_bulk_db():
    from project1_app import app
    with patch('newsroom_safe2024.get_data',side_effect=AssertionError('bulk DB read on landing')):
        with patch('newsroom.postgres_data.active',return_value=True):
            response=TestClient(app).get('/safe2024')
    assert response.status_code==200
    assert '2024년 총선 시간별 재생' in response.text
    assert '1.8%' in response.text and '실시간 연결 아님' in response.text
    assert '/safe2024/api/replay/' in response.text
    assert '/safe2024?page=final' in response.text


def test_db_endpoint_reads_only_requested_sequence():
    from project1_app import app
    requested=[]
    class Cursor:
        def execute(self,sql,args):
            assert 'historical_replay_2024' in sql
            requested.append(args[0])
        def fetchone(self):
            x=dataset()['events'][requested[-1]]
            return (x['id'],x['time'],x['phase'],x['turnout'],x['counting'],x['source'],x['source_label'],x['note'])
        def __enter__(self):return self
        def __exit__(self,*_):pass
    class Conn:
        def cursor(self):return Cursor()
        def __enter__(self):return self
        def __exit__(self,*_):pass
    with patch('newsroom.postgres_data.active',return_value=True):
        with patch('newsroom.postgres_data._connect',return_value=Conn()):
            response=TestClient(app).get('/safe2024/api/replay/12')
    assert response.status_code==200 and response.json()['counting']==16.14
    assert requested==[12]


def test_invalid_sequence_rejected():
    from fastapi import HTTPException
    for n in (-1,20,9999):
        try:
            pg_replay_observation(n)
        except HTTPException as exc:
            assert exc.status_code==404
        else:
            raise AssertionError('Invalid index returned a snapshot')
