"""V1.2 user-provided 2024 original data integration regression checks."""
from fastapi.testclient import TestClient
from project1_app import app
from newsroom.real_data_api import vote_data, turnout


def test_real_originals_and_seats():
    data=vote_data()
    con=data['constituency']; pr=data['proportional']
    assert con['total_seats']==254
    assert len(con['districts'])==254
    assert len(con['regions'])==17
    assert con['seats_by_party']=={'더불어민주당':161,'국민의힘':90,'진보당':1,'새로운미래':1,'개혁신당':1}
    assert len(pr['nation']['parties'])==38
    assert len(pr['areas'])==253
    assert pr['seat_count']==46
    assert sum(pr['seat_allocation'].values())==46
    assert sum(v['votes'] for v in pr['nation']['parties'])==pr['nation']['valid']==28344519
    assert pr['nation']['ballots']==29654450
    assert all(sum(p['votes'] for p in area['parties'])==area['valid'] for area in pr['areas'])


def test_jongno_precise_final_counts():
    data=vote_data()
    district=next(x for x in data['constituency']['districts'] if x['region']=='서울특별시' and x['district']=='종로구')
    assert district['winner']['name']=='곽상언'
    assert district['winner']['votes']==44713
    assert district['margin']==5961
    assert district['candidates'][1]['name']=='최재형'
    assert district['candidates'][1]['votes']==38752
    proportional=next(x for x in data['proportional']['areas'] if x['region']=='서울특별시' and x['area']=='종로구')
    assert proportional['valid']==86035


def test_turnout_sources_are_separate():
    data=turnout()
    assert data['national']['final']==67.0
    assert data['national']['sample']==67.2
    assert data['national']['vote_method_share']['선거일']==52.7
    assert data['election_day']['all']==51.8
    assert data['age_sex']['남성']['20대 후반']==45.6
    assert data['age_sex']['여성']['20대 후반']==58.2


def test_api_and_question_coverage():
    c=TestClient(app)
    health=c.get('/api/real/health').json()
    assert health['ok'] and health['districts']==254 and health['pr_parties']==38
    q=c.get('/api/real/ask',params={'q':'사전투표는 전수조사인가요?'}).json()
    assert '전수조사' in q['answer'] and q['evidence'][0]['source']
    q=c.get('/api/real/ask',params={'q':'비례대표 정당 득표는?'}).json()
    assert '10,395,264' in q['answer'] and '더불어민주연합' in q['answer']
    q=c.get('/api/real/ask',params={'q':'왜 본투표만 표본으로 조사했나요?'}).json()
    assert '구체적 이유는 설명하지 않습니다' in q['answer']
    pdf=c.get('/api/real/turnout-report.pdf')
    assert pdf.status_code==200 and pdf.content[:4]==b'%PDF'
    apphtml=c.get('/').text
    assert 'real_results.js' in apphtml and 'realQaQuestion' in apphtml
    assert c.get('/project1').status_code==200
