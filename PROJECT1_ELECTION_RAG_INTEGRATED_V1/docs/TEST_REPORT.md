# 프로젝트 1 검증 결과

| 실행 환경 | 검사 결과 | 범위 |
|---|---|---|
| NEWSROOM LAB V0.7 | 60 PASS | 기존 개표·수치·시계열·CSV·기사·검수·미디어 UI 구조 |
| STAT WORKBENCH V1.0 | 44 PASS | 17종 통계 계산·샘플·필터·가공·API |
| 프로젝트1 통합 | 17 PASS | 기존 URL/WebSocket/오류주입/검수/TF-IDF + 선거 전용 분석·방송 스튜디오 + 전체 흐름·업로드 데이터 분리·UI 구성요소 점검 |
| JavaScript 문법 검사 | PASS | 신규 화면, 복사한 통계툴, 기존 뉴스룸 |
| ASGI TestClient HTTP 테스트 | PASS | /, /project1, /workbench/, API, JS/CSS 제공 |
| 브라우저 표시 점검 | 구 V1.0 PASS(제한적), V1.1 실화면 미검증 | 신규 방송 스튜디오 코드는 Chromium 브라우저 실행 권한 때문에 육안 확인하지 못함. 정적 JS 구문·ASGI 자산/API는 통과 |
| 실제 Windows 11 실행 | 사용자 화면 표시·실행 보고 | 사용자 PC에서 전체 기능별 클릭·연결·재접속 확인은 별도 필요 |
| 실제 선거 원본/실시간 피드 | 미검증/미연결 | 교육용 자료만 자동 실행 |

**주의:** 121개 통과는 세 개로 분리 실행한 테스트의 합계로, 공식 데이터 정확성·실시간성·완성된 LangChain RAG를 입증하지 않습니다.

## 핵심 통합 시험
- `valid`: 수치/지역/근거 ID 일치 → 검수 사유 입력 후 **교육용** 승인
- `wrong_votes`: 표수를 17표 변경 → 409 승인 차단
- `wrong_region`: 지역 텍스트 치환 → 409 승인 차단
- `missing_id`: 인용 ID 제거 → 409 승인 차단
- `stale`: 개표 단계 증가 후 이전 스냅샷 기준 기사 승인 → 409 차단
- `transfer`: 최종 결과 샘플 204행 → 독립 Workbench 데이터셋 생성 → 그룹별 득표 집계 실행
- `tfidf`: 교육용 문서 검색 후 ID/발행자/유사도 반환, 근거 없으면 보류

## Windows에서 검증할 3가지
1. 설치·실행: `START_PROJECT1_WINDOWS.bat` → `http://127.0.0.1:8541/project1`.
2. 테스트: `CHECK_PROJECT1_TESTS.bat`; 기존 두 세트는 각각 `newsroom`·`workbench`에서 `python -m pytest tests -q`.
3. 화면 클릭: 모의 개표 업데이트 → 오류 기사 초안 → 승인 차단 → 통계툴 연결 → 그래프/표 출력.
