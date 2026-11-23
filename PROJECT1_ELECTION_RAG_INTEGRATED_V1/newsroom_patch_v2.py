"""2024 NEC finalized election newsroom add-on.
Non-destructive additive API: original simulator and real-data routes are not modified.
For PDF-based facts this is source-linked rule retrieval, not an LLM/vector RAG.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import re, json
from functools import lru_cache

HERE = Path(__file__).resolve().parent
router = APIRouter(prefix='/api/v2',tags=['2024 verified-source newsroom patch'])
PDF = HERE/'newsroom'/'real_data'/'turnout_report_2024.pdf'
NEC_REPORT = '중앙선거관리위원회 「제22대 국회의원선거 투표율 분석」'
REPORT_URL='/api/v2/report.pdf'
DISTRICT_SOURCE='https://www.data.go.kr/data/15025527/fileData.do'
PR_SOURCE='https://www.data.go.kr/data/15144273/fileData.do'
SEAT_REFERENCE='https://m.go.seoul.co.kr/news/politics/national-assembly-election-2024/2024/04/11/20240411500082'

# The percentages below are transcribed from the attached NEC report; no inference or mock votes.
REAL = {
    'year':2024, 'election':'제22대 국회의원선거',
    'election_date':'2024-04-10','status':'최종 개표 결과 / 실시간 아님',
    'seats':{'total':300,'constituency':254,'proportional':46},
    'party_seats':[
        {'party':'더불어민주당 + 더불어민주연합','total':175,'constituency':161,'proportional':14},
        {'party':'국민의힘 + 국민의미래','total':108,'constituency':90,'proportional':18},
        {'party':'조국혁신당','total':12,'constituency':0,'proportional':12},
        {'party':'개혁신당','total':3,'constituency':1,'proportional':2},
        {'party':'새로운미래','total':1,'constituency':1,'proportional':0},
        {'party':'진보당','total':1,'constituency':1,'proportional':0},
    ],
    'vote_share_of_voters':{'선거일 투표':52.7,'사전투표':46.7,'거소·선상투표':0.3,'재외투표':0.3},
    'total_turnout':67.0,'total_sample_turnout':67.2,
    'sample':{'precincts':1505,'electors':4480811,'share_of_electors':10.1,'population_electors':44251919,'confidence_level':95,'claimed_margin_pp':0.05},
    'day_vote':{'rate':51.8,'denominator':'사전투표·거소·선상투표·재외투표 등 이미 다른 방식으로 투표한 사람을 제외한 표본 투표구 선거인 3,039,100명','sample_electors':3039100,'male':49.2,'female':54.1,'aged_20s':35.6,'aged_70s':75.2},
    'gender_total_sample':{'남성':66.5,'여성':67.9},
    'age_total_sample':{'18세':56.8,'19세':57.7,'20대':52.4,'30대':55.1,'40대':62.6,'50대':71.6,'60대':82.0,'70대':84.7,'80세 이상':60.5},
    'early':{'eligible_electors':44280011,'voters':13849043,'rate':31.3,'male':33.2,'female':29.4,'aged_60s':40.8,'aged_70s':37.5,'aged_50s':35.8,'aged_18':22.9},
    'overseas':{'eligible':147989,'rate':62.8,'absentee_eligible':119897,'absentee_rate':71.1,'overseas_elector_eligible':28092,'overseas_elector_rate':27.4},
    'regional_final_turnout':{'서울':69.3,'부산':67.5,'대구':64.0,'인천':65.3,'광주':68.2,'대전':66.3,'울산':66.9,'세종':70.1,'경기':66.7,'강원':66.6,'충북':65.2,'충남':65.0,'전북':67.4,'전남':69.0,'경북':65.1,'경남':67.6,'제주':62.2},
    'regional_day_sample_turnout':{'서울':54.1,'부산':53.4,'대구':51.7,'인천':51.9,'광주':48.3,'대전':51.7,'울산':51.9,'세종':53.5,'경기':52.5,'강원':49.5,'충북':50.2,'충남':49.0,'전북':47.5,'전남':46.9,'경북':50.2,'경남':53.5,'제주':47.6},
    'regional_early_turnout':{'서울':32.6,'부산':29.6,'대구':25.6,'인천':30.1,'광주':38.0,'대전':30.3,'울산':30.1,'세종':36.8,'경기':29.5,'강원':32.6,'충북':30.6,'충남':30.2,'전북':38.5,'전남':41.2,'경북':30.7,'경남':30.7,'제주':28.5},
    'regional_sample_turnout':{'서울':69.4,'부산':67.4,'대구':63.9,'인천':66.2,'광주':68.1,'대전':65.8,'울산':67.4,'세종':70.1,'경기':66.9,'강원':66.5,'충북':65.6,'충남':65.0,'전북':68.0,'전남':70.2,'경북':66.4,'경남':68.0,'제주':61.8},
    'methodology': [
        {'label':'확정 전체 투표율','method':'공식 확정 집계','denominator':'전체 선거인','pages':'7·20쪽'},
        {'label':'전체 선거인 투표율','method':'표본조사','denominator':'전국 1,505개 투표구 · 선거인 4,480,811명(10.1%) · 사전투표자 포함','pages':'4·22~29쪽'},
        {'label':'선거일(본투표) 투표율','method':'표본조사','denominator':'위 1,505개 표본 투표구에서 사전·거소·선상·재외 등 이미 투표한 사람 제외(3,039,100명)','pages':'4·30~34쪽'},
        {'label':'사전투표율','method':'전수조사','denominator':'통합선거인명부 · 사전투표자 13,849,043명','pages':'6·35~43쪽'},
        {'label':'국외부재자 투표율','method':'전수조사','denominator':'국외부재자명부 119,897명 · 회송용봉투 접수 기준','pages':'6·52~59쪽'},
        {'label':'재외선거인 투표율','method':'전수조사','denominator':'재외선거인명부 28,092명 · 회송용봉투 접수 기준','pages':'6·60~67쪽'},
    ],
    'source':{'publisher':'중앙선거관리위원회','pdf':NEC_REPORT,'pdf_url':REPORT_URL,'regional_csv':DISTRICT_SOURCE,'proportional_csv':PR_SOURCE,'seats_historical_crosscheck':SEAT_REFERENCE},
    'aggregation_notice':'지역구 254개는 국회의원 지역구 선거구 수입니다. 비례대표 253개 구·시·군 집계행은 행정구역 단위 집계행 수로 단위가 다르며, 이것만으로 원본 누락 여부를 판정할 수 없습니다. 완전성은 전국 합계 등으로 별도 검산해야 합니다.',
}

# Original code module may be loaded by either old or revised main app. No mutation of underlying dataset.
def _dataset():
    try:
        import server  # original NEWSROOM LAB module already loaded in the host
        value=getattr(server,'official_store',{}).get('dataset')
        return value if value and value.get('mode') != 'SYNTHETIC_SAMPLE_NOT_OFFICIAL' else None
    except Exception:return None

@router.get('/report.pdf')
def report_pdf():
    if not PDF.is_file():raise HTTPException(404,'원본 PDF를 찾을 수 없습니다.')
    return FileResponse(PDF,media_type='application/pdf',filename=PDF.name)

@router.get('/summary')
def summary():
    ds=_dataset()
    return {**REAL,'uploaded_count_status':{'loaded':bool(ds),'district_count':ds.get('district_count') if ds else None,
        'source_url':ds.get('source_url') if ds else None,'verified_by_independent_comparison':False},
        'source_warning':'수치 출처: 중앙선관위 보고서와 선거결과 발표. 원본 개표 CSV의 행별 독립 대조는 완료되지 않았습니다.'}

class Question(BaseModel):
    question:str=Field(min_length=2,max_length=350)

# The original PDF text is indexed as verbatim excerpts, not generated claims.
@lru_cache(maxsize=1)
def _pdf_index():
    p=HERE/'선관위_PDF_근거검색색인.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else []

def _lookup_pdf(q):
    toks=[t for t in re.findall(r'[가-힣]{2,}|[0-9]{2,}',q) if t not in {'자료','보도','국회의원','총선','선거','기준','대해서','알려줘','어떻게','결과','2024','22대','투표율'}]
    if not toks:return None
    ranked=[]
    for chunk in _pdf_index():
        raw=re.sub(r'\s+','',chunk['text'])
        hits=[t for t in toks if t in raw]
        if not hits:continue
        # Require informative matches; '투표율' alone is never a valid hit.
        enough=(len(hits)>=2 or (len(toks)==1 and len(toks[0])>=4))
        if not enough:continue
        score=sum(len(t)*len(t) for t in hits)+len(hits)*6
        if chunk['printed_page']<=70:score+=5
        ranked.append((score,chunk))
    if not ranked:return None
    ranked.sort(key=lambda x:-x[0])
    best=ranked[0][1]
    return {'status':'원문 발췌 · 의미 확인 필요',
        'answer':'중앙선관위 보고서에서 관련 문구를 찾았습니다. 원문 발췌: '+best['text'][:410]+('…' if len(best['text'])>410 else '')+' 이 발췌문은 자동 검색 결과이며 개별 수치의 의미는 원문 표와 분모를 확인해야 합니다.',
        'evidence':[{'source':NEC_REPORT,'pages':f"인쇄 {best['printed_page']}쪽 / PDF {best['pdf_page']}쪽",'url':REPORT_URL}]}

# Explicit retrieval rules: answer only covered questions; unsupported -> unknown.
def _answer(q: str):
    s=re.sub(r'\s+','',q)
    def found(answer,pages='',source=NEC_REPORT):
        return {'status':'확인','answer':answer,'evidence':[{'source':source,'pages':pages,'url':REPORT_URL if source==NEC_REPORT else (DISTRICT_SOURCE if source=='중앙선거관리위원회 개표결과' else SEAT_REFERENCE)}]}
    # Check region first: a nationwide 51.8% answer would be wrong for a region-specific question.
    region=next((r for r in REAL['regional_final_turnout'] if r in s),None)
    if region and ('투표율' in s or '투표' in s):
        if any(v in s for v in ['사전투표','사전']):
            val=REAL['regional_early_turnout'][region]
            return found(f'{region}의 사전투표율은 {val:.1f}%입니다. 전체 선거인 대비 비율로, 통합선거인명부를 활용한 전수조사 수치입니다.','20·36~37쪽')
        if '표본' in s and '본투표' not in q and '선거일' not in s and '당일투표' not in s:
            val=REAL['regional_sample_turnout'][region]
            return found(f'{region}의 전체 선거인 표본조사 투표율은 {val:.1f}%입니다. 표본조사 결과로 실제 확정 투표율과 구분해야 합니다.','21·25쪽')
        if any(v in s for v in ['선거일','당일투표']) or '본투표' in q:
            val=REAL['regional_day_sample_turnout'][region]
            return found(f'{region}의 선거일 투표율은 {val:.1f}%입니다. 1,505개 표본 투표구 자료에서 사전투표 등으로 이미 투표한 사람을 제외한 선거인 기준입니다.','30~32쪽')
        val=REAL['regional_final_turnout'][region]
        return found(f'{region}의 실제 확정 전체 투표율은 {val:.1f}%입니다. 전체 선거인 기준입니다.','20쪽')
    # When a final district CSV has been loaded by the original program, answer from that source.
    ds=_dataset()
    if ds and any(word in s for word in ['득표','후보','누가이겼','당선']):
        for d in ds.get('districts',[]):
            r=d.get('region',''); district=d.get('district','')
            # Both region and district must be present to avoid ambiguous names.
            if not r or not district:continue
            rshort=r.replace('특별시','').replace('광역시','').replace('특별자치시','').replace('특별자치도','').replace('도','')
            if (r in q or rshort in s) and district.replace(' ','') in s:
                cands=[v for v in ds.get('votes',[]) if v['region']==r and v['district']==district]
                if not cands:break
                cands.sort(key=lambda v:-v['votes'])
                total=sum(v['votes'] for v in cands)
                pieces=[f"{v['candidate']} {v['votes']:,}표({v['votes']/total*100:.2f}%)" for v in cands[:10]] if total else []
                return {'status':'업로드된 개표자료 내 확인','answer':f'{r} {district}의 후보별 득표 결과: '+', '.join(pieces)+'. 이 수치는 같은 선거구 내 후보별 합계 대비 비율이며 선거인 투표율이 아닙니다. 파일 원본과의 독립 교차검증은 별도로 필요합니다.',
                    'evidence':[{'source':'중앙선거관리위원회 개표결과 (프로그램에 불러온 파일 기준)','pages':district,'url':ds.get('source_url',DISTRICT_SOURCE)}]}
    if ('표본' in s and '1505' in s) or ('사전투표' in s and ('전수' in s or '표본' in s)):
        return found('사전투표는 통합선거인명부를 이용한 전수조사입니다. 전체 선거인 표본조사는 전국 1,505개 투표구의 선거인 4,480,811명(10.1%)을 조사했습니다. 투표구와 지역구는 서로 다른 단위입니다.','4~6쪽')
    if ((re.search(r'(?<!표)본투표',q) is not None) or '선거일투표' in s or '당일투표' in s) and ('51.8' in s or '기준' in s or '표본' in s or '투표율' in s):
        return found('선거일 투표율 51.8%는 표본 1,505개 투표구의 선거인 가운데 사전투표·거소·선상·재외투표 등으로 이미 투표한 사람을 제외한 3,039,100명을 분모로 계산한 값입니다. 전체 투표자 중 본투표자 비중 52.7%와 다릅니다.','4·22·30쪽')
    if '253' in s and ('254' in s or '비례' in s):
        return {'status':'부분 확인','answer':REAL['aggregation_notice'],'evidence':[{'source':'중앙선거관리위원회 개표결과','pages':'데이터 정의(지역구·비례대표 CSV 별도)','url':DISTRICT_SOURCE}]}
    if ('비례' in s and ('의석' in s or '몇석' in s or '당선' in s)) or ('정당' in s and ('의석' in s or '몇석' in s)):
        pieces=[f"{x['party']} {x['total']}석(지역구 {x['constituency']}석·비례 {x['proportional']}석)" for x in REAL['party_seats']]
        return found('2024년 제22대 총선 전체 300석의 정당별 결과: '+', '.join(pieces)+'.','2024-04-11 결과 보도','2024년 개표완료 결과 보도')
    if '비례' in s and ('득표율' in s or '득표수' in s or '투표율' in s):
        return {'status':'확인 불가','answer':'현재 내장 자료에는 비례대표 정당별 득표수·득표율 원본이 없어 답할 수 없습니다. 비례대표 개표결과 CSV를 불러와 검산해야 합니다. 의석수는 득표율과 다릅니다.','evidence':[{'source':'중앙선거관리위원회 비례대표 개표결과 CSV','pages':'별도 자료 필요','url':PR_SOURCE}]}
    if '표본' in s and ('전국' in s or '전체' in s) and ('투표율' in s or '67.2' in s) and '사전' not in s:
        return found('전국 전체 선거인 표본조사 투표율은 67.2%입니다. 조사 대상은 1,505개 투표구의 선거인 4,480,811명(10.1%)이며, 실제 최종 전체 투표율 67.0%와 구분해야 합니다.','4·21쪽')
    if ('사전' in s and ('남' in s or '여' in s or '성별' in s)):
        return found('사전투표율은 남성 33.2%, 여성 29.4%로 남성이 3.8%p 높았습니다. 통합선거인명부를 이용한 전수조사 결과입니다.','35쪽')
    if ('여성' in s or '남성' in s or '남녀' in s or '성별' in s) and ('전체' in s or '총선' in s or '투표율' in s):
        return found('전체 선거인 표본조사에서 여성 67.9%, 남성 66.5%로 여성이 1.4%p 높았습니다. 표본 투표구에 속한 선거인 기준이며 전수조사가 아닙니다.','22쪽')
    if ('20대후반' in s or '20~24' in s) and ('남' in s or '여' in s or '격차' in s):
        return found('20대 후반 전체 투표율은 남성 45.6%, 여성 58.2%로 12.6%p 차이가 났습니다. 전국 1,505개 투표구 표본조사 결과입니다.','27~28쪽')
    if '70대' in s and ('투표율' in s or '20대' in s):
        return found('전체 선거인 표본조사에서 70대 84.7%, 20대 52.4%입니다. 이는 투표 참여율이며 후보나 정당 지지율이 아닙니다.','23쪽')
    if '사전' in s and ('31.3' in s or '투표율' in s or '비중' in s):
        return found('전체 선거인 대비 사전투표율은 약 31.3%입니다. 실제 투표한 사람 전체를 100%로 보면 사전투표자는 46.7%입니다. 분모가 다르므로 구분해야 합니다.','20·22·35쪽')
    if ('재외' in s or '국외부재' in s) and ('투표율' in s or '전수' in s):
        return found('재외투표(국외부재자와 재외선거인 합계) 투표율은 62.8%이며 전수조사입니다. 국외부재자 71.1%, 재외선거인 27.4%입니다.','6·13~15쪽')
    if ('비례' in s and ('지역구' in s or '구분' in s)):
        return found('제22대 국회의원선거 의석은 지역구 254석, 비례대표 46석, 합계 300석입니다. 이는 정당별 비례대표 득표율과 별개의 지표입니다.','2024-04-11 결과 보도','2024년 개표완료 결과 보도')
    if ('총선' in s or '전체' in s or '22대' in s) and ('67' in s or '투표율' in s) and not ('사전' in s or '선거일' in s or '본투표' in s):
        return found('제22대 총선의 실제 확정 전체 투표율은 67.0%이고, 전체 선거인 표본조사의 투표율은 67.2%입니다. 두 결과의 차이는 0.2%p입니다.','7·21쪽')
    if any(w in s for w in ['왜','이유','비용','전산화','시각별','시간별']):
        return {'status':'확인 불가','answer':'해당 원인·비용·전산화 여부 또는 시간대별 개표 기록은 현재 보고서·확정 자료에서 확인되지 않습니다. 선관위 담당 부서의 추가 확인이 필요합니다.','evidence':[]}
    extracted=_lookup_pdf(q)
    if extracted:return extracted
    return {'status':'확인 불가','answer':'제공된 중앙선관위 투표율 분석 PDF와 현재 확인된 개표 자료만으로 해당 질문의 답을 확인할 수 없습니다. 추측하여 답하지 않습니다. 질문을 구체화하거나 관련 원본 데이터를 추가해야 합니다.','evidence':[]}

@router.post('/question')
def question(body:Question):
    return {'question':body.question,**_answer(body.question),'engine':'원문 대조형 규칙 검색 (LLM·벡터 RAG 아님)','human_review_required':True}

class DraftRequest(BaseModel):
    topic:str='overall'
    mode:str='real'

DRAFTS:dict[str,dict]={}

def facts_for(topic):
    if topic=='age':
        return {'title':'제22대 총선, 70대 투표율 84.7%·20대 52.4%',
            'lead':'2024년 제22대 국회의원선거 투표율 분석에서 70대의 투표율은 84.7%로 가장 높았으며 20대는 52.4%로 가장 낮게 나타났습니다.',
            'body':'중앙선거관리위원회는 전국 1,505개 투표구에 속한 선거인 448만 811명을 표본으로 조사했습니다. 따라서 이 수치는 전체 선거인 표본조사 결과이며 전수집계가 아닙니다.',
            'facts':['84.7%','52.4%','1,505개'],'pages':'4·23쪽'}
    if topic=='gender':
        return {'title':'22대 총선 전체 투표율 여성 67.9%·남성 66.5%',
            'lead':'중앙선관위 표본조사에서 제22대 총선의 여성 투표율이 67.9%로 남성 66.5%보다 1.4%p 높았습니다.',
            'body':'이는 전국 1,505개 투표구를 대상으로 한 전체 선거인 표본조사 결과입니다. 성별 정당 지지율을 의미하지 않습니다.',
            'facts':['67.9%','66.5%','1.4%p'],'pages':'4·22쪽'}
    if topic=='early':
        return {'title':'22대 총선 사전투표자, 전체 투표자의 46.7%',
            'lead':'제22대 총선에서 실제 투표한 사람 중 사전투표를 이용한 비율은 46.7%였습니다. 선거일 투표는 52.7%였습니다.',
            'body':'사전투표율 31.3%는 전체 선거인 대비 수치로, 전체 투표자 대비 비율 46.7%와 구분됩니다. 사전투표는 통합선거인명부에 의한 전수조사입니다.',
            'facts':['46.7%','52.7%','31.3%'],'pages':'6·20·22쪽'}
    if topic=='overseas':
        return {'title':'제22대 총선 재외투표율 62.8%…국외부재자 71.1%',
            'lead':'2024년 제22대 총선의 재외투표 전체 투표율은 62.8%로 집계됐습니다. 국외부재자는 71.1%, 재외선거인은 27.4%였습니다.',
            'body':'중앙선관위는 국외부재자와 재외선거인 명부를 각각 전수조사했습니다. 재외투표 전체는 두 집단을 합친 통계입니다.',
            'facts':['62.8%','71.1%','27.4%'],'pages':'6·13~15쪽'}
    if topic=='seats':
        return {'title':'22대 총선 최종 300석…민주당 계열 175석·국민의힘 계열 108석',
            'lead':'2024년 4월 10일 실시된 제22대 총선에서 더불어민주당·더불어민주연합이 175석, 국민의힘·국민의미래가 108석을 확보했습니다.',
            'body':'전체 300석 중 지역구는 254석, 비례대표는 46석입니다. 조국혁신당은 비례대표 12석을 얻었습니다. 이 자료는 최종 의석 결과이며 시간대별 개표 진행 기록을 재현한 수치가 아닙니다.',
            'facts':['175석','108석','300석','254석','46석','12석'],'pages':'2024-04-11 결과 보도','source':'2024년 개표완료 결과 보도'}
    return {'title':'22대 총선 투표율 67.0%…사전투표율 31.3%',
        'lead':'2024년 4월 10일 치러진 제22대 국회의원선거의 최종 투표율은 67.0%로, 제21대 총선의 66.2%보다 0.8%p 높았습니다.',
        'body':'중앙선거관리위원회의 전체 선거인 표본조사 투표율은 67.2%로 실제 확정 투표율과 0.2%p 차이가 났습니다. 사전투표율은 전체 선거인 기준 31.3%였습니다.',
        'facts':['67.0%','66.2%','0.8%p','67.2%','31.3%'],'pages':'7·20·21쪽'}

@router.post('/draft')
def draft(body:DraftRequest):
    if body.mode!='real':raise HTTPException(422,'실제 확정 결과 모드에서만 생성합니다.')
    if body.topic not in {'overall','age','gender','early','overseas','seats'}:raise HTTPException(422,'지원하는 근거 주제가 아닙니다.')
    src=facts_for(body.topic);article_id='NEC24-'+uuid4().hex[:8].upper()
    result={'article_id':article_id,'topic':body.topic,'title':src['title'],'lead':src['lead'],'body':src['body'],'facts':src['facts'],'source':src.get('source',NEC_REPORT),'source_pages':src['pages'],'source_url':REPORT_URL if src.get('source') is None else SEAT_REFERENCE,'status':'검수 전 초안','editor':None}
    DRAFTS[article_id]=result
    return result

class ApproveRequest(BaseModel):
    article_id:str=Field(min_length=1,max_length=32)
    title:str=Field(min_length=5,max_length=350)
    lead:str=Field(min_length=10,max_length=2000)
    body:str=Field(min_length=10,max_length=6000)
    editor:str=Field(min_length=2,max_length=60)
    reason:str=Field(min_length=5,max_length=700)
    approve:bool=False

@router.post('/review')
def review(body:ApproveRequest):
    src=DRAFTS.get(body.article_id)
    if not src:raise HTTPException(404,'해당 초안이 없습니다.')
    combined=body.title+' '+body.lead+' '+body.body
    missing=[x for x in src['facts'] if x not in combined]
    # New numbers introduced by edits are not independently checked; human must review.
    changed=(body.title!=src['title'] or body.lead!=src['lead'] or body.body!=src['body'])
    if missing:raise HTTPException(409,'원자료와 연결된 숫자가 삭제됐습니다: '+', '.join(missing))
    number_pattern=r'\d[\d,]*(?:\.\d+)?(?:%p|%|석|명|개|표|년|월|일)'
    original=src.setdefault('verified_numeric_tokens',set(re.findall(number_pattern,src['title']+' '+src['lead']+' '+src['body'])))
    new_tokens=set(re.findall(number_pattern,combined))-set(original)
    if new_tokens:raise HTTPException(409,'원본 근거에 없는 새 수치를 추가했습니다: '+', '.join(sorted(new_tokens)))
    src.update({'title':body.title,'lead':body.lead,'body':body.body,'editor':body.editor,'review_reason':body.reason,
        'status':'사람 검수 승인 · 외부 게시 아님' if body.approve else '편집 중 · 사람 검수 필요','updated_at':datetime.now(timezone.utc).isoformat()})
    return {'status':src['status'],'article_id':body.article_id,'missing_facts':missing,'edited':changed,'notice':'숫자 존재·신규 수치 차단 검증만 자동 수행했습니다. 문장의 사실관계와 판단은 승인한 편집자가 원문과 대조해야 합니다.'}

@router.get('/patch.js')
def patch_js():return FileResponse(HERE/'newsroom_patch_ui.js',media_type='application/javascript; charset=utf-8')
@router.get('/patch.css')
def patch_css():return FileResponse(HERE/'newsroom_patch_ui.css',media_type='text/css; charset=utf-8')
