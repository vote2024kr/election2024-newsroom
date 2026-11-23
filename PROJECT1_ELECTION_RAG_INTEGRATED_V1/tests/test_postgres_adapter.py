"""Isolated SQL adapter regression: no access to a user's local DB is assumed."""
import json
import copy
import re
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import HTTPException
import pytest

from project1_app import app
from newsroom import postgres_data
from newsroom.real_data_api import vote_data, turnout

DATA = Path(__file__).resolve().parents[1] / 'newsroom' / 'real_data'
E = json.loads((DATA / 'election_2024.json').read_text(encoding='utf-8'))
T = json.loads((DATA / 'turnout_2024.json').read_text(encoding='utf-8'))


def fixture_tables():
    tables = {}
    tables['source_documents'] = {'election_2024': E, 'turnout_2024': T}
    tables['district_results'] = [(d['id'],d['region'],d['district'],d['registered'],
       d['ballots'],d['valid'],d['invalid'],d['abstained'],d['winner']['name'],
       d['winner']['party'],d['margin'],d.get('excel_row')) for d in E['constituency']['districts']]
    tables['district_candidates'] = [(d['id'],c['name'],c['party'],c['votes'],c['share'])
       for d in E['constituency']['districts'] for c in d['candidates']]
    n = E['proportional']['nation']
    tables['proportional_nation'] = [(E['meta']['date'],n['registered'],n['ballots'],n['valid'],
                                   n['invalid'],n['abstained'],n.get('excel_row'))]
    tables['proportional_nation_parties'] = [(p['party'],p['votes'],p['share']) for p in n['parties']]
    tables['proportional_areas'] = [(a['region'],a['area'],a['registered'],a['ballots'],
        a['valid'],a['invalid'],a.get('excel_row')) for a in E['proportional']['areas']]
    tables['proportional_area_parties'] = [(a['region'],a['area'],p['party'],p['votes'],p['share'])
       for a in E['proportional']['areas'] for p in a['parties']]
    tables['region_summaries'] = [(r['name'],r) for r in E['constituency']['regions']]
    tables['seat_totals'] = [(type_,p,v) for type_, part in (
       ('regional',E['constituency']['seats_by_party']),
       ('proportional',E['proportional']['seat_allocation'])) for p,v in part.items()]
    # Avoid dependency on external migration folder in the delivered project.
    rates = []
    def add(g, i, rate, sub=''): rates.append((g,i,sub,rate))
    for k in ('final','sample','early','total_voter_early_share'): add('national',k,T['national'][k])
    for k,v in T['national']['vote_method_share'].items(): add('vote_method_share',k,v)
    for g in ('sex','age','early_sex','early_age','region_sample','region_actual','region_early'):
        for k,v in T[g].items():add(g,k,v)
    for sub,values in T['age_sex'].items():
        for k,v in values.items(): add('age_sex',k,v,sub)
    add('election_day','all',T['election_day']['all'])
    for k,v in T['election_day']['sex'].items():add('election_day_sex',k,v)
    tables['turnout_rates'] = rates
    return tables


class Cursor:
    def __init__(self,tables):self.tables=tables;self.rows=None
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def execute(self,sql,params=()):
        match=re.search(r'election_lab\.([a-z_]+)',sql)
        assert match, sql
        table=match.group(1)
        if table=='source_documents' and 'WHERE' in sql:
            self.rows=[(copy.deepcopy(self.tables[table][params[0]]),)]
        elif 'count(*)' in sql:
            self.rows=[(len(self.tables[table]),)]
        else:self.rows=self.tables[table]
    def fetchall(self):return self.rows


class Connection:
    def __init__(self,tables):self.tables=tables
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def cursor(self):return Cursor(self.tables)


def test_postgres_sql_matches_complete_originals(monkeypatch):
    tables=fixture_tables()
    monkeypatch.setattr(postgres_data,'_connect',lambda: Connection(tables))
    monkeypatch.setenv('NEWSROOM_DATA_SOURCE','postgres')
    assert len(tables['turnout_rates'])==106
    assert postgres_data.load_election()==E
    assert postgres_data.load_turnout()==T
    c=TestClient(app)
    data=c.get('/api/real/data')
    assert data.status_code==200, data.text
    assert data.json()['data_backend']=='PostgreSQL'
    assert data.json()['constituency']==E['constituency']
    assert data.json()['turnout']==T
    status=c.get('/api/real/db-status')
    assert status.status_code==200
    assert status.json()['active'] and status.json()['counts']['proportional_area_parties']==9614
    q=c.get('/api/real/ask',params={'q':'서울특별시 종로구 후보 득표는?'}).json()
    assert '44,713표' in q['answer']


def test_sql_values_drive_the_ui_not_local_json(monkeypatch):
    tables=fixture_tables()
    # A database-only change should appear in the UI, while total stays consistent.
    old = tables['district_candidates']
    a=next(i for i,r in enumerate(old) if r[0]=='C001' and r[1]=='곽상언')
    b=next(i for i,r in enumerate(old) if r[0]=='C001' and r[1]=='최재형')
    old[a]=(old[a][0],old[a][1],old[a][2],old[a][3]+1,old[a][4])
    old[b]=(old[b][0],old[b][1],old[b][2],old[b][3]-1,old[b][4])
    monkeypatch.setattr(postgres_data,'_connect',lambda: Connection(tables))
    monkeypatch.setenv('NEWSROOM_DATA_SOURCE','postgres')
    district=next(d for d in vote_data()['constituency']['districts'] if d['id']=='C001')
    assert district['winner']['votes']==44714
    assert district['winner']['votes']!=E['constituency']['districts'][0]['winner']['votes']


def test_postgres_failure_is_not_silently_replaced_by_json(monkeypatch):
    monkeypatch.setenv('NEWSROOM_DATA_SOURCE','postgres')
    def bad():raise HTTPException(503,'DB 서버 연결 실패')
    monkeypatch.setattr(postgres_data,'_connect',bad)
    resp=TestClient(app).get('/api/real/data')
    assert resp.status_code==503
    assert 'DB 서버 연결 실패' in resp.text


def test_local_mode_preserved(monkeypatch):
    monkeypatch.delenv('NEWSROOM_DATA_SOURCE',raising=False)
    assert vote_data()==E
    assert turnout()==T
    assert TestClient(app).get('/api/real/db-status').json()['active'] is False
