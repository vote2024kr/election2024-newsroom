import csv
import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from training_pipeline import (
    preview_content, to_csv, draft_jsonl, approved_jsonl,
    parse_local_html, TrainingError,
)
from server import app
BASE=Path(__file__).resolve().parents[1]
CSV=(BASE/'samples'/'crawling_training'/'press_raw_DEMO.csv').read_text(encoding='utf-8-sig')
HTML=(BASE/'samples'/'crawling_training'/'press_sample_DEMO.html').read_text(encoding='utf-8')

def test_sample_counts_and_rejections():
    r=preview_content(CSV,synthetic=True)
    assert r['total']==12 and r['accepted']==10 and r['rejected_count']==2
    assert '중복 본문' in sum((e['reasons'] for e in r['excluded']),[])
    assert any('200~2500' in s for e in r['excluded'] for s in e['reasons'])

def test_fixture_html_matches_csv():
    a=preview_content(CSV,synthetic=True)
    b=preview_content(HTML,'html',synthetic=True)
    assert [x['body_sha256'] for x in a['records']]==[x['body_sha256'] for x in b['records']]

def test_draft_jsonl_alpaca_and_not_reviewed():
    r=preview_content(CSV,synthetic=True)
    lines=draft_jsonl(r['records']).splitlines()
    assert len(lines)==10
    assert set(json.loads(lines[0]))=={'instruction','input','output'}
    assert r['llm_called'] is False
    assert r['source_verified'] is False
    assert all(x['approved'] is False for x in r['records'])

def test_not_enough_provenance_rejects_user_file():
    out=preview_content(CSV,synthetic=False)
    assert out['accepted']==0 and out['rejected_count']==12
    assert any('HTTPS' in reason for x in out['excluded'] for reason in x['reasons'])

def test_csv_robust_parser():
    with pytest.raises(TrainingError,match='필수 열'):preview_content('a,b\n1,2')
    with pytest.raises(TrainingError,match='크기|1MB'):preview_content('x'*1_000_001)
    with pytest.raises(TrainingError):preview_content('bad','pdf')

def test_no_unreviewed_export():
    r=preview_content(CSV,synthetic=True)
    record={**r['records'][0], 'approved':True,'lead':'검수하여 확정한 임시 문장'}
    with pytest.raises(TrainingError,match='검수자'):approved_jsonl([record],'',True)
    with pytest.raises(TrainingError,match='권리'):approved_jsonl([record],'편집자',False)
    with pytest.raises(TrainingError,match='승인'):approved_jsonl([r['records'][0]],'편집자',True)

def test_changed_body_hash_is_blocked():
    r=preview_content(CSV,synthetic=True)
    changed={**r['records'][0],'body':r['records'][0]['body']+' 내용 추가','approved':True,'lead':'확정 리드'}
    with pytest.raises(TrainingError,match='해시'):approved_jsonl([changed],'편집자',True)

def test_reviewed_jsonl():
    r=preview_content(CSV,synthetic=True)
    rec={**r['records'][0],'approved':True,'lead':r['records'][0]['lead_draft']}
    lines=approved_jsonl([rec],'검수자',True).splitlines()
    assert len(lines)==1 and 'output' in json.loads(lines[0])

def test_api_sample_and_export_gate():
    with TestClient(app) as client:
        response=client.get('/api/training/sample')
        assert response.status_code==200,response.text
        d=response.json();assert d['accepted']==10
        assert client.post('/api/training/export-reviewed',json={'reviewer':'검수자','rights_confirmed':False,'records':[]}).status_code==422
        r=client.post('/api/training/export-reviewed',json={'reviewer':'검수자','rights_confirmed':True,
              'records':[{**d['records'][0],'approved':True,'lead':d['records'][0]['lead_draft']}]})
        assert r.status_code==200,r.text
        assert r.json()['count']==1

def test_api_invalid_real_upload():
    with TestClient(app) as client:
        response=client.post('/api/training/preview',json={'kind':'csv','content':CSV})
        assert response.status_code==200 and response.json()['accepted']==0
        assert client.post('/api/training/preview',json={'kind':'html','content':'<title>bad</title>'}).status_code==422

def test_original_views_and_static_preserved():
    with TestClient(app) as client:
        doc=client.get('/').text
        for view in ('dashboard','district','articles','studio','analytics','official','media','training'):
            assert f'id="view-{view}"' in doc
        assert client.get('/api/snapshot').status_code==200
        assert client.get('/static/training/press_sample_DEMO.html').status_code==200
        assert client.get('/static/training.js').status_code==200
        assert client.get('/api/official/status').status_code==200
