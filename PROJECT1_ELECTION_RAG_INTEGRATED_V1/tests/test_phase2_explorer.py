"""2차 개편: 전국 요약과 지역 탐색을 별개 화면으로 보존하는 회귀 테스트.

운영 PostgreSQL 연결이나 GitHub 변경 없이 검토용 로컬 사본으로 수행.
"""
from fastapi.testclient import TestClient
from newsroom.real_data_api import _local_vote_data, _local_turnout
from newsroom_district_explorer2024 import municipalities


def test_constituency_turnout_is_derived_from_verified_counts():
    rows = _local_vote_data()['constituency']['districts']
    assert len(rows) == 254
    assert all(d['registered'] > 0 and d['ballots'] == d['valid'] + d['invalid'] for d in rows)
    total = sum(d['ballots'] for d in rows) / sum(d['registered'] for d in rows) * 100
    assert abs(total - 67.0) < 0.03
    x = next(d for d in rows if d['id'] == 'C119')
    assert x['region'] == '경기도' and x['district'] == '수원시정'
    assert f'{x["ballots"]/x["registered"]*100:.2f}%' == '70.66%'


def test_municipality_index_keeps_combined_constituencies():
    assert municipalities('동두천시양주시연천군갑') == ['동두천시', '양주시', '연천군']
    assert municipalities('성남시분당구갑') == ['성남시']
    assert municipalities('중구성동구갑') == ['중구','성동구']


def test_final_result_is_an_overview_not_a_drilldown():
    from review_preview2024 import app
    body = TestClient(app).get('/safe2024?page=final').text
    assert '전국 최종 결과' in body
    assert '정당별 최종 의석수' in body
    assert '지역구 당선 의석' in body and '비례대표 배분 의석' in body
    assert '국회 전체 의석' in body
    assert '시·도·시·군을 확대' in body
    assert '시·군 및 지역구 목록' not in body


def test_explorer_region_city_district_and_individual_turnout():
    from review_preview2024 import app
    client = TestClient(app)
    nationwide = client.get('/safe2024?page=district')
    assert nationwide.status_code == 200 and '시·도 선택' in nationwide.text
    region = client.get('/safe2024?page=district&region=경기도')
    assert '수원시' in region.text and '부천시' in region.text
    assert '66.7%' in region.text
    suwon = client.get('/safe2024?page=district&region=경기도&area=수원시')
    assert '수원시정' in suwon.text
    assert '검색 결과 5개 지역구' in suwon.text
    detail = client.get('/safe2024?page=district&region=경기도&area=수원시&district=C119')
    assert detail.status_code == 200
    assert '김준혁' in detail.text and '이수정' in detail.text
    assert '70.66%' in detail.text and '2,377표' in detail.text
    assert '선관위 지역구 개표 원자료에서 계산' in detail.text


def test_other_v5_menus_unchanged_and_available():
    from review_preview2024 import app
    client = TestClient(app)
    for path in ['/safe2024','/safe2024?page=turnout','/safe2024?page=pr',
                 '/safe2024?page=stats','/safe2024?page=articles']:
        response = client.get(path)
        assert response.status_code == 200 and 'DB 조회 확인 필요' not in response.text
