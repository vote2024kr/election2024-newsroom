from pathlib import Path
from fastapi.testclient import TestClient
from app.server import app, DATASETS
import pytest

C=TestClient(app)

def test_initial_ui_and_method_catalog():
    r=C.get('/');assert r.status_code==200
    assert '통합 통계' in r.text
    r=C.get('/api/catalog');assert r.status_code==200
    assert len(r.json()['methods'])==17

def test_samples_and_analysis():
    r=C.get('/api/samples');assert len(r.json()['samples'])==4
    d=C.post('/api/samples/sample_election.csv/load').json()
    r=C.post('/api/analyze',json={'dataset_id':d['id'],'method':'election_votes'})
    assert r.status_code==200
    assert r.json()['source']['verified'] is False
    assert r.json()['chart']['labels']
    h=C.get(f'/api/datasets/{d["id"]}/history').json()['history']
    assert len(h)==1

def test_kind_update_and_recommendation():
    d=C.post('/api/samples/sample_air.csv/load').json()
    r=C.patch(f'/api/datasets/{d["id"]}/kind',json={'kind':'election'})
    assert r.status_code==200
    assert r.json()['kind']=='election'

def test_upload_user_and_guard():
    content='지역,수치\n서울,10\n부산,20\n'.encode('utf-8')
    r=C.post('/api/datasets/upload',files={'file':('test.csv',content,'text/csv')},data={'kind':'general','source':'로컬 테스트'})
    assert r.status_code==200
    d=r.json();assert d['origin']=='upload'
    assert d['profile']['rows']==2
    out=C.post('/api/analyze',json={'dataset_id':d['id'],'method':'summary','options':{'x':'수치'}})
    assert out.status_code==200
    assert out.json()['summary']['평균']==15
    assert C.post('/api/analyze',json={'dataset_id':d['id'],'method':'summary','options':{'x':'abc'}}).status_code==422

def test_bad_file_and_traversal():
    r=C.post('/api/datasets/upload',files={'file':('bad.csv',b'a,a\n1,2','text/csv')})
    assert r.status_code==422
    r=C.post('/api/samples/..%5Cpassword/load');assert r.status_code in (400,404)

def test_no_method_on_missing_dataset():
    r=C.post('/api/analyze',json={'dataset_id':'not-found','method':'summary'})
    assert r.status_code==404

def test_transform_csv_export_and_formula_escape():
    content='name,x,y\n=HYPERLINK(1),20,2\nnormal,10,2\n'.encode('utf-8')
    meta=C.post('/api/datasets/upload',files={'file':('data.csv',content,'text/csv')}).json()
    r=C.post('/api/transform/export',json={'dataset_id':meta['id'],'derived':'ratio','x':'x','y':'y','new_column':'unit_value'})
    assert r.status_code==200
    assert r.headers['x-processed-rows']=='2'
    assert 'unit_value' in r.text
    assert "'=HYPERLINK(1)" in r.text


def test_transform_bad_column_blocked():
    d=C.post('/api/samples/sample_air.csv/load').json()
    r=C.post('/api/transform/export',json={'dataset_id':d['id'],'derived':'difference','x':'unknown','y':'pm25'})
    assert r.status_code==422
