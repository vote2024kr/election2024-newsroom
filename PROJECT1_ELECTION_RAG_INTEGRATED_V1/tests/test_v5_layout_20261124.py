"""Regression checks for 2024 national summary and district explorer."""
from newsroom_election_layout_v2 import cities_for, geometry_svg, nationwide_overview, district_explorer
from newsroom.real_data_api import _local_vote_data, _local_turnout

def test_municipality_names():
    assert cities_for('성남시분당구갑') == ['성남시']
    assert cities_for('동두천시양주시연천군갑') == ['동두천시','양주시','연천군']
    assert cities_for('강남구갑') == ['강남구']

def test_real_map_ids_and_254_seats():
    d=_local_vote_data()
    assert len(d['constituency']['districts']) == 254
    assert geometry_svg(d).count('<path ') == 254
    assert geometry_svg(d,region='서울특별시').count('<path ') == 48

def test_final_page_static_summary():
    d,t=_local_vote_data(),_local_turnout()
    html=nationwide_overview(d,t)
    assert '지역구 · 254석' in html and '비례대표 · 46석' in html
    assert '전체 국회 · 300석' in html
    assert '/safe2024?page=district&region=' not in html

def test_district_details_and_back_navigation():
    d,t=_local_vote_data(),_local_turnout()
    rec=next(x for x in d['constituency']['districts'] if x['region']=='서울특별시' and x['district']=='용산구')
    html=district_explorer(d,t,region='서울특별시',district=rec['id'])
    assert rec['winner']['name'] in html
    assert f"{rec['ballots']/rec['registered']*100:.2f}%" in html
    assert '이전 단계로' in html and '전국 지도 보기' in html
    assert 'explore-top' in html and 'explore-bottom' in html

def test_route_integration_with_postgres_mock():
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from project1_app import app
    d,t=_local_vote_data(),_local_turnout()
    with patch('newsroom_safe2024.get_data',return_value=(d,t)):
        client=TestClient(app)
        a=client.get('/safe2024?page=final')
        b=client.get('/safe2024?page=district&region=서울특별시')
        c=client.get('/safe2024/final-embed')
    assert a.status_code==b.status_code==c.status_code==200
    assert '전국 254개 지역구 최종 당선 지도' in a.text
    assert '전국 17개 시·도 선택' in b.text
    assert '전체 국회 · 300석' in c.text
