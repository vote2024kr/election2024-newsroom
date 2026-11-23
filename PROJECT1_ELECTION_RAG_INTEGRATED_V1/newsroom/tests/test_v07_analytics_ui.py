"""V0.7 regression: analytics UI contract and typed API under each data scope."""
from pathlib import Path
from fastapi.testclient import TestClient
from server import app, state, make_snapshot
from analytics import METHODS
ROOT=Path(__file__).resolve().parents[1]


def test_frontend_bindings_and_chart_renderers_exist():
    html=(ROOT/'static/index.html').read_text(encoding='utf-8')
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    css=(ROOT/'static/style.css').read_text(encoding='utf-8')
    for element in ('statScope','statRegion','statDistrict','statMethod','statWindow','statRefresh',
                    'statChart','statSummary','statTableHead','statTableBody','statRowCount','statExport'):
        assert f'id="{element}"' in html
    for fn in ('refreshStatistics','renderStatisticsChart','renderStatisticsReport',
               'updateStatSelectors','scheduleStatistics'):
        assert f'function {fn}' in js or f'async function {fn}' in js
    assert "if(view==='analytics')" in js
    assert '.stat-controls' in css and '.stat-summary-item' in css and '.stat-bar-item' in css


def test_all_8_simulation_methods_return_graph_and_evidence_rows():
    with TestClient(app) as client:
        client.post('/api/control',json={'action':'reset','seed':20261111})
        client.post('/api/control',json={'action':'tick'})
        client.post('/api/control',json={'action':'tick'})
        for method in METHODS:
            resp=client.get('/api/analytics',params={'method':method,'scope':'national','window':30})
            assert resp.status_code==200,(method,resp.text)
            doc=resp.json()
            assert doc['mode']=='SIMULATION_ONLY'
            assert doc['chart']['kind'] in ('bar','line','scatter')
            assert doc['rows'] and doc['columns']
            assert doc['summary']['district_count']==254
            assert doc['source'].startswith('내장된 난수')


def test_region_and_district_scopes_and_bad_region_guard():
    with TestClient(app) as client:
        client.post('/api/control',json={'action':'reset','seed':20261111})
        client.post('/api/control',json={'action':'tick'})
        client.post('/api/control',json={'action':'tick'})
        for scope,extra in (
            ('region',{'region':'서울'}),
            ('district',{'region':'서울','district_id':'서울-001'}),
        ):
            for method in METHODS:
                result=client.get('/api/analytics',params={'method':method,'scope':scope,**extra})
                assert result.status_code==200,(scope,method,result.text)
                assert result.json()['rows']
        bad=client.get('/api/analytics',params={'method':'vote_share','scope':'district',
                   'region':'부산','district_id':'서울-001'})
        assert bad.status_code==400


def test_export_csv_has_traceable_metadata_and_rows():
    with TestClient(app) as client:
        res=client.get('/api/analytics/export.csv',params={'method':'vote_share','scope':'national'})
        assert res.status_code==200
        text=res.content.decode('utf-8-sig')
        assert 'mode,source,scope,method,updated_at,step' in text
        assert text.count('SIMULATION_ONLY')==3
        assert '모의 후보 A' in text


def test_source_separation_and_no_real_live_feed():
    with TestClient(app) as client:
        a=client.get('/api/analytics').json()
        official=client.get('/api/official/status').json()
        assert a['mode']=='SIMULATION_ONLY'
        assert official['verified'] is False
        assert official['mode'] in ('SYNTHETIC_SAMPLE_NOT_OFFICIAL','USER_UPLOADED_FINAL_RESULT')
        assert a['source']!=official['source_url']


def test_controls_reset_keep_history_consistent():
    with TestClient(app) as client:
        assert client.post('/api/control',json={'action':'reset','seed':20261111}).status_code==200
        report=client.get('/api/analytics',params={'method':'progress_trend'}).json()
        assert report['history_points']==1
        assert len(report['rows'])==1
        assert client.post('/api/control',json={'action':'tick'}).status_code==200
        report2=client.get('/api/analytics',params={'method':'increment_trend'}).json()
        assert report2['history_points']==2
        assert len(report2['rows'])==1
        assert report2['rows'][0]['new_votes']>=0
