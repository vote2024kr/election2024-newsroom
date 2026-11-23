"""PostgreSQL-only classroom launcher. Credentials are never saved to disk."""
from __future__ import annotations

import os
import runpy
import sys
from getpass import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def prompt(label, default):
    return input(f'{label} [{default}]: ').strip() or default


def main():
    # Keep Korean console text legible in Windows CMD when supported.
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    print('NEWSROOM LAB / PostgreSQL (2024)')
    print('기존 자료는 변경하지 않습니다. 비밀번호는 저장되지 않습니다.')
    dbname = prompt('데이터베이스 이름', 'Election2024')
    host = prompt('서버 주소', 'localhost')
    port = prompt('포트', '5432')
    user = prompt('사용자', 'postgres')
    password = getpass('PostgreSQL 비밀번호 (화면에 표시되지 않습니다): ')

    try:
        import psycopg
        with psycopg.connect(host=host, port=port, dbname=dbname, user=user,
                             password=password, connect_timeout=7,
                             options='-c statement_timeout=12000') as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT count(*) FROM election_lab.district_results')
                districts = cur.fetchone()[0]
                cur.execute('SELECT count(*) FROM election_lab.turnout_rates')
                turnout = cur.fetchone()[0]
                cur.execute('SELECT count(*) FROM election_lab.source_documents')
                originals = cur.fetchone()[0]
        if (districts, turnout, originals) != (254, 106, 2):
            print(f'자료 불일치: 지역구 {districts}, 투표율 {turnout}, 원본 {originals}')
            print('데이터 입력 도구를 먼저 실행해서 자료가 완성되었는지 확인하세요.')
            return 2
    except Exception as exc:
        print('DB 연결/검증 실패: PostgreSQL이 실행 중인지, 접속 정보가 맞는지 확인하세요.')
        print('진단 유형:', type(exc).__name__)
        return 1

    try:
        from newsroom_replay2024 import seed_postgres
        count = seed_postgres(host, port, dbname, user, password)
        print(f'과거 시간별 기록 PostgreSQL 확인 완료: {count}개 시점')
    except Exception as exc:
        print('시간별 재생 DB 준비 실패: ', type(exc).__name__)
        print('기존 선거 결과 데이터는 변경되지 않았습니다.')
        return 4

    print(f'연결 확인: DB={dbname} / 지역구 {districts}개 / 투표율 {turnout}개')
    print('이제 개표·투표율은 PostgreSQL에서 조회합니다. JSON 자동 대체 없음.')
    os.environ.update({'NEWSROOM_DATA_SOURCE':'postgres',
                       'NEWSROOM_PG_DB':dbname,'NEWSROOM_PG_HOST':host,
                       'NEWSROOM_PG_PORT':port,'NEWSROOM_PG_USER':user,
                       'NEWSROOM_PG_PASSWORD':password})
    password = None
    # Existing launcher starts the *unchanged* FastAPI app in the existing venv.
    runpy.run_path(str(ROOT/'newsroom_launch.py'), run_name='__main__')
    return 0


if __name__ == '__main__':
    sys.exit(main())
