from pathlib import Path
from fastapi.testclient import TestClient
from server import app, official_store, load_local_election_sample, state
from official_results import analyze, parse_csv, DataError, NON_CANDIDATES

SOURCE='https://www.data.go.kr/data/15025527/fileData.do'


def test_v06_sample_loaded_on_start():
    ds=load_local_election_sample()
    assert ds['mode']=='SYNTHETIC_SAMPLE_NOT_OFFICIAL'
    assert ds['verified'] is False and ds['source_url']=='LOCAL_SYNTHETIC_DEMO'
    assert ds['region_count']==17 and ds['district_count']==68
    assert ds['rows']==612 and ds['summary_rows_excluded']==408
    assert len(state['history'])>=1  # prior tests may reset the mutable simulation state


def test_v06_all_methods_render_rows_with_values():
    ds=load_local_election_sample()
    methods=['region_votes','district_votes','candidate_share','lead_margin','candidate_count',
         'vote_distribution','region_district_count','region_avg_votes','candidate_vote_distribution',
         'margin_distribution','close_races','district_leader_share']
    for method in methods:
        kwargs={'region':'서울특별시','district':'교육용 제01선거구'} if method=='candidate_share' else {}
        result=analyze(ds,method,**kwargs)
        assert result['rows'] and any(r['value'] is not None for r in result['rows']),method
        assert result['verified'] is False
    assert sum(x['value'] for x in analyze(ds,'region_district_count')['rows'])==68


def test_v06_candidate_counts_skip_pseudo_candidate_rows():
    raw=('시도명,선거구명,법정읍면동명,투표구명,후보자,득표수\n'
         '서울,갑,A,1투,가후보,50\n'
         '서울,갑,A,1투,나후보,60\n'
         '서울,갑,A,1투,선거인수,150\n'
         '서울,갑,A,1투,투표수,130\n'
         '서울,갑,A,1투,무효투표수,20\n'
         '서울,갑,A,1투,기권자수,20\n').encode('utf-8')
    ds=parse_csv(raw,source_url=SOURCE)
    assert ds['rows']==2
    assert ds['summary_rows_excluded']==4
    assert analyze(ds,'district_votes')['rows'][0]['value']==110
    assert analyze(ds,'candidate_count')['rows'][0]['value']==2


def test_v06_demo_restore_api_and_actual_upload_replace():
    with TestClient(app) as client:
        d=client.post('/api/official/load-demo').json()
        assert d['loaded'] and d['is_demo']
        assert client.get('/api/official/analyze',params={'method':'margin_distribution'}).status_code==200
        actual=('시도명,선거구명,법정읍면동명,투표구명,후보자,득표수\n'
                '서울,테스트구,A,1투,테스트 후보1,12\n'
                '서울,테스트구,A,1투,테스트 후보2,10\n')
        out=client.post('/api/official/import',params={'source_url':SOURCE},content=actual.encode()).json()
        assert out['loaded'] and not out['is_demo']
        assert out['region_count']==1 and out['district_count']==1
        assert client.get('/api/official/analyze',params={'method':'district_leader_share'}).status_code==200
        d2=client.post('/api/official/load-demo').json()
        assert d2['is_demo'] and d2['region_count']==17


def test_v06_frontend_required_elements_and_preservation():
    with TestClient(app) as client:
        html=client.get('/').text
        assert 'id="ofDemo"' in html and 'id="ofMethodGuide"' in html
        assert 'data-view="district"' in html
        assert 'data-view="articles"' in html
        assert 'data-view="training"' in html
        assert 'data-view="media"' in html
        assert 'data-view="analytics"' in html
        js=client.get('/static/official.js').text
        assert 'load-demo' in js and 'GUIDES' in js
        csv=Path(__file__).resolve().parents[1]/'samples'/'SIMULATION_ONLY_nationwide_17regions_68districts.csv'
        assert csv.exists() and csv.stat().st_size>30000
