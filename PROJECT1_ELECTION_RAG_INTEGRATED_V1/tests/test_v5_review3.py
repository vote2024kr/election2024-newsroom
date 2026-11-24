"""Regression checks for locally isolated V5 review round 3."""
from pathlib import Path
from fastapi.testclient import TestClient
import newsroom_visuals2024 as visuals

ROOT=Path(__file__).resolve().parents[1]

def test_turnout_shading_is_darker_for_higher_actual_rate():
    assert visuals._turnout_color(70.1)=='#123c76'
    assert visuals._turnout_color(62.2)=='#a5dce9'
    assert visuals._turnout_color(69.3)!=visuals._turnout_color(65.0)

def test_media_gallery_has_only_new_verified_cg():
    import review_preview2024
    c=TestClient(review_preview2024.app)
    r=c.get('/safe2024?page=media')
    assert r.status_code==200
    assert r.text.count('class="latest-media-item"')==6
    assert '교육용 관제실 예시' not in r.text
    assert '기존 프로젝트의 화면 검증용 캡처' not in r.text
    assert '실제 선거 데이터' in r.text
    for name in ('v5_r3_final_overview.png','v5_r3_district_detail.png',
                 'v5_r3_turnout_analysis.png','v5_r3_count_analysis.png',
                 'v5_r3_replay_13.png','v5_r3_replay_final.png'):
        resp=c.get('/safe2024/visuals/'+name)
        assert resp.status_code==200 and resp.content[:8]==b"\x89PNG\r\n\x1a\n"
    assert c.get('/safe2024/visuals/control_room_cg.jpg').status_code==404

def test_navigation_and_13h_arrow_retained():
    import review_preview2024
    c=TestClient(review_preview2024.app)
    r=c.get('/safe2024?page=district&region=%EA%B2%BD%EA%B8%B0%EB%8F%84&area=%EC%88%98%EC%9B%90%EC%8B%9C')
    assert r.status_code==200
    assert '이전 단계로' in r.text and '전국 지도 보기' in r.text
    replay=(ROOT/'newsroom_replay2024.py').read_text('utf8')
    assert 'replay-early-arrowhead' in replay
    assert '13시 · 사전투표율 포함됨' in replay

def test_standalone_preview_has_embedded_cg_and_new_tab():
    s=(ROOT/'V5_3차_브라우저_미리보기.html').read_text('utf8')
    assert 'data-page="media"' in s and 'function mediaView()' in s
    assert s.count('data:image/jpeg;base64,')==6
