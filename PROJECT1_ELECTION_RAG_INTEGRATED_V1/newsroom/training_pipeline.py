"""Offline, source-aware press material → review queue → Alpaca JSONL.

No HTTP crawler, LLM, internet request or fine-tuning runs in this module.
Only users' locally supplied HTML/CSV may be parsed. Review is mandatory for final JSONL.
"""
from __future__ import annotations
import csv
from dataclasses import dataclass
from io import StringIO
from hashlib import sha256
from urllib.parse import urlsplit
import json
import re
from bs4 import BeautifulSoup

MAX_SIZE = 1_000_000
MAX_ROWS = 250
MIN_LENGTH = 200
MAX_LENGTH = 2500
INSTRUCTION = '보도자료를 읽고 확인 가능한 사실만 사용해 기사 첫 문장(리드)을 한 문장으로 작성하세요.'

class TrainingError(ValueError):
    pass


def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', str(text or '')).strip()


def parse_local_html(text: str) -> list[dict]:
    """Reads only the class exercise markup: article.press-item / .press-title / .press-body."""
    soup = BeautifulSoup(text, 'html.parser')
    rows=[]
    for article in soup.select('article.press-item'):
        title=article.select_one('.press-title')
        body=article.select_one('.press-body')
        if not title or not body: continue
        rows.append({'title':title.get_text(' ', strip=True),
                     'body':body.get_text(' ', strip=True),
                     'source_url':article.get('data-source',''),
                     'publisher':article.get('data-publisher',''),
                     'published_at':article.get('data-date','')})
        if len(rows)>MAX_ROWS:raise TrainingError('행 상한 250개를 초과했습니다.')
    if not rows: raise TrainingError('HTML에서 article.press-item/.press-title/.press-body 구조를 찾지 못했습니다.')
    return rows


def parse_local_csv(text: str) -> list[dict]:
    reader=csv.DictReader(StringIO(text, newline=''))
    if not reader.fieldnames:raise TrainingError('CSV 헤더가 없습니다.')
    names=set(reader.fieldnames)
    title_col='제목' if '제목' in names else 'title' if 'title' in names else None
    body_col='본문' if '본문' in names else 'body' if 'body' in names else None
    if not title_col or not body_col:raise TrainingError('필수 열은 제목·본문 또는 title·body입니다.')
    result=[]
    for row in reader:
        if len(result)>=MAX_ROWS:raise TrainingError('행 상한 250개를 초과했습니다.')
        if None in row:raise TrainingError('CSV 필드 수 오류')
        result.append({'title':row.get(title_col,''),'body':row.get(body_col,''),
                       'source_url':row.get('출처URL',row.get('source_url','')),
                       'publisher':row.get('기관',row.get('publisher','')),
                       'published_at':row.get('게시일',row.get('published_at',''))})
    if not result:raise TrainingError('비어 있는 CSV입니다.')
    return result


def is_valid_source_link(url: str) -> bool:
    p=urlsplit(url)
    return p.scheme=='https' and bool(p.hostname) and not (p.username or p.password)


def _lead_draft(title: str, body: str) -> str:
    """Explicitly non-LLM placeholder; never label as approved or factual news."""
    first=re.split(r'(?<=[.!?。])\s+',body)[0]
    if len(first)<15 or len(first)>160: first=title
    return clean_text(first[:160])


def transform(rows: list[dict], *, synthetic: bool=False) -> dict:
    """Deterministic cleaning and traceable review queue. Does not certify sources."""
    result=[]; rejected=[]; seen=set()
    for i,row in enumerate(rows,1):
        title=clean_text(row.get('title',''))
        body=clean_text(row.get('body',''))
        source=clean_text(row.get('source_url',''))
        pub=clean_text(row.get('publisher',''))
        date=clean_text(row.get('published_at',''))
        reasons=[]
        if not title:reasons.append('제목 없음')
        if not body:reasons.append('본문 없음')
        if body and not MIN_LENGTH<=len(body)<=MAX_LENGTH:reasons.append('본문 길이 200~2500자 기준 제외')
        digest=sha256(body.encode('utf-8')).hexdigest()
        if digest in seen:reasons.append('중복 본문')
        if not synthetic and not is_valid_source_link(source):reasons.append('출처 URL 누락 또는 HTTPS 아님')
        if not synthetic and not pub:reasons.append('발행기관 누락')
        base={'row_number':i,'title':title,'body':body,'source_url':source,
              'publisher':pub,'published_at':date,'body_sha256':digest,
              'origin':'SYNTHETIC_DEMO' if synthetic else 'USER_SUPPLIED_UNVERIFIED'}
        if reasons:rejected.append({**base,'reasons':reasons})
        else:
            result.append({**base, 'id':f'PRESS-{i:03d}',
                           'lead_draft':_lead_draft(title,body),
                           'review_status':'PENDING_HUMAN_REVIEW',
                           'reviewed_by':'','approved':False})
        seen.add(digest)
    return {'mode':'OFFLINE_LOCAL_CONTENT_ONLY', 'source_verified':False,
            'llm_called':False, 'crawling_executed':False,
            'total':len(rows),'accepted':len(result),'rejected_count':len(rejected),
            'records':result,'excluded':rejected,
            'notice':'교재의 수집·정제·검수 형식을 재현. 실제 기관 자료 수집, 출처 검증, AI 호출이나 학습 수행 아님.'}


def preview_content(text: str, kind: str='csv', *, synthetic=False) -> dict:
    if not isinstance(text,str) or not text.strip() or len(text.encode('utf-8'))>MAX_SIZE:
        raise TrainingError('텍스트는 비어 있지 않아야 하며 최대 1MB까지 허용합니다.')
    if kind not in ('csv','html'):raise TrainingError('CSV 또는 HTML만 지원합니다.')
    rows=parse_local_csv(text) if kind=='csv' else parse_local_html(text)
    return transform(rows,synthetic=synthetic)


def to_csv(records: list[dict]) -> str:
    output=StringIO(newline='')
    keys=['id','title','body','lead_draft','source_url','publisher','published_at','origin','review_status','body_sha256']
    writer=csv.DictWriter(output,fieldnames=keys,extrasaction='ignore')
    writer.writeheader();writer.writerows(records)
    return output.getvalue()


def draft_jsonl(records: list[dict]) -> str:
    """UNREVIEWED demonstration output: NEVER considered approved training data."""
    return ''.join(json.dumps({'instruction':INSTRUCTION,'input':r['body'],'output':r['lead_draft']},ensure_ascii=False)+'\n' for r in records)


def approved_jsonl(records: list[dict], reviewer: str, rights_confirmed: bool) -> str:
    if not reviewer.strip():raise TrainingError('검수자 이름 또는 식별자를 입력해야 합니다.')
    if not rights_confirmed:raise TrainingError('자료 재사용·학습 권리를 확인해야 합니다.')
    if not records:raise TrainingError('검수 완료한 자료가 없습니다.')
    out=[]
    for row in records:
        if row.get('approved') is not True or not row.get('body_sha256') or not row.get('id'):
            raise TrainingError('승인 표시·근거 ID·본문 해시가 누락된 자료입니다.')
        body=clean_text(row.get('body',''))
        lead=clean_text(row.get('lead',''))
        if not MIN_LENGTH<=len(body)<=MAX_LENGTH or not lead or len(lead)>200:
            raise TrainingError('본문 또는 최종 리드 길이 검증 실패')
        if row.get('origin') not in ('SYNTHETIC_DEMO','USER_SUPPLIED_UNVERIFIED'):
            raise TrainingError('자료의 출처 종류가 잘못되었습니다.')
        if sha256(body.encode('utf-8')).hexdigest()!=row['body_sha256']:
            raise TrainingError('본문 수정됨: 해시 검증 실패')
        out.append(json.dumps({'instruction':INSTRUCTION,'input':body,'output':lead},ensure_ascii=False))
    return '\n'.join(out)+'\n'
