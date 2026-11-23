"""Local-only FastAPI UI; all uploads kept in volatile memory, not published."""
from __future__ import annotations
from collections import OrderedDict
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
import secrets
import json
import pandas as pd
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .catalog import KINDS, METHODS
from .engine import MAX_FILE, analyze, profile, read_data, recommend, table_rows, transform_data

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'app'/'static'
SAMPLES=ROOT/'samples'
app=FastAPI(title='통합 통계 분석 워크벤치',version='1.0.0')
app.mount('/static',StaticFiles(directory=str(STATIC)),name='static')
DATASETS:OrderedDict[str,dict]=OrderedDict()


def _stamp():return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _add(name,df,kind='auto',source=None,source_url=None,origin='upload'):
    if kind not in KINDS:raise ValueError('지원하지 않는 데이터 분야')
    token=secrets.token_urlsafe(18)
    entry={'id':token,'name':name,'kind':kind,'source':source or ('자체 생성 교육용 예제' if origin=='sample' else '사용자 업로드; 공식성 미검증'),
           'source_url':source_url or '','origin':origin,'at':_stamp(),'df':df,'history':[]}
    DATASETS[token]=entry
    while len(DATASETS)>5:DATASETS.popitem(last=False)
    return _meta(entry)


def _meta(d):
    return {'id':d['id'],'name':d['name'],'kind':d['kind'],'source':d['source'],'source_url':d['source_url'],
            'origin':d['origin'],'at':d['at'],'profile':profile(d['df']),'preview':table_rows(d['df'],8),
            'recommended':recommend(d['df'],d['kind'])}


def _entry(dataset_id):
    if dataset_id not in DATASETS:raise HTTPException(404,'데이터가 없습니다. 새로 업로드하거나 샘플을 다시 선택하세요.')
    return DATASETS[dataset_id]


class Filter(BaseModel):
    column:str
    op:str='equals'
    value:str=''
class KindUpdate(BaseModel):
    kind:str

class TransformInput(BaseModel):
    dataset_id:str
    filters:list[Filter]=Field(default_factory=list,max_length=4)
    missing_policy:str='keep'
    deduplicate:bool=False
    derived:str='none'
    x:str|None=None
    y:str|None=None
    new_column:str='derived_value'

class Query(BaseModel):
    dataset_id:str
    method:str
    options:dict=Field(default_factory=dict)
    filters:list[Filter]=Field(default_factory=list,max_length=4)
    missing:str='drop'


@app.get('/')
def index():return FileResponse(STATIC/'index.html')
@app.get('/api/health')
def health():return {'status':'ok','version':'1.0','data_sets':len(DATASETS),'at':_stamp()}
@app.get('/api/catalog')
def catalog():return {'kinds':KINDS,'methods':METHODS,'limits':{'max_file_mib':12,'max_rows':50000,'max_columns':120}}
@app.get('/api/samples')
def sample_list():
    return {'samples':[{'name':p.name,'size_bytes':p.stat().st_size,'label':{
       'sample_election.csv':'교육용 모의 선거 (17개 시도 · 12단계)',
       'sample_air.csv':'환경 관측값 (합성 샘플)',
       'sample_sales.csv':'판매·매출 (합성 샘플)',
       'sample_news.jsonl':'뉴스 제목·분야 (합성 샘플)'} .get(p.name,p.name)}
       for p in sorted(SAMPLES.iterdir()) if p.suffix.lower() in ('.csv','.json','.jsonl','.xlsx')]}

@app.post('/api/samples/{filename}/load')
def sample_load(filename:str):
    if '/' in filename or '\\' in filename or filename.startswith('.'):raise HTTPException(400,'파일명 오류')
    p=SAMPLES/filename
    if not p.is_file():raise HTTPException(404,'샘플을 찾을 수 없음')
    kind=('election' if 'election' in filename else 'air' if 'air' in filename else 'commerce' if 'sales' in filename else 'news')
    try:return _add(p.name,read_data(p.read_bytes(),p.name),kind=kind,origin='sample')
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@app.post('/api/datasets/upload')
async def upload(file:UploadFile=File(...),kind:str=Form('auto'),source:str=Form(''),source_url:str=Form('')):
    if kind not in KINDS:raise HTTPException(422,'자료 분야를 다시 선택하세요.')
    contents=await file.read(MAX_FILE+1)
    if len(contents)>MAX_FILE:raise HTTPException(413,'최대 12MiB 파일까지 허용됩니다.')
    filename=(file.filename or '').split('/')[-1].split('\\')[-1]
    try:
        df=read_data(contents,filename)
        return _add(filename,df,kind,source=source.strip()[:200] or None,source_url=source_url.strip()[:500])
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@app.get('/api/datasets/{dataset_id}')
def get_dataset(dataset_id:str):return _meta(_entry(dataset_id))

@app.patch('/api/datasets/{dataset_id}/kind')
def set_kind(dataset_id:str,body:KindUpdate):
    if body.kind not in KINDS:raise HTTPException(422,'자료 유형이 없습니다.')
    entry=_entry(dataset_id)
    entry['kind']=body.kind
    return _meta(entry)

@app.post('/api/analyze')
def run_query(body:Query):
    e=_entry(body.dataset_id)
    try:
        result=analyze(e['df'],body.method,body.options,[f.model_dump() for f in body.filters],body.missing)
    except (ValueError,KeyError,TypeError,OverflowError) as exc:raise HTTPException(422,str(exc)) from exc
    result['source']={'name':e['name'],'kind':e['kind'],'origin':e['origin'],'label':e['source'],
                      'url':e['source_url'],'verified':False,'dataset_id':e['id']}
    result['ran_at']=_stamp()
    history={'method':result['method'],'method_name':result['method_name'],'summary':result['summary'],
             'options':body.options,'filters':[f.model_dump() for f in body.filters],
             'at':result['ran_at'],'input_rows':result['input_rows'],'filtered_rows':result['filtered_rows']}
    e['history'].append(history);e['history']=e['history'][-20:]
    return result

@app.get('/api/datasets/{dataset_id}/history')
def history(dataset_id:str):return {'history':_entry(dataset_id)['history'][::-1]}

@app.get('/api/datasets/{dataset_id}/export-original.csv')
def export_source(dataset_id:str):
    e=_entry(dataset_id);csv_text=e['df'].to_csv(index=False)
    return StreamingResponse(iter([b'\xef\xbb\xbf',csv_text.encode('utf-8')]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="filtered_source_preview.csv"'})

@app.post('/api/transform/export')
def export_transformed(body:TransformInput):
    entry=_entry(body.dataset_id)
    try:
        data,stats=transform_data(entry['df'],[f.model_dump() for f in body.filters],
          missing_policy=body.missing_policy,deduplicate=body.deduplicate,derived=body.derived,
          x=body.x,y=body.y,new_column=body.new_column)
    except (ValueError,KeyError,TypeError) as exc:raise HTTPException(422,str(exc)) from exc
    # CSV formula injection protection for spreadsheet applications. Numeric literals remain numeric.
    def guarded(v):
        if not isinstance(v,str):return v
        trimmed=v.lstrip()
        if trimmed.startswith(('=','+','-','@')):
            import re
            if re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',trimmed):return v
            return "'"+v
        return v
    clean=data.map(guarded) if hasattr(data,'map') else data.applymap(guarded)
    csv_bytes=b'\xef\xbb\xbf'+clean.to_csv(index=False).encode('utf-8')
    return StreamingResponse(iter([csv_bytes]),media_type='text/csv; charset=utf-8',headers={
       'Content-Disposition':'attachment; filename="processed_data.csv"',
       'X-Processed-Rows':str(stats['output_rows']), 'X-Input-Rows':str(stats['input_rows'])})
