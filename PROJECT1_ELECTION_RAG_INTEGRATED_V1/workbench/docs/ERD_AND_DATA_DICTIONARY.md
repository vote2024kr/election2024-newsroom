# 데이터 관계 설계 (ERD) 및 현재 상태

**현재 V1.0은 DB를 쓰지 않습니다.** 아래는 SQLite/PostgreSQL의 영속 저장 및 RAG/뉴스 검수 연계를 위한 **제안 ERD**입니다. 동작 중 데이터는 서버 프로세스의 메모리에만 있고 재시작하면 초기화됩니다.

```mermaid
erDiagram
    SOURCE_REGISTER ||--o{ DATASET : provides
    DATASET ||--o{ DATA_COLUMN : contains
    DATASET ||--o{ ANALYSIS_RUN : analyzed_by
    STAT_METHOD ||--o{ ANALYSIS_RUN : executes
    ANALYSIS_RUN ||--o{ FILTER_CONDITION : has
    ANALYSIS_RUN ||--o{ RESULT_TABLE : produces
    ANALYSIS_RUN ||--o{ SCENARIO_HISTORY : records
    DATASET ||--o{ ELECTION_STAGE : optionally_contains
    SOURCE_REGISTER { string source_id PK string file_name string source_url string publisher string license_note boolean verified_flag }
    DATASET { string dataset_id PK string source_id FK string kind int row_count datetime created_at }
    DATA_COLUMN { string column_id PK string dataset_id FK string column_name string inferred_type int missing_count }
    STAT_METHOD { string method_id PK string category string requirements string caveat }
    ANALYSIS_RUN { string run_id PK string dataset_id FK string method_id FK string options_json string status datetime started_at }
    FILTER_CONDITION { string filter_id PK string run_id FK string column_name string operator string value }
    RESULT_TABLE { string result_id PK string run_id FK string summary_json string chart_json string result_rows_json }
    SCENARIO_HISTORY { string scenario_id PK string run_id FK string scenario_name }
    ELECTION_STAGE { string stage_id PK string dataset_id FK string district_code string candidate_id int step int votes }
```

## 핵심 원칙
1. 업로드 원본과 정제 데이터는 분리 저장한다. 버전/체크섬 기록을 도입한다.
2. `ANALYSIS_RUN`의 실행 조건/기법 버전/결과 생성시각을 기록하면 그래프와 표를 재현할 수 있다.
3. 선거는 후보·지역·선거구·단계의 고유 키를 정하고 **정당별/후보별 표와 집계 항목을 분리**해야 한다.
4. 기사/RAG/팩트체크/사람 승인은 `EVIDENCE`, `ARTICLE`, `APPROVAL_AUDIT`를 별도 테이블로 만들되 현재 MVP에서는 미연동.
5. 권한 관리/인증·개인정보 비식별화·영속 로그 백업 후에만 외부 공개를 검토한다.

## 현행 메모리 키
- `DATASETS[dataset_id]` → `{name,kind,source,source_url,origin,at,df,history}`
- `df`는 사용자 업로드 원본을 읽은 `pandas.DataFrame`; 계산 엔진은 복사본을 이용.
- `history[]`는 최근 20회 기법명·필터·옵션·요약·시각; 원본 데이터 자체는 포함하지 않음.
