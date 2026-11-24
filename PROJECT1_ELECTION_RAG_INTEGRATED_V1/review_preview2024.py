"""격리된 검토용 미리보기. 실제 PostgreSQL에 접근하거나 어떤 기록도 저장하지 않습니다.

실제 운영·취재 시에는 반드시 RUN_POSTGRES_NEWSROOM.cmd로 실행하십시오.
여기는 CSV/JSON 참고 자료가 들어 있는 기존 프로젝트 파일을 읽기 전용으로 사용합니다.
"""
from __future__ import annotations
from fastapi import FastAPI
import newsroom_safe2024 as safe
from newsroom import real_data_api as real
from newsroom_replay2024 import _validated_rows

app=FastAPI(title='V5 개편 검토용 - 운영 DB 아님')
from fastapi.staticfiles import StaticFiles
from pathlib import Path
app.mount('/static', StaticFiles(directory=str(Path(__file__).resolve().parent/'newsroom'/'static')), name='static')

# These overrides exist ONLY in this process and are not persisted to repository.
safe.postgres_data.active=lambda: True
safe.get_data=lambda:(real._local_vote_data(),real._local_turnout())

def replay_readonly(index):
    rows=_validated_rows()
    if index<0 or index>=len(rows):
        from fastapi import HTTPException
        raise HTTPException(404,'기록되지 않은 시점')
    return rows[index]
safe.pg_replay_observation=replay_readonly
_original=safe.layout
def _layout(*args,**kwargs):
    html=_original(*args,**kwargs)
    html=html.replace('PostgreSQL DB 조회 성공','검토용 로컬 자료 (실DB 미연결)')
    html=html.replace('중앙선거관리위원회 제22대 국회의원선거 최종 집계 · PostgreSQL election_lab 테이블 사용',
         '검토용 · 번들에 포함된 선관위 최종 결과 사본 · 운영 검증은 PostgreSQL 별도 연결 필요')
    html=html.replace('</header>','<div style="position:fixed;top:0;left:35%;z-index:99999;background:#f6bd55;color:#173144;font-size:12px;font-weight:bold;padding:5px 12px;border-radius:0 0 8px 8px">로컬 디자인 검토용 · 실제 PostgreSQL 조회 아님</div></header>')
    return html
safe.layout=_layout
safe.bind_safe(app)
