"""사용자 제공 3차 V5를 기준으로 한 화면 배치 전용 회귀 검사.

지도 원본은 네트워크에서 받지 않고 검증한다. 원래 기능은 절대 대체하지 않는다.
"""
from pathlib import Path
from unittest.mock import patch

from newsroom.real_data_api import _local_vote_data, _local_turnout
from newsroom_district_explorer2024 import district_explorer


def test_user_approved_three_top_two_bottom_layout():
    data, turnout = _local_vote_data(), _local_turnout()
    with patch('newsroom_district_explorer2024.load_geography', side_effect=OSError('offline test')):
        output = district_explorer(data, turnout, region='서울특별시', district='C004')
    assert output.count('class="explore-grid"') == 1
    assert output.count('class="explore-bottom-grid"') == 1
    assert output.index('class="explore-side explore-national"') < output.index('class="explore-map explore-center"')
    assert output.index('class="explore-map explore-center"') < output.index('class="explore-result"')
    assert output.index('class="explore-result"') < output.index('class="explore-bottom-grid"')
    assert output.index('class="explore-bottom-grid"') < output.index('class="explore-side explore-province-chooser"')
    assert output.index('class="explore-bottom-grid"') < output.index('class="explore-side explore-list"')
    assert '← 이전 단계로' in output and '⌂ 전국 지도 보기' in output
    assert '권영세' in output and '68.91%' in output


def test_standalone_preview_has_same_layout():
    p = Path(__file__).resolve().parents[1] / 'V5_3차_브라우저_미리보기.html'
    html = p.read_text(encoding='utf-8')
    assert 'class="grid-bottom"' in html
    assert 'class="card national-card"' in html
    assert 'class="card selected-card"' in html
    assert 'class="card detail"' in html
    assert 'data-act="back"' in html
    assert '사진·영상 자료' in html
