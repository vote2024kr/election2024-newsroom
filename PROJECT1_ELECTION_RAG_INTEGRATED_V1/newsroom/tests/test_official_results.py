import sys
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from official_results import parse_csv, analyze, replay, DataError
from server import app, official_store
SOURCE='https://www.data.go.kr/data/15025527/fileData.do'
CSV='''시도명,선거구명,법정읍면동명,투표구명,후보자,득표수
서울,갑선거구,가동,1투표구,가후보,"1,200"
서울,갑선거구,가동,1투표구,나후보,800
서울,갑선거구,나동,2투표구,가후보,300
서울,갑선거구,나동,2투표구,나후보,700
서울,을선거구,다동,1투표구,다후보,100
서울,을선거구,다동,1투표구,라후보,200
부산,병선거구,라동,1투표구,마후보,700
부산,병선거구,라동,1투표구,바후보,300
전국,계,,,,10000
'''

@pytest.fixture
def ds():return parse_csv(CSV.encode('utf-8-sig'),source_url=SOURCE,election_name='TEST_ONLY')

def test_csv_metadata_provenance(ds):
    assert ds['verified'] is False
    assert ds['summary_rows_excluded']==1
    assert ds['rows']==8
    assert ds['region_count']==2 and ds['district_count']==3
    assert ds['sha256']

def test_region_aggregation(ds):
    out=analyze(ds,'region_votes')
    assert {x['label']:x['value'] for x in out['rows']}=={'서울':3300,'부산':1000}
    assert out['total_candidate_votes']==4300

def test_no_national_candidate_share(ds):
    with pytest.raises(DataError,match='개별 선거구'):
        analyze(ds,'candidate_share')

def test_candidate_share_in_district(ds):
    out=analyze(ds,'candidate_share',region='서울',district='갑선거구')
    assert [(r['label'],r['votes']) for r in out['rows']]==[('가후보',1500),('나후보',1500)]
    assert sum(x['value'] for x in out['rows'])==100


def test_lead_margin(ds):
    out=analyze(ds,'lead_margin',region='서울')
    assert next(x for x in out['rows'] if '갑선거구' in x['label'])['value']==0
    assert next(x for x in out['rows'] if '을선거구' in x['label'])['value']==pytest.approx(100/300*100,abs=.002)

def test_excludes_summary_rows(ds):
    assert all('전국'!=x['region'] for x in ds['votes'])


def test_duplicate_rejected():
    txt=CSV+CSV.splitlines()[1]+'\n'
    with pytest.raises(DataError,match='중복'):parse_csv(txt.encode(),source_url=SOURCE)


def test_invalid_vote_rejected():
    with pytest.raises(DataError,match='정수'):parse_csv(CSV.replace('800','7.5').encode(),source_url=SOURCE)


def test_unofficial_source_rejected():
    with pytest.raises(DataError,match='공식'):parse_csv(CSV.encode(),source_url='https://attacker-data.go.kr.evil.test')


def test_bad_header_rejected():
    with pytest.raises(DataError,match='필수 열'):parse_csv('a,b\n1,2'.encode(),source_url=SOURCE)


def test_cp949_supported():
    ds=parse_csv(CSV.encode('cp949'),source_url=SOURCE)
    assert ds['encoding']=='cp949'


def test_replay_increments_finish_exactly(ds):
    out=replay(ds,'서울','갑선거구',20)
    assert out['actual_counting_timestamps'] is False
    assert out['mode']=='SYNTHETIC_REPLAY_OF_FINAL_RESULTS'
    for s in out['series']:
        assert s['points'][0]==0 and s['points'][-1]==s['final_votes']
        assert all(a<=b for a,b in zip(s['points'],s['points'][1:]))
    assert replay(ds,'서울','갑선거구',20)==out


def test_district_replay_without_selection_rejected(ds):
    with pytest.raises(DataError):replay(ds,'서울','')


def test_api_import_and_analyze():
    official_store['dataset']=None
    with TestClient(app) as c:
        assert c.get('/api/official/status').json()['loaded'] is False
        resp=c.post('/api/official/import',params={'source_url':SOURCE,'election_name':'교육 검증용'},content=CSV.encode())
        assert resp.status_code==200,resp.text
        body=resp.json();assert body['verified'] is False
        stat=c.get('/api/official/analyze',params={'method':'region_votes'});
        assert stat.status_code==200
        assert stat.json()['total_candidate_votes']==4300
        resp=c.get('/api/official/replay',params={'region':'서울','district':'갑선거구'});
        assert resp.status_code==200
        assert resp.json()['series'][0]['points'][-1]==1500
    official_store['dataset']=None


def test_api_responds_bad_upload():
    with TestClient(app) as c:
        resp=c.post('/api/official/import',params={'source_url':SOURCE},content=b'bad')
        assert resp.status_code==422
        assert c.get('/api/official/status').status_code==200


def test_existing_web_page_kept():
    with TestClient(app) as c:
        html=c.get('/').text
        assert 'view-dashboard' in html
        assert 'view-articles' in html
        assert 'view-official' in html
        assert 'view-analytics' in html
        assert c.get('/api/snapshot').status_code==200
