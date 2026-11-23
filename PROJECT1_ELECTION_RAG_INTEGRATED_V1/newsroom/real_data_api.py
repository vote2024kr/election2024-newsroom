"""Historical 2024 election analysis; strictly separate from fictional live simulator."""
from __future__ import annotations
from pathlib import Path
from functools import lru_cache
from collections import Counter
from newsroom import postgres_data
import json,re
from fastapi import HTTPException, Query
from fastapi.responses import FileResponse

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'real_data'
@lru_cache(maxsize=1)
def _local_vote_data():return json.loads((DATA/'election_2024.json').read_text('utf8'))
@lru_cache(maxsize=1)
def _local_turnout():return json.loads((DATA/'turnout_2024.json').read_text('utf8'))
def vote_data():
 return postgres_data.load_election() if postgres_data.active() else _local_vote_data()
def turnout():
 return postgres_data.load_turnout() if postgres_data.active() else _local_turnout()
@lru_cache(maxsize=1)
def pages():return json.loads((DATA/'turnout_pdf_pages.json').read_text('utf8'))

def bind(app):
 @app.get('/api/real/data')
 def real_data():
  d=vote_data()
  return {'data_mode':'FINAL_RESULTS_2024','election':d['meta'],'constituency':d['constituency'],
          'proportional':d['proportional'],'turnout':turnout(),
          'data_backend':'PostgreSQL' if postgres_data.active() else 'local_json'}

 @app.get('/api/real/db-status')
 def database_status():return postgres_data.db_status()

 @app.get('/api/real/health')
 def health():
  d=vote_data()
  return {'ok':len(d['constituency']['districts'])==254 and len(d['proportional']['areas'])==253,
          'regions':len(d['constituency']['regions']),'districts':len(d['constituency']['districts']),
          'pr_parties':len(d['proportional']['nation']['parties']),
          'pr_areas':len(d['proportional']['areas']),
          'data_backend':'PostgreSQL' if postgres_data.active() else 'local_json',
          'constituency_seats':d['constituency']['total_seats'],
          'proportional_seats':d['proportional']['seat_count']}

 @app.get('/api/real/turnout-report.pdf')
 def source_report():return FileResponse(DATA/'turnout_report_2024.pdf',media_type='application/pdf',filename='제22대_국회의원선거_투표율_분석.pdf')

 @app.get('/api/real/ask')
 def ask(q:str=Query(min_length=2,max_length=350),region:str='',district:str='',kind:str='auto'):
  """Deterministic grounded Q&A + ranked excerpts. Not a generative LLM/RAG."""
  question=q.strip(); d=vote_data(); t=turnout()
  ev=[]; answer=''; mode='자료 조회'; qplain=re.sub(r'\s+','',question)
  def cite_xlsx(sheet,row):return {'source':f'개표결과.xlsx / {sheet} 시트 / {row}행', 'type':'xlsx','file':'original_results.xlsx'}
  def cite_pdf(pg):return {'source':f'선관위 투표율 분석 · 인쇄 {pg}쪽','type':'pdf','url':'/api/real/turnout-report.pdf#page='+str(pg+8)}
  if '왜' in qplain and any(x in qplain for x in ('표본','본투표','선거일')):
   answer='보고서에는 선거일 투표의 표본 추출방법과 규모가 나와 있지만, 전수조사 대신 표본조사를 선택한 구체적 이유는 설명하지 않습니다. 중앙선관위 담당 부서에 별도 확인해야 합니다.';ev=[cite_pdf(4),cite_pdf(6)]
  elif ('표본' in qplain or '전수' in qplain) and any(x in qplain for x in ('사전','선거일','조사')):
   answer='전체 선거인 표본조사는 1,505개 투표구의 4,480,811명(10.1%)이며, 사전투표자 13,849,043명은 통합선거인명부를 이용한 전수조사입니다. 재외투표도 해당 명부를 이용한 전수조사입니다.';ev=[cite_pdf(4),cite_pdf(6)]
  elif '본투표' in qplain or '선거일' in qplain:
   answer='전체 투표자 중 선거일 투표자가 52.7%입니다(전체 투표자를 분모로 한 비중). 별도의 선거일 투표율 51.8%는 선거일 투표 대상 표본 선거인 3,039,100명을 기준으로 조사한 수치입니다. 두 수치는 분모가 다릅니다.';ev=[cite_pdf(22),cite_pdf(30),cite_pdf(4)]
  elif '사전' in qplain:
   answer='사전투표율은 전체 선거인 대비 31.3%이며, 실제 투표자 가운데 사전투표자의 비중은 46.7%입니다. 성별 사전투표율은 남성 33.2%, 여성 29.4%입니다. 사전투표 통계는 전수조사입니다.';ev=[cite_pdf(20),cite_pdf(35),cite_pdf(6)]
  elif '20대' in qplain and ('남' in qplain or '여' in qplain):
   answer='전체 선거인 표본조사에서 20대 후반 남성은 45.6%, 여성은 58.2%로 여성 투표율이 12.6%p 높았습니다. 이는 실제 후보 지지율을 뜻하지 않습니다.';ev=[cite_pdf(28)]
  elif any(x in qplain for x in ('연령','70대','60대','청년')):
   answer='전체 선거인 표본조사에서 20대 투표율은 52.4%로 가장 낮았고, 70대는 84.7%로 가장 높았습니다. 연령별 후보 지지 여부는 이 자료로 알 수 없습니다.';ev=[cite_pdf(23)]
  elif '성별' in qplain or ('남성' in qplain and '여성' in qplain):
   answer='전체 선거인 표본조사 결과 남성 투표율 66.5%, 여성 투표율 67.9%로 여성이 1.4%p 높았습니다. 반면 사전투표 전수조사는 남성 33.2%, 여성 29.4%였습니다.';ev=[cite_pdf(22),cite_pdf(35)]
  elif '비례' in qplain or '조국혁신당' in qplain or '국민의미래' in qplain or '더불어민주연합' in qplain:
   p=d['proportional']['nation']['parties']
   top=p[:4]
   answer='제22대 총선 비례대표 전국 유효표 기준: '+', '.join(f"{x['party']} {x['votes']:,}표({x['share']:.2f}%)" for x in top)+'. 비례대표 배분 의석: 국민의미래 18석, 더불어민주연합 14석, 조국혁신당 12석, 개혁신당 2석입니다.'
   ev=[cite_xlsx('비례대표',3),{'source':'제22대 총선 의석 집계 (선관위 제공 보도 자료)', 'url':'https://m.ohmynews.com/NWS_Web/Event/Elect/2024/counting.aspx'}]
  elif '의석' in qplain or '지역구' in qplain and '전국' in qplain:
   seats=d['constituency']['seats_by_party']; answer='지역구 254석 기준: '+', '.join(f'{k} {v}석' for k,v in sorted(seats.items(),key=lambda p:-p[1]))+'. 비례대표는 별도 46석입니다.'
   ev=[{'source':'개표결과.xlsx / 지역구 254개 선거구 합계행의 최다 득표자', 'type':'xlsx','file':'original_results.xlsx'}]
  else:
   target=None
   if district:target=next((x for x in d['constituency']['districts'] if x['district']==district and (not region or x['region']==region)),None)
   if not target:
    for x in d['constituency']['districts']:
     if x['district'] in question and (not region or x['region']==region):target=x;break
   if target:
    winner=target['winner'];answer=f"{target['region']} {target['district']}에서는 {winner['party']} {winner['name']} 후보가 {winner['votes']:,}표({winner['share']:.2f}%)를 얻어 1위를 기록했습니다. 유효투표 {target['valid']:,}표 기준입니다."
    ev=[cite_xlsx('지역구',target['excel_row'])]
   elif any(x in qplain for x in ('투표율','투표','전국')):
    answer='제22대 국회의원선거 최종 투표율은 67.0%입니다. 성별·연령별 전체 투표율은 1,505개 투표구를 대상으로 한 표본조사입니다.';ev=[cite_pdf(7),cite_pdf(4)]
  # If no exact answer, retrieve source passages; do not fabricate a result.
  if not answer:
   tokens=[x for x in re.findall(r'[가-힣A-Za-z0-9]{2,}',question) if x not in {'어떻게','알려줘','무엇인가요','했나요','그리고','있나요','어떤'}]
   scored=[]
   for pg in pages():
    txt=pg.get('text','')
    score=sum(min(4,txt.count(tok))*max(1,len(tok)//3) for tok in tokens)
    if score and pg['printed_page'] and pg['printed_page']>=3:
     segs=re.split(r'[\n\r]+',txt)
     matches=[s.strip() for s in segs if any(tok in s for tok in tokens)]
     excerpt=' '.join(matches[:3])[:350] if matches else txt[:350]
     scored.append((score,pg['printed_page'],excerpt))
   scored.sort(reverse=True)
   if scored:
    score,pg,excerpt=scored[0];answer='정확히 일치하는 수치 답변을 자동 확정하지 않았습니다. 관련 원문: '+excerpt;ev=[cite_pdf(pg)]
   else:
    answer='제공된 개표 데이터와 투표율 분석보고서에서 질문에 대응하는 직접 근거를 찾지 못했습니다. 질문 범위를 구체화하거나 공식 자료를 추가 확인해야 합니다.'
  return {'question':question,'answer':answer,'evidence':ev,'method':'원자료 수치 조회 + 규칙 기반 질의응답 / 키워드 원문 검색','limitations':'언어모델을 호출하는 생성형 RAG가 아닙니다. 사람의 기사 검증·승인을 대체하지 않습니다.'}
