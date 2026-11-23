"""FastAPI + WebSocket fictional broadcast rehearsal, no external election API."""
from __future__ import annotations
import asyncio, os, csv, io
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from engine import generate, evolve, snapshot, evidence_for, draft_from_evidence, validate_draft, clock
from rag_demo import search_documents
from official_results import parse_csv as parse_official, analyze as analyze_official, replay as replay_official, DataError
from analytics import analyze, compact_history, METHODS, LIMIT_HISTORY

ROOT=Path(__file__).parent
app=FastAPI(title='모의 선거 개표 방송 제작실',version='0.1-demo')
app.mount('/static',StaticFiles(directory=str(ROOT/'static')),name='static')
SEED=20261111
state={'districts':generate(SEED),'seed':SEED,'step':0,'running':True,'interval':2.0,
       'articles':{},'audit':[],'last_changes':[]}
clients=set()
# Independent source layer: never mixed with the simulation websocket/state.
official_store={'dataset':None,'loaded_at':None}

def load_local_election_sample():
    path=ROOT/'samples'/'SIMULATION_ONLY_nationwide_17regions_68districts.csv'
    parsed=parse_official(path.read_bytes(), source_url='LOCAL_SYNTHETIC_DEMO',
                          election_name='교육용 가상 선거 - 전국 17개 시도 68개 모의 선거구', demo_mode=True)
    official_store['dataset']=parsed
    official_store['loaded_at']=clock()
    return parsed

load_local_election_sample()
state['history']=[compact_history(snapshot(state['districts'], 0, SEED))]
for init_step in range(1, 7):
    state['last_changes']=evolve(state['districts'], SEED, init_step)
    state['step']=init_step
    state['history'].append(compact_history(snapshot(state['districts'], init_step, SEED)))

class Control(BaseModel):
    action:str
    seed:int|None=None
    interval:float|None=None

class DraftInput(BaseModel):
    scope:str='national'
    region:str|None=None
    district_id:str|None=None

class ReviewInput(BaseModel):
    editor:str='교육용 편집자'
    approve:bool=False
    reason:str=''
    revised_text:str|None=None

def make_snapshot():
    s=snapshot(state['districts'],state['step'],state['seed'])
    s['running']=state['running'];s['interval']=state['interval'];s['latest_changes']=state['last_changes'][:30]
    return s

async def broadcast():
    if not clients:return
    payload={'type':'snapshot','data':make_snapshot()}
    for ws in tuple(clients):
        try:await ws.send_json(payload)
        except Exception:clients.discard(ws)

async def tick():
    state['step']+=1
    state['last_changes']=evolve(state['districts'],state['seed'],state['step'])
    state['history'].append(compact_history(make_snapshot()))
    del state['history'][:-LIMIT_HISTORY]
    await broadcast()

async def ticker():
    while True:
        await asyncio.sleep(state['interval'])
        if state['running']:await tick()

@app.on_event('startup')
async def start():
    app.state.ticker=asyncio.create_task(ticker())

@app.on_event('shutdown')
async def stop():
    app.state.ticker.cancel()

@app.get('/')
def index():return FileResponse(ROOT/'static'/'index.html')

@app.get('/api/snapshot')
def get_snapshot():return make_snapshot()

@app.get('/api/rag/search')
def rag_search(question:str,k:int=3):
    try:docs=search_documents(question,k)
    except ValueError as err:raise HTTPException(400,str(err))
    return {'mode':'offline_lexical_evidence_search',
            'warning':'교육용 문서에 대한 키워드 검색. LangChain/벡터 검색/LLM 호출이 아닙니다.',
            'question':question,'results':docs,'count':len(docs)}

@app.get('/api/analytics/methods')
def analytics_methods():
    return [{'id': k, 'name': v[0], 'description': v[1], 'chart': v[2]} for k,v in METHODS.items()]

@app.get('/api/analytics')
def analytics_report(method: str='vote_share', scope: str='national',
                     region: str|None=None, district_id: str|None=None, window: int=30):
    try:
        return analyze(make_snapshot(), state['history'], method=method, scope=scope,
                       region=region, district_id=district_id, window=window)
    except ValueError as err:
        raise HTTPException(400, str(err)) from err

@app.get('/api/analytics/export.csv')
def analytics_csv(method: str='vote_share', scope: str='national',
                  region: str|None=None, district_id: str|None=None, window: int=30):
    report=analytics_report(method,scope,region,district_id,window)
    output=io.StringIO(newline='')
    writer=csv.writer(output)
    writer.writerow(['mode','source','scope','method','updated_at','step']+[c['key'] for c in report['columns']])
    for row in report['rows']:
        writer.writerow(['SIMULATION_ONLY', report['source'], report['scope_label'],
                         report['method_label'], report['updated_at'], report['step']]
                        +[row.get(c['key'],'') for c in report['columns']])
    return Response(output.getvalue().encode('utf-8-sig'),media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="fictional_election_analytics.csv"'})

@app.get('/api/export/districts.csv')
def export_districts():
    out=io.StringIO(newline='')
    writer=csv.writer(out)
    writer.writerow(['mode','source','updated_at','district_id','region','district_name','progress_pct',
                     'candidate_A_votes','candidate_B_votes','candidate_C_votes','counted_total'])
    snap=make_snapshot()
    for d in snap['districts']:
        writer.writerow(['SIMULATION_ONLY','Synthetic seeded random data',snap['updated_at'],d['id'],d['region'],
                         d['name'],d['progress_pct'],*d['votes'],d['counted']])
    return Response(out.getvalue().encode('utf-8-sig'),media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition':'attachment; filename="fictional_district_votes.csv"'})

@app.get('/api/articles')
def list_articles():return list(state['articles'].values())[::-1]

@app.get('/api/audit')
def list_audit():return state['audit'][-100:][::-1]

@app.post('/api/control')
async def control(body:Control):
    if body.action=='pause':state['running']=False
    elif body.action=='resume':state['running']=True
    elif body.action=='tick':await tick()
    elif body.action=='reset':
        seed=body.seed if body.seed is not None else state['seed']
        if abs(seed)>1000000000:raise HTTPException(400,'seed 범위 초과')
        state.update({'districts':generate(seed),'seed':seed,'step':0,'running':True,'last_changes':[], 'articles':{},'audit':[]})
        state['history']=[compact_history(make_snapshot())]
    elif body.action=='speed':
        if body.interval is None or not .25<=body.interval<=15:raise HTTPException(400,'간격 0.25~15초')
        state['interval']=body.interval
    else:raise HTTPException(400,'알 수 없는 제어')
    await broadcast()
    return {'ok':True,'action':body.action,'step':state['step']}

@app.post('/api/articles/draft')
def draft(body:DraftInput):
    snap=make_snapshot()
    try:e=evidence_for(snap,body.scope,body.region,body.district_id)
    except ValueError as err:raise HTTPException(400,str(err))
    aid=f'NEWS-{len(state["articles"])+1:04}'
    text=draft_from_evidence(e)
    record={'id':aid,'text':text,'evidence':e,'validation':validate_draft(text,e),
       'status':'draft','approved_by':None,'approved_at':None,'created_at':clock(),
       'ai_generated':False,'source_label':'교육용 난수 기반 개표','approval_reason':None}
    state['articles'][aid]=record
    state['audit'].append({'at':clock(),'action':'DRAFT_CREATED','article_id':aid,'evidence_id':e['id']})
    return record

@app.post('/api/articles/{article_id}/review')
def review(article_id:str,body:ReviewInput):
    a=state['articles'].get(article_id)
    if not a:raise HTTPException(404,'초안 없음')
    if a['status']=='approved':raise HTTPException(409,'이미 승인된 기사')
    if body.revised_text is not None:a['text']=body.revised_text
    a['validation']=validate_draft(a['text'],a['evidence'])
    if body.approve and not a['validation']['passed']:
        a['status']='review_required'
        state['audit'].append({'at':clock(),'action':'APPROVAL_BLOCKED','article_id':article_id,'errors':a['validation']['errors']})
        raise HTTPException(409,{'message':'근거 또는 수치 불일치 — 승인 차단','errors':a['validation']['errors']})
    if body.approve and not body.reason.strip():raise HTTPException(400,'사람 승인 사유가 필요합니다')
    if body.approve:
        a['status']='approved';a['approved_by']=body.editor.strip()[:60] or '교육용 편집자'
        a['approved_at']=clock();a['approval_reason']=body.reason.strip()[:250]
        action='APPROVED'
    else:
        a['status']='review_required';action='REVIEW_REQUIRED'
    state['audit'].append({'at':clock(),'action':action,'article_id':article_id,
                           'editor':body.editor[:60],'reason':body.reason[:250]})
    return a

@app.websocket('/ws')
async def websocket(ws:WebSocket):
    await ws.accept();clients.add(ws)
    try:
        await ws.send_json({'type':'snapshot','data':make_snapshot()})
        while True:
            message=await ws.receive_text()
            if message=='ping':await ws.send_json({'type':'pong','at':clock()})
    except WebSocketDisconnect:pass
    finally:clients.discard(ws)

if __name__=='__main__':
    import uvicorn
    uvicorn.run('server:app',host='127.0.0.1',port=int(os.environ.get('PORT','8502')),reload=False)


@app.get('/api/official/status')
def official_status():
    d=official_store['dataset']
    if not d:return {'loaded':False,'mode':'NOT_LOADED','message':'공식 출처로 표시된 CSV를 사용자가 로컬에서 올리세요. 미확인.'}
    return {'loaded':True,'mode':d['mode'],'verified':False,'election_name':d['election_name'],
        'source_url':d['source_url'],'source_status':d['source_status'],'sha256':d['sha256'],
        'encoding':d['encoding'],'rows':d['rows'],'summary_rows_excluded':d['summary_rows_excluded'],
        'region_count':d['region_count'],'district_count':d['district_count'],
        'regions':d['regions'],'districts':d['districts'],'loaded_at':official_store['loaded_at'],
        'is_demo':d['mode']=='SYNTHETIC_SAMPLE_NOT_OFFICIAL'}

@app.get('/api/official/demo.csv')
def official_demo_csv():
    return FileResponse(ROOT/'samples'/'SIMULATION_ONLY_nationwide_17regions_68districts.csv',
        media_type='text/csv; charset=utf-8',
        filename='SIMULATION_ONLY_election_17regions_68districts.csv')

@app.post('/api/official/load-demo')
def official_load_demo():
    load_local_election_sample()
    return official_status()

@app.post('/api/official/import')
async def official_import(request: Request, source_url: str=Query(...,max_length=450),
                          election_name: str=Query('사용자 제공 선거 결과',max_length=120)):
    # No network fetch; user-supplied original CSV remains outside the project.
    limit=35*1024*1024
    if request.headers.get('content-length','').isdigit() and int(request.headers['content-length'])>limit:
        raise HTTPException(413,'35MiB 상한 초과')
    data=await request.body()
    if len(data)>limit:raise HTTPException(413,'35MiB 상한 초과')
    try:dataset=parse_official(data,source_url=source_url,election_name=election_name)
    except DataError as err:raise HTTPException(422,str(err))
    official_store['dataset']=dataset;official_store['loaded_at']=clock()
    return official_status()

@app.get('/api/official/analyze')
def official_analyze(method: str='district_votes',region: str='',district: str='',limit: int=25):
    ds=official_store['dataset']
    if not ds:raise HTTPException(409,'CSV를 먼저 불러오세요')
    try:return analyze_official(ds,method=method,region=region,district=district,limit=limit)
    except DataError as err:raise HTTPException(422,str(err))

@app.get('/api/official/replay')
def official_replay(region: str,district: str,stages: int=20):
    ds=official_store['dataset']
    if not ds:raise HTTPException(409,'CSV를 먼저 불러오세요')
    try:return replay_official(ds,region,district,stages=stages)
    except DataError as err:raise HTTPException(422,str(err))

# V0.5: offline educational press-data preparation. Isolated from official vote CSV and mock votes.
from training_pipeline import preview_content, to_csv as press_to_csv, draft_jsonl, approved_jsonl, TrainingError

class TrainingPreviewInput(BaseModel):
    kind: str = 'csv'
    content: str

class TrainingApprovedInput(BaseModel):
    reviewer: str
    rights_confirmed: bool = False
    records: list[dict]

@app.get('/api/training/sample')
def training_sample():
    text=(ROOT/'samples'/'crawling_training'/'press_raw_DEMO.csv').read_text(encoding='utf-8-sig')
    result=preview_content(text,kind='csv',synthetic=True)
    return {**result,'draft_csv':press_to_csv(result['records']), 'draft_jsonl':draft_jsonl(result['records'])}

@app.post('/api/training/preview')
def training_preview(body:TrainingPreviewInput):
    try:result=preview_content(body.content,kind=body.kind,synthetic=False)
    except TrainingError as exc:raise HTTPException(422,str(exc)) from exc
    return {**result,'draft_csv':press_to_csv(result['records']), 'draft_jsonl':draft_jsonl(result['records'])}

@app.post('/api/training/export-reviewed')
def training_export_reviewed(body:TrainingApprovedInput):
    try:lines=approved_jsonl(body.records,body.reviewer,body.rights_confirmed)
    except TrainingError as exc:raise HTTPException(422,str(exc)) from exc
    return {'status':'USER_MARKED_REVIEWED_NOT_EXTERNALLY_CERTIFIED',
            'notice':'사용자가 직접 승인 표시한 항목만 포함. 출처·사실·이용권한은 서버가 독립 확인하지 않았습니다.',
            'count':len(body.records),'jsonl':lines}
