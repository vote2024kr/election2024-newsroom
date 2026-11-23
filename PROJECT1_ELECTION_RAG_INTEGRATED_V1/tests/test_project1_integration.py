"""End-to-end ASGI tests for classroom integration; no official election results involved."""
from pathlib import Path
import sys
import sqlite3
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from project1_app import app
import project1_app


def test_integrated_pages_assets_and_status():
    with TestClient(app) as c:
        for path in ('/','/project1','/project1/static/project1.js','/project1/static/project1.css',
                     '/workbench/','/workbench/static/app.js','/workbench/static/style.css',
                     '/api/project1/status','/api/analytics/methods','/workbench/api/catalog'):
            r=c.get(path)
            assert r.status_code==200, (path,r.text[:200])
        html=c.get('/').text
        assert 'ELECTION CONTROL CENTER' in html
        assert '/project1' in html
        workbench=c.get('/workbench/').text
        assert '/workbench/static/app.js' in workbench
        assert '/workbench/static/style.css' in workbench
        js=c.get('/workbench/static/app.js').text
        assert "api('/workbench/api/" in js
        assert "api('/api/" not in js
        assert 'datasetFromNewsroom' in js
        status=c.get('/api/project1/status').json()
        assert status['official_live_feed']=='NOT_IMPLEMENTED'
        assert status['langchain_vector_rag']=='NOT_IMPLEMENTED'
        assert status['news_video']=='DEFERRED_NO_VIDEO_OR_NEW_CG'


def test_websocket_and_step_change():
    with TestClient(app) as c:
        c.post('/api/control',json={'action':'pause'})
        with c.websocket_connect('/ws') as w:
            initial=w.receive_json()
            assert initial['type']=='snapshot'
            assert initial['data']['mode']=='SIMULATION_ONLY'
            old=initial['data']['step']
            r=c.post('/api/control',json={'action':'tick'})
            assert r.status_code==200
            fresh=w.receive_json()
            assert fresh['data']['step']==old+1
            assert fresh['data']['national']['counted']>=initial['data']['national']['counted']


def test_valid_drill_and_manual_review():
    with TestClient(app) as c:
        c.post('/api/control',json={'action':'pause'})
        d=c.post('/api/project1/drill',json={'scenario':'valid'}).json()
        assert d['validation']['passed'] is True
        assert d['status']=='draft'
        r=c.post('/api/project1/approve',json={'article_id':d['article_id'],
          'editor':'프로젝트1 검수자','reason':'가상 원본 수치와 근거 ID를 비교했습니다'})
        assert r.status_code==200, r.text
        assert r.json()['status']=='approved_training_only'
        events=c.get('/api/project1/audit').json()['events']
        assert any(e['article_id']==d['article_id'] and e['event_type']=='APPROVED_LOCAL_CLASSROOM' for e in events)
        assert any(e['article_id']==d['article_id'] and e['event_type']=='DRILL_CREATED' for e in events)


def test_all_bad_drills_block_approval():
    with TestClient(app) as c:
        c.post('/api/control',json={'action':'pause'})
        for scenario in ('wrong_votes','wrong_region','missing_id'):
            d=c.post('/api/project1/drill',json={'scenario':scenario})
            assert d.status_code==200
            j=d.json();assert not j['validation']['passed'], scenario
            review=c.post('/api/project1/approve',json={'article_id':j['article_id'],
                'editor':'프로젝트1 검수자','reason':'형식 검토 후 시험 승인 요청'})
            assert review.status_code==409, (scenario,review.text)


def test_new_count_step_blocks_old_article():
    with TestClient(app) as c:
        c.post('/api/control',json={'action':'pause'})
        d=c.post('/api/project1/drill',json={'scenario':'valid'}).json()
        c.post('/api/control',json={'action':'tick'})
        review=c.post('/api/project1/approve',json={'article_id':d['article_id'],
            'editor':'프로젝트1 검수자','reason':'단계 변경 이후 승인 시험'})
        assert review.status_code==409
        assert '개표 단계' in review.text


def test_import_final_demo_to_workbench_and_run_analysis():
    with TestClient(app) as c:
        demo=c.post('/api/official/load-demo')
        assert demo.status_code==200
        assert demo.json()['mode']=='SYNTHETIC_SAMPLE_NOT_OFFICIAL'
        x=c.post('/api/project1/transfer-final-result')
        assert x.status_code==200, x.text
        j=x.json();assert not j['verified']
        assert j['mode']=='SYNTHETIC_SAMPLE_NOT_OFFICIAL'
        assert j['rows']>100
        meta=c.get('/workbench/api/datasets/'+j['dataset_id'])
        assert meta.status_code==200
        assert meta.json()['kind']=='election'
        assert meta.json()['source'].startswith('교육용')
        # The second statistics app actually calculates a graphable group summary.
        r=c.post('/workbench/api/analyze',json={'dataset_id':j['dataset_id'],'method':'group_summary',
            'options':{'group':'region','x':'votes','aggregation':'sum'},'filters':[], 'missing':'drop'})
        assert r.status_code==200,r.text[:400]
        assert r.json()['filtered_rows']>100
        assert r.json()['source']['verified'] is False


def test_audit_sqlite_persists_records():
    path=ROOT/'data'/'project1_events.sqlite3'
    with sqlite3.connect(path) as conn:
        count=conn.execute('select count(*) from event').fetchone()[0]
        assert count>=1


def test_original_newsroom_analytics_renderable_data():
    with TestClient(app) as c:
        r=c.get('/api/analytics',params={'method':'vote_share','scope':'national'})
        assert r.status_code==200
        j=r.json(); assert len(j['rows'])>0
        assert j['chart'] is not None
        assert len(j['columns'])>0


def test_local_sparse_rag_search_and_id():
    with TestClient(app) as c:
        a=c.get('/api/project1/rag/search',params={'question':'사람 승인 근거 ID 검증'})
        assert a.status_code==200
        out=a.json()
        assert out['mode']=='offline_tfidf_sparse_vector'
        assert out['count']>0
        assert out['results'][0]['id'].startswith('DEMO-')
        assert out['results'][0]['externally_verified'] is False
        z=c.get('/api/project1/rag/search',params={'question':'a'})
        assert z.status_code==400


def test_project1_curated_election_methods_and_original_17_preserved():
    with TestClient(app) as c:
        item=c.get('/api/project1/election/methods')
        assert item.status_code==200
        method_ids={x['id'] for x in item.json()['methods']}
        assert len(method_ids)==10
        assert {'live_increment_trend','live_candidate_trend','final_candidate_share','final_close_races'}.issubset(method_ids)
        assert not any('pca' in m or 'regression' in m or 'bootstrap' in m for m in method_ids)
        assert len(c.get('/workbench/api/catalog').json()['methods'])==17
        page=c.get('/project1').text
        assert 'analysisMethod' in page and 'analysisRegion' in page
        assert c.get('/project1/static/election_stats.js').status_code==200
        assert c.get('/project1/static/election_stats.css').status_code==200


def test_curated_live_uses_only_simulated_stage_history():
    with TestClient(app) as c:
        c.post('/api/control',json={'action':'pause'})
        c.post('/api/control',json={'action':'tick'})
        for method in ('live_vote_share','live_lead_margin','live_candidate_trend','live_increment_trend'):
            r=c.get('/api/project1/election/analyze',params={'method':method})
            assert r.status_code==200,(method,r.text)
            data=r.json()
            assert data['source_mode']=='SIMULATION_ONLY'
            assert data['verified'] is False
            assert data['result']['rows']
        events=c.get('/api/project1/audit').json()['events']
        assert any(e['event_type']=='ELECTION_STAT_ANALYSIS' for e in events)


def test_curated_final_results_never_combine_candidate_denominators():
    with TestClient(app) as c:
        demo=c.post('/api/official/load-demo').json()
        assert demo['is_demo']
        r=c.get('/api/project1/election/analyze',params={'method':'final_candidate_share'})
        assert r.status_code==422
        assert '개별 선거구' in r.text or '선거구' in r.text
        r=c.get('/api/project1/election/analyze',params={'method':'final_candidate_share','region':demo['districts'][0]['region'],'district':demo['districts'][0]['district']})
        assert r.status_code==200,r.text
        data=r.json()
        assert data['source_mode']=='SYNTHETIC_SAMPLE_NOT_OFFICIAL'
        assert data['verified'] is False
        assert abs(sum(item['value'] for item in data['result']['rows'])-100)<0.01
        for method in ('final_district_votes','final_lead_margin','final_close_races','final_region_votes','final_vote_distribution'):
            result=c.get('/api/project1/election/analyze',params={'method':method})
            assert result.status_code==200,(method,result.text[:300])
            assert result.json()['source_mode']=='SYNTHETIC_SAMPLE_NOT_OFFICIAL'
        assert c.get('/api/project1/election/analyze',params={'method':'final_candidate_share','district':demo['districts'][0]['district']}).status_code==422


def test_curated_election_rejects_nonapproved_and_mixed_scope():
    with TestClient(app) as c:
        assert c.get('/api/project1/election/analyze',params={'method':'regression'}).status_code==422
        assert c.get('/api/project1/election/analyze',params={'method':'live_vote_share','region':'서울'}).status_code==422
        assert c.get('/api/project1/election/analyze',params={'method':'final_region_votes','limit':100}).status_code==422


def test_live_broadcast_studio_reuses_existing_snapshot_without_false_official_label():
    with TestClient(app) as c:
        html=c.get('/project1').text
        assert 'broadcastHeadline' in html and 'ON AIR' in html
        assert '교육용 모의 개표 방송' in html
        assert '/project1/static/broadcast_live.js' in html
        assert '/project1/static/broadcast_live.css' in html
        js=c.get('/project1/static/broadcast_live.js')
        css=c.get('/project1/static/broadcast_live.css')
        assert js.status_code==css.status_code==200
        assert "project1:snapshot" in js.text
        assert "s.mode!=='SIMULATION_ONLY'" in js.text
        assert '실제 선거 결과' in js.text
        original=c.get('/project1/static/project1.js').text
        assert "new CustomEvent('project1:snapshot'" in original
        snap=c.get('/api/snapshot').json()
        assert snap['mode']=='SIMULATION_ONLY'
        assert len(snap['national']['votes'])==3
