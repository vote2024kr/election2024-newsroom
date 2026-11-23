# 제22대 총선 뉴스룸 — PostgreSQL 연결판

## 실행 순서

1. 기존 `PROJECT1_ELECTION_RAG_정리본.zip`은 백업으로 남겨둡니다. 이 새 ZIP은 **다른 폴더**에 압축을 풉니다.
2. PC에 **PostgreSQL 19**가 설치되어 있고, 앞서 데이터 입력 도구가 `Election2024`의 `election_lab` 스키마에 자료를 저장했는지 확인합니다. 이미 성공했다면 데이터 입력 도구를 다시 실행하지 마세요.
3. 새 폴더의 **`RUN_POSTGRES_NEWSROOM.cmd`**를 더블클릭합니다. 최초 실행 시 Python 3.12 및 인터넷이 필요할 수 있습니다.
4. 데이터베이스 이름 `[Election2024]`, 서버 `[localhost]`, 포트 `[5432]`, 사용자 `[postgres]`에는 별도 변경이 없었다면 **Enter**를 누릅니다.
5. 설치 때 설정한 비밀번호를 입력하고 Enter를 누릅니다. 화면에는 글자·별표가 보이지 않는 것이 정상입니다.
6. 브라우저에서 `http://127.0.0.1:8541/project1?mode=real`을 엽니다. 기존 서버가 8541 포트를 사용한다면 먼저 **`뉴스룸_종료_한글.bat`**로 종료해야 합니다.

## PostgreSQL 작동 확인

브라우저 주소창에 다음 주소를 입력하세요.

- `http://127.0.0.1:8541/api/real/db-status`

`"backend": "PostgreSQL"`, `"active": true`, `"ok": true`이면 DB에서 읽고 있습니다. 건수는 지역구 254, 후보 693, 비례대표 253개 지역 집계, 지역별 정당 득표 9,614, 투표율 106입니다.

- `http://127.0.0.1:8541/api/real/health`: 기존 화면에 사용되는 최종 자료 건수 확인
- `http://127.0.0.1:8541/api/real/data`: 실제 데이터 API (`data_backend`가 PostgreSQL인지 확인)

## pgAdmin에서 직접 SQL 확인

`Election2024` → Query Tool에 아래 명령을 실행하세요.

```sql
SELECT region, district_name, winner_name, winner_party
FROM election_lab.district_results
WHERE district_name = '종로구';

SELECT metric_group, item, rate_percent, aggregation_basis
FROM election_lab.turnout_rates
WHERE metric_group = 'national';
```

## 유지된 항목과 변경된 항목

- **유지**: 기존 화면·한글 UI, 그래프, 2024 최종 개표자료, 투표율 표본/전수 구분, 원문 PDF, 모의 개표, 기사·검수 및 교육용 검색 기능.
- **변경**: `RUN_POSTGRES_NEWSROOM.cmd`로 실행하면 **실제 개표·투표율 데이터를 PostgreSQL `election_lab`의 SQL 테이블에서 읽습니다**. `source_documents` JSONB는 원본 구조·출처 정보의 기준이고, 개별 득표수와 투표율은 정규화된 테이블 조회값으로 갱신합니다.
- 원본 파일과 별도 기존 실행 방식(`뉴스룸_실행_한글.bat`)도 남겨뒀습니다. 기존 실행 방식에서는 여전히 파일을 읽습니다. **과제 제출·시연 시 반드시 PostgreSQL 전용 CMD를 실행하세요.**
- 비밀번호는 파일에 저장하지 않고 실행할 때마다 입력합니다. PostgreSQL 연결 실패 시 다른 자료로 몰래 대체하지 않고 오류를 표시합니다.
- `election_lab`의 DB를 기존 입력 도구로 초기 구축하는 것 외에는 이번 프로그램이 DB에 쓰거나 기존 테이블을 변경하지 않습니다.
- 기존 독립적인 모의 개표 및 통계 워크벤치 자료는 원래 방식을 보존했습니다. PostgreSQL 조회 대상은 2024 **실제 확정 개표·투표율** 데이터입니다.

## 검증·주의

개표·투표율 데이터는 2024년 **최종 집계**로, 실제 실시간 시간대별 개표 기록은 아닙니다. RAG는 생성형 AI가 아닌 근거 검색·규칙 기반 질의응답입니다. 본 수정본은 로컬 기능 테스트를 실행했지만 사용자의 Windows PostgreSQL에 실제로 연결해 보는 시험은 사용자가 수행해야 합니다.
