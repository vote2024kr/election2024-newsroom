"""Project 1 classroom integration: existing NEWSROOM LAB + STAT WORKBENCH.
* Only hypothetical counting in WebSocket; no official live feed.
* Offline lexical document search, NOT LangChain vector RAG/LLM.
* Human approval is a local classroom gate; no production identity authentication.
"""
from __future__ import annotations
import sys, re
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'newsroom')) # preserve original internal imports
sys.path.insert(0,str(ROOT))
import server as newsroom
from workbench.app import server as stats
from project1_audit import record, list_events, initialize
from project1_sparse_retrieval import search as tfidf_search

# Curated Project 1 methods: the generic 17-method workbench remains intact.
# These use the original newsroom calculation functions, without duplicating
# vote-share denominators or treating a final CSV as a real-time time series.
ELECTION_METHODS = [
    {'id':'live_vote_share','name':'모의 개표 · 후보별 현재 득표율','source':'simulation','needs':'현재 모의 개표 단계'},
    {'id':'live_lead_margin','name':'모의 개표 · 선거구 1·2위 격차','source':'simulation','needs':'현재 모의 선거구'},
    {'id':'live_candidate_trend','name':'모의 개표 · 후보별 누적 변화','source':'simulation','needs':'모의 단계 이력'},
    {'id':'live_increment_trend','name':'모의 개표 · 단계별 추가 집계','source':'simulation','needs':'모의 단계 이력'},
    {'id':'final_district_votes','name':'최종 CSV · 선거구별 후보표 합계','source':'final_csv','needs':'지역·선거구·후보·득표수'},
    {'id':'final_candidate_share','name':'최종 CSV · 선거구별 후보 득표율','source':'final_csv','needs':'시도와 선거구 모두 선택 필수'},
    {'id':'final_lead_margin','name':'최종 CSV · 선거구 1·2위 격차','source':'final_csv','needs':'같은 선거구의 후보 2인 이상'},
    {'id':'final_close_races','name':'최종 CSV · 근소 격차 선거구','source':'final_csv','needs':'동일 선거구 후보 득표수'},
    {'id':'final_region_votes','name':'최종 CSV · 시도별 집계 표수','source':'final_csv','needs':'시도·선거구·후보·득표수'},
    {'id':'final_vote_distribution','name':'최종 CSV · 선거구 집계표 분포','source':'final_csv','needs':'선거구별 합계 표수'},
]
ELECTION_METHOD_MAP = {item['id']:item for item in ELECTION_METHODS}

initialize()
app=newsroom.app
# An isolated analysis ASGI app; original workbench routes and NEWSROOM routes untouched.
app.mount('/workbench',stats.app,name='statistics_workbench')

class DrillInput(BaseModel):
    scenario:str='valid'
    scope:str='national'
    region:str|None=None
    district_id:str|None=None

class ApprovalInput(BaseModel):
    article_id:str=Field(min_length=1,max_length=48)
    editor:str=Field(min_length=2,max_length=60)
    reason:str=Field(min_length=5,max_length=350)
    revised_text:str|None=None

@app.get('/project1')
def project1_index():return FileResponse(ROOT/'project1_ui'/'index.html')

@app.get('/project1/static/{filename}')
def project1_static(filename:str):
    if filename not in {'project1.js','project1.css','election_stats.css','election_stats.js','broadcast_live.css','broadcast_live.js'}:raise HTTPException(404,'File not found')
    return FileResponse(ROOT/'project1_ui'/filename)

@app.get('/api/project1/status')
def project1_status():
    source=newsroom.official_status()
    return {'project':'P1_RAG_ELECTION_NEWS','mode':'EDUCATION_SIMULATION_ONLY',
        'websocket':'simulation_active','count_step':newsroom.state['step'],
        'official_final_csv':source,'official_live_feed':'NOT_IMPLEMENTED',
        'evidence_search':'offline_tfidf_sparse_vector','langchain_vector_rag':'NOT_IMPLEMENTED',
        'article_generation':'deterministic_template_not_LLM',
        'factcheck':'template_and_evidence_matching_only',
        'human_approval':'classroom_reviewer_non_authenticated',
        'audit':'local_sqlite_for_project1_drills',
        'news_video':'DEFERRED_NO_VIDEO_OR_NEW_CG',
        'statistics':'mounted_separate_app_plus_10_curated_election_methods',
        'sources_verified_external':False}

@app.get('/api/project1/election/methods')
def project1_election_methods():
    return {'methods':ELECTION_METHODS,
        'excluded':'여론조사 표본오차·회귀 예측·군집·PCA 등은 선거 개표 기사 자동 근거로 사용하지 않음',
        'notice':'투표율·실제 개표율은 필요한 분모 자료가 없으면 계산하지 않습니다.'}

@app.get('/api/project1/election/analyze')
def project1_election_analyze(method:str='live_vote_share',region:str='',district:str='',limit:int=20):
    if method not in ELECTION_METHOD_MAP:
        raise HTTPException(422,'프로젝트 1에서 허용한 선거 분석 기법이 아닙니다.')
    if not 1<=limit<=50:raise HTTPException(422,'표시 건수는 1~50입니다.')
    source=ELECTION_METHOD_MAP[method]['source']
    if source=='simulation':
        if region or district:raise HTTPException(422,'모의 개표 분석은 현재 전국 범위로만 제공합니다.')
        result=newsroom.analytics_report(method=method.removeprefix('live_'),scope='national',window=60)
        label='교육용 난수 개표 단계 · 실제 선거 결과 아님'
        source_mode='SIMULATION_ONLY'
    else:
        if district and not region:raise HTTPException(422,'선거구 선택 시 시도도 지정하세요.')
        if method=='final_candidate_share' and not district:
            raise HTTPException(422,'후보 득표율은 시도와 개별 선거구를 선택해야 합니다.')
        dataset=newsroom.official_store['dataset']
        if dataset is None:raise HTTPException(409,'최종 결과 CSV 또는 교육용 예제를 먼저 불러오세요.')
        result=newsroom.official_analyze(method=method.removeprefix('final_'),region=region,district=district,limit=limit)
        label=dataset['source_status']
        source_mode=dataset['mode']
    record('ELECTION_STAT_ANALYSIS',status='unverified',detail={'method':method,'source_mode':source_mode,
           'region':region,'district':district,'result_rows':len(result['rows'])})
    return {'method':method,'name':ELECTION_METHOD_MAP[method]['name'],'source_mode':source_mode,
            'source_label':label,'verified':False,'result':result,
            'warning':'최종 결과 CSV는 실시간 시계열이 아닙니다. 후보 득표율은 같은 선거구 내 후보 득표 합계 기준입니다. 투표율·실제 개표율·당선 예측은 계산하지 않습니다.'}

def _scramble(article,scenario):
    e=article['evidence']; original=article['text']
    if scenario=='valid':return original
    if scenario=='wrong_region':return original.replace(e['label'],'확인되지 않은 가상 지역',1)
    if scenario=='missing_id':return original.replace('['+e['id']+']','',1)
    if scenario=='wrong_votes':
        number=re.search(r'([0-9][0-9,]*)표',original)
        if not number:raise HTTPException(500,'표수 토큰 누락')
        old=number.group(1)
        return original[:number.start(1)]+f'{int(old.replace(",",""))+17:,}'+original[number.end(1):]
    raise HTTPException(422,'지원하지 않는 시나리오')

@app.get('/api/project1/rag/search')
def project1_rag_search(question:str,k:int=4):
    try:return tfidf_search(question,k)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc

@app.post('/api/project1/drill')
def project1_drill(body:DrillInput):
    if body.scenario not in {'valid','wrong_region','missing_id','wrong_votes'}:
        raise HTTPException(422,'지원되지 않는 오류 유형')
    # The original article creation and validation functions are called, not duplicated.
    a=newsroom.draft(newsroom.DraftInput(scope=body.scope,region=body.region,district_id=body.district_id))
    text=_scramble(a,body.scenario)
    a['text']=text
    a['validation']=newsroom.validate_draft(text,a['evidence'])
    if not a['validation']['passed']:a['status']='review_required'
    record('DRILL_CREATED',a['id'],body.scenario,'blocked' if not a['validation']['passed'] else 'draft',
           a['evidence']['id'],{'errors':a['validation']['errors'],'step':a['evidence']['step']})
    return {'article_id':a['id'],'scenario':body.scenario,'text':text,
      'evidence_id':a['evidence']['id'],'validation':a['validation'],
      'status':a['status'],'simulation_only':True,'broadcast_ready':False}

@app.post('/api/project1/approve')
def project1_approve(body:ApprovalInput):
    a=newsroom.state['articles'].get(body.article_id)
    if not a:raise HTTPException(404,'기사 초안이 없습니다.')
    # A newer count stage requires fresh evidence for a live-style bulletin.
    if a['evidence']['step']!=newsroom.state['step']:
        record('APPROVAL_BLOCKED_STALE',a['id'],status='blocked',evidence_id=a['evidence']['id'],
               detail={'draft_stage':a['evidence']['step'],'current_stage':newsroom.state['step']})
        raise HTTPException(409,'개표 단계가 변경되었습니다. 새 기준시각과 근거로 초안을 다시 만들어 주세요.')
    if a['status']=='approved':raise HTTPException(409,'이미 승인된 초안')
    try:
        saved=newsroom.review(body.article_id,newsroom.ReviewInput(
           editor=body.editor,approve=True,reason=body.reason,revised_text=body.revised_text))
    except HTTPException as exc:
        record('APPROVAL_BLOCKED',a['id'],status='blocked',evidence_id=a['evidence']['id'],
               detail={'errors':a['validation'].get('errors',[]),'http_status':exc.status_code})
        raise
    record('APPROVED_LOCAL_CLASSROOM',a['id'],status='approved_training_only',
           evidence_id=a['evidence']['id'],detail={'editor':body.editor,'reason':body.reason})
    return {'article_id':a['id'],'status':'approved_training_only','approved_at':saved['approved_at'],
        'evidence_id':a['evidence']['id'],'notice':'인증 없는 로컬 실습 승인, 실제 기사 게시 불가'}

@app.get('/api/project1/audit')
def project1_audit_list(limit:int=50):return {'events':list_events(limit)}

@app.post('/api/project1/transfer-final-result')
def project1_transfer():
    ds=newsroom.official_store['dataset']
    if not ds:raise HTTPException(409,'먼저 결과 CSV를 올려주세요.')
    import pandas as pd
    df=pd.DataFrame(ds['votes'])
    kind='election'
    src=('교육용 모의 최종결과' if ds['mode']=='SYNTHETIC_SAMPLE_NOT_OFFICIAL' else '사용자 업로드 최종 개표 결과 · 공식 원본 대조 미실시')
    added=stats._add(ds['election_name'],df,kind=kind,source=src,
        source_url=ds['source_url'] if ds['mode']!='SYNTHETIC_SAMPLE_NOT_OFFICIAL' else '',
        origin='sample' if ds['mode']=='SYNTHETIC_SAMPLE_NOT_OFFICIAL' else 'upload')
    record('DATASET_TRANSFERRED',status='unverified',detail={'rows':len(df),'mode':ds['mode'],'sha256':ds['sha256']})
    return {'dataset_id':added['id'],'workbench_url':'/workbench/?dataset='+added['id'],
      'mode':ds['mode'],'rows':len(df),'verified':False,
      'warning':'모의 자료 또는 사용자 업로드 자료입니다. 공식성/실시간성은 확인되지 않았습니다.'}

# V1.2 additive: 2024 verified-as-supplied historical election dataset, independent of live simulator.
from newsroom.real_data_api import bind as bind_real_2024
bind_real_2024(app)


# NEC2024_VERIFIED_PATCH_V2 — 기존 라우트·시뮬레이션 보존, 새 출처 API 추가
from newsroom_patch_v2 import router as nec2024_router
app.include_router(nec2024_router)


# V4: Additive server-rendered PostgreSQL dashboard; original routes untouched.
from newsroom_safe2024 import bind_safe
bind_safe(app)
