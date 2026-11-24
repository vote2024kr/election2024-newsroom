# AI·RAG 관련 산출물 현황 — 구현 사실과 확장 설계의 구분

## 1. 실제 보유
- `project1_app.py`의 기존 프로젝트1에는 **교육용 TF-IDF 희소 벡터 검색** 및 근거 문서 ID·발행자 반환 기능이 있다.
- `page=qa`는 기존 `/api/real/ask` 경로 등과 연계한 **근거 질문** 화면이다.
- `page=training`은 `press_sample_DEMO.html`, `press_raw_DEMO.csv`, `lead_draft_UNREVIEWED.jsonl` 등 기존 실습 자료를 제공한다.
- 실제 선거 자료는 PostgreSQL `election_lab` 및 별도 41개 시간 관측 기록으로 관리된다.

## 2. 현재 없거나 확인되지 않은 것
| 항목 | 정확한 상태 |
|---|---|
| 학습된 분류/생성 모델 `.pkl`·`.h5` | 학습·직렬화 실물 파일 확인되지 않음 |
| 모델 성능 평가 보고서 | 검증된 학습 모델의 정밀도·재현율·F1 등의 시험 결과 없음 |
| 운영 벡터 DB | Pinecone/FAISS/Chroma/Qdrant 등 별도 실제 배포 벡터 DB 증거 없음 |
| 별도 프롬프트 평가 | 훈련용 인용 근거·기사 문장 검증과 LLM 프롬프트 벤치마크는 동일하지 않음 |

## 3. 교육용 RAG 문서 구성
~~~mermaid
flowchart LR
 Q["사용자 질문"] --> SEARCH["교육용 TF-IDF 검색"]
 DOCUMENTS["기존 교육용 문서"] --> SEARCH
 SEARCH --> EVIDENCE["관련 문서·근거 ID"]
 EVIDENCE --> CHECK["기사 초안/검수 흐름"]
 CHECK --> HUMAN["사람의 수동 확인"]
~~~
현재 흐름은 **생성형 LLM RAG 모델 학습 완료**를 의미하지 않는다.

## 4. 벡터 DB 설계서가 요구될 때의 제안안 (미구현)
~~~text
documents(document_id, source_url, publisher, published_at, license)
chunks(chunk_id, document_id, text, offset_start, offset_end)
embeddings(chunk_id, model_id, dimension, vector)
retrieval_log(query_id, question, chunks, timestamp, citation_check)
~~~
이는 **향후 확장 가능 데이터 모델**이며 실제 SQL에 생성된 테이블이 아니다. 구현 전에는 원문 이용 권리·임베딩 모델·출처 검증·개인정보 보호·기사 승인 절차의 별도 결정을 받아야 한다.

## 5. 프롬프트 설계 원칙 (문서화, 적용 성과 주장 아님)
- 답변은 확인된 원문·URL·기준시각이 있는 자료를 우선한다.
- 인용 근거가 없으면 근거 없음으로 보고한다.
- 전국 실제/표본·선거일 표본/사전 전수조사 값을 혼합하지 않는다.
- 지역구별 과거 시각 중간 득표를 추정하지 않는다.
- 언론사 내부 검수·사람 승인 없이 실제 기사 자동 발행하지 않는다.

이 문서는 교육표의 AI 추가 산출물 목록을 **허위 완료 표시 없이 정리**하기 위한 자료이며 새로운 모델이나 DB를 생성하지 않는다.
