"""Additional functional regression checks for the team handoff (education demo only)."""
from __future__ import annotations

import re
from pathlib import Path
from fastapi.testclient import TestClient
from project1_app import app

ROOT = Path(__file__).resolve().parents[1]


def test_step_statistics_evidence_article_block_approve_audit_flow():
    with TestClient(app) as c:
        c.post('/api/control',json={'action':'pause'})
        before=c.get('/api/snapshot').json()
        assert before['mode']=='SIMULATION_ONLY'
        with c.websocket_connect('/ws') as ws:
            first=ws.receive_json()
            assert first['type']=='snapshot'
            assert first['data']['mode']=='SIMULATION_ONLY'
            tick=c.post('/api/control',json={'action':'tick'})
            assert tick.status_code==200
            received=ws.receive_json()
            assert received['data']['step']==first['data']['step']+1
        analysis=c.get('/api/project1/election/analyze',params={'method':'live_candidate_trend'})
        assert analysis.status_code==200
        assert analysis.json()['verified'] is False
        assert analysis.json()['source_mode']=='SIMULATION_ONLY'
        doc=c.get('/api/project1/rag/search',params={'question':'사람 승인 근거 ID 검증'})
        assert doc.status_code==200 and doc.json()['count']>0
        bad=c.post('/api/project1/drill',json={'scenario':'wrong_region'}).json()
        assert bad['validation']['passed'] is False
        rejected=c.post('/api/project1/approve',json={'article_id':bad['article_id'],
            'editor':'테스트 검수자','reason':'변조된 지역명 승인 거부 시험'})
        assert rejected.status_code==409
        good=c.post('/api/project1/drill',json={'scenario':'valid'}).json()
        assert good['validation']['passed']
        approved=c.post('/api/project1/approve',json={'article_id':good['article_id'],
            'editor':'테스트 검수자','reason':'모의 원본 수치와 근거 ID 대조 완료'})
        assert approved.status_code==200
        assert approved.json()['status']=='approved_training_only'
        assert '실제 기사 게시 불가' in approved.json()['notice']
        events=c.get('/api/project1/audit').json()['events']
        assert any(x['event_type']=='APPROVAL_BLOCKED' and x['article_id']==bad['article_id'] for x in events)
        assert any(x['event_type']=='APPROVED_LOCAL_CLASSROOM' and x['article_id']==good['article_id'] for x in events)


def test_uploaded_final_data_separated_from_live_simulation_and_not_certified():
    raw='시도명,선거구명,후보자,득표수\n서울,가상-1,A,60\n서울,가상-1,B,40\n부산,가상-2,A,10\n부산,가상-2,B,90\n'.encode('utf-8-sig')
    with TestClient(app) as c:
        try:
            previous=c.get('/api/snapshot').json()
            r=c.post('/api/official/import',params={'source_url':'https://data.nec.go.kr/demo',
                'election_name':'테스트용 사용자 입력'},content=raw,headers={'Content-Type':'text/csv'})
            assert r.status_code==200,r.text
            assert r.json()['mode']=='USER_UPLOADED_FINAL_RESULT'
            assert not r.json()['verified']
            district=c.get('/api/project1/election/analyze',params={'method':'final_candidate_share',
                'region':'서울','district':'가상-1'})
            assert district.status_code==200,district.text
            rows=district.json()['result']['rows']
            assert {x['label']:x['value'] for x in rows}=={'A':60.0,'B':40.0}
            assert '독립 대조' in district.json()['source_label']
            assert c.get('/api/project1/election/analyze',params={'method':'final_candidate_share'}).status_code==422
            transfer=c.post('/api/project1/transfer-final-result')
            assert transfer.status_code==200
            dataset=transfer.json()
            assert not dataset['verified']
            response=c.post('/workbench/api/analyze',json={'dataset_id':dataset['dataset_id'],
                'method':'group_summary','options':{'group':'region','x':'votes','aggregation':'sum'},
                'filters':[],'missing':'drop'})
            assert response.status_code==200,response.text
            assert response.json()['source']['verified'] is False
            latest=c.get('/api/snapshot').json()
            assert latest['mode']=='SIMULATION_ONLY'
            assert latest['seed']==previous['seed']
        finally:
            c.post('/api/official/load-demo')


def test_display_contract_all_new_assets_and_required_elements_exist():
    html=(ROOT/'project1_ui'/'index.html').read_text(encoding='utf-8')
    ids=set(re.findall(r'\bid="([A-Za-z0-9_-]+)"',html))
    for script_name in ('election_stats.js','broadcast_live.js'):
        js=(ROOT/'project1_ui'/script_name).read_text(encoding='utf-8')
        referenced=set(re.findall(r"\$\('([A-Za-z0-9_-]+)'\)",js))
        assert referenced.issubset(ids),(script_name,referenced-ids)
    with TestClient(app) as c:
        for filename in ('election_stats.js','broadcast_live.js','election_stats.css','broadcast_live.css'):
            assert c.get('/project1/static/'+filename).status_code==200
        assert '교육용 모의' in html
        assert 'ON AIR' in html
        assert 'browser' not in c.get('/api/project1/status').json()['official_live_feed'].lower()
