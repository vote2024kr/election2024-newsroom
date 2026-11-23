# PROJECT 1 — Election Newsroom V1.1 Logic & UI QA

검토 기준: 첨부 `프로젝트_123_작업지시서_요약.pdf` 중 **프로젝트 1**, 기존 NEWSROOM LAB V0.7 및 통계 워크벤치 V1.0, 이전 작업 결정사항(기존 UI/기능 보존·GitHub 미등록·영상/CG 신규 제작 보류).

## 1. 핵심 처리 흐름 검토

| 단계 | 실제 코드/경로 | 검증 결과 | 한계 또는 다음 조치 |
|---|---|---|---|
| 교육용 개표 수집/갱신 | `newsroom/engine.py`, `/ws`, `/api/control` | PASS — 단계 증가·WebSocket 메시지 | 공식 실시간 API **미연결**, 화면에 모의 표시 |
| 전국/시도/선거구 화면 | `newsroom/static`, `/` | PASS — 원본 60개 회귀 검사 | 실제 공식 선거구 획정 정보 아님 |
| 최종 CSV 정제 | `newsroom/official_results.py`, `/api/official/import` | PASS — 출처 URL·원본 해시·중복키 검사 | URL 입력만으로 원본 진위 검증되지 않음; 영구 원본 저장 미구현 |
| 선거 전용 분석 | `/api/project1/election/methods`, `/analyze` | PASS — 10개 선별, 모의 4종/최종 6종 | 모의 스냅샷과 최종 CSV는 서로 다른 흐름 |
| 통계 17종 보존 | `/workbench/` | PASS — 44개 기존 회귀 검사 | 후보 필터 등 계산 분모 조건 유의 |
| 개별 후보 득표율 | `official_results.analyze` | PASS — 시도+선거구 없으면 422 | 다른 선거구 후보 집계 금지 |
| 집계표수 / 선거인 수 | `workbench/app/engine.py::election_progress` | **수정 완료** — '개표율' 명칭 삭제 | 이 수치는 실제 투표율·개표율이 아니며 보도 근거로 사용 불가 |
| 근거 검색 | `project1_sparse_retrieval.py` | PASS — 5개 데모 문서 검색/근거 ID | 생성형 RAG 또는 외부 공약 문서 검색 아님 |
| 기사 초안 | `newsroom/engine.py::draft_from_evidence` | PASS — 모의 개표 숫자 템플릿 | TF-IDF 문서 검색과 기사 문장별 근거 자동 연결 **미구현** |
| 숫자/지역/ID 검사 | `validate_draft`; `/api/project1/drill` | PASS — 오류 3종 주입 시 차단 | 템플릿 동일성 검사, 실제 외부 팩트체크 아님 |
| 오래된 기사 차단 | `/api/project1/approve` | PASS — 새 개표 단계 후 HTTP 409 | 기사 기준시각·원본 일치 추가 운영 검증 필요 |
| 사람 검수 | `/api/project1/approve` | PASS — 사유 입력·승인 기록 | 로그인·편집자 역할/권한 없음. 실제 기사 게시 불가 |
| SQLite 감사 | `project1_audit.py`, `data/project1_events.sqlite3` | PASS — 기사·차단·통계 실행 기록 | 기존 기사, 업로드 데이터, 다른 모듈 상태는 메모리 보관 |
| 화면 연결 | `/project1`, `/`, `/workbench/` | PASS — 3개 화면과 정적 자산 반환 | Windows 실제 브라우저 수동 검증 남음 |
| 프로젝트1 UI | `project1_ui/election_stats.css/.js` | 개선 — 통계 카드 확대, 여백·모바일·표 정돈 | Chromium 시각화는 실행 샌드박스 제한으로 미완료 |
| 교육용 방송상황실 | `project1_ui/broadcast_live.css/.js` | 추가 — 모의 실시간 후보표·그래프·시도·티커 | 기존 WebSocket 스냅샷 사용, 실제 방송/공식 개표 아님 |
| 신규 동영상/CG | 제작하지 않음 | 지시 준수 | 제출용 FHD 20분 영상은 별도 승인 후 |
| GitHub 등록 | 수행하지 않음 | 지시 준수 | 별도 승인 없이는 업로드하지 않음 |

## 2. 수정한 논리 오류

기존 워크벤치 `election_progress`는 `sum(votes) / target_voters × 100`을 **'개표율'**로 표시했다. 그러나 교육용 데이터의 `target_voters`는 **선거인 수**로 정의되어 있어 개표 대상 총 표수와 동일하지 않다. 이 수치는 실제 **개표율도 투표율도 아니다**.

V1.1에서는 코드를 삭제하지 않고 지표명을 **'선거인 대비 집계표 비율(%)'**로 변경하고, 차트·요약·기법 설명·테스트·예시 문서의 라벨을 일치시켰다. 진짜 투표율은 투표자 수와 선거인 수, 실제 개표율은 개표 완료 대상과 전체 개표 대상이 검증된 뒤 별도 기법으로 구현해야 한다.

## 3. UI 검토 및 변경 범위

- NEWSROOM 원본 `/`와 공통 WORKBENCH `/workbench/`의 기존 HTML·JS·CSS/상태/핵심 로직을 유지했다. 다만 잘못된 워크벤치 지표 이름과 관련 계산 결과의 라벨은 정확성 때문에 수정했다.
- 프로젝트1 `/project1`에만 분석 기법 선택/시도/선거구 필터/결과 그래프·표를 추가했다.
- 원래 `project1.css`는 그대로 두고 별도 `election_stats.css`, `election_stats.js`, `broadcast_live.css`, `broadcast_live.js`를 추가했다. `project1.js`는 기존 수신 기능을 바꾸지 않고 동일 스냅샷을 스튜디오로 전달하는 **이벤트 발행 한 줄**만 수정했다.
- 기존 6개 작업 카드 모두 보존. 통계 카드 폭을 넓히고, PC/태블릿/모바일 반응형 그리드, 대비, 폼·버튼·결과표 간격을 보완했다.
- 상단에 ON AIR 배지(교육용 모의 방송 고정 표시), 가상 후보 3명 득표 그래프, 시도별 집계, 방송형 하단 티커를 추가했다. 기존 2초 갱신 WebSocket을 재사용하므로 별도 공식 피드를 수집하지 않는다.
- JS 문법 검사 통과. 헤드리스 Chromium 화면 캡처는 현 실행 환경에서 브라우저 내부 소켓 생성 권한이 없어 실행 불가. 따라서 육안 화면 검수 완료로 표시하지 않는다.

## 4. ERD 읽는 방법

`ERD_ACTUAL_V11.png`: **지금 실제로 존재하는 데이터 저장 구조**. SQLite 물리 테이블은 `EVENT` 한 개뿐이다. 다른 박스는 메모리의 객체 또는 로컬 JSON·CSV이며, 점선 연결은 외래키가 아닌 논리 참조를 뜻한다.

`ERD_TARGET_V11.png`: **향후 구현 제안**. SOURCE/ELECTION/DISTRICT/CANDIDATE/SNAPSHOT/RAG_DOCUMENT/ARTICLE/VALIDATION/EDITOR_REVIEW/AUDIT 등은 아직 실제 DB에 생성된 테이블이 아니다. 이 ERD를 '구현 완료'로 주장하지 않는다.

`FLOW_LOGIC_V11.png`: 두 데이터 흐름(모의 WebSocket vs 최종 CSV)을 분리하고, 문서 검색·초안·검증·승인과 미구현 RAG 경계를 표시한다.

## 5. 테스트 결과 및 재현

| 테스트 | 기존 V1.0 | V1.1 확인 |
|---|---:|---:|
| NEWSROOM LAB | 60 | **60 PASS** |
| STAT WORKBENCH | 44 | **44 PASS** (기존 선거인 대비 비율 라벨 시험 갱신) |
| PROJECT 1 통합 | 9 | **17 PASS** (선거 기법 선택·스튜디오 + WebSocket→기사→승인→감사 E2E, 업로드/모의 분리, 화면 자산 3개 추가 검증) |
| 합계 | 113 | **121 PASS** |

Windows 11에서 `START_PROJECT1_WINDOWS.bat` 실행 → `http://127.0.0.1:8541/project1` → 02 통계 단계에서 모의 후보 누적 변화 선택 → 계산 → 최종 CSV 선택 시 시도+선거구 지정 후 후보 득표율 계산 → 04 카오스 오류 주입 → 05 승인 차단 → 06 감사 이력 확인.

### 미완료/고위험 기능

1. **공식 실시간 선거 데이터와 원본 교차검증**: 제공기관 이용조건, 권한, 게시일, 갱신시각 및 원장 설계 필요.
2. **문서 기반 생성형 RAG**: 출처문서 수집, 청크 ID, 문장별 인용과 수치 검증 연결 구현 필요. TF-IDF 검색만 RAG 완료로 표시하면 안 된다.
3. **편집자 인증·역할 기반 승인/정정**: 현재 개인명 텍스트 입력은 신원 확인이 아니다.
4. **원본 데이터와 기사/승인 이력의 영구 보존**: 현재 이벤트 SQLite 한 테이블만 지속적이다.
5. **최종 영상/FHD 방송**: 이전 사용자 요청에 따라 제작 보류.

### 최종 판단

**교육용 로컬 통합 시연 V1.1 준비 완료(자동 테스트 기준).** 사용자가 Windows 화면 표시와 실행을 보고했지만 전체 기능별 수동 승인 시험은 남아 있다. 정식 선거 보도 서비스 또는 공식 선거 수치 검증 시스템으로 승인된 상태는 아니다. 브라우저 화면별 수동 검증·공식 원본 교차검증 후 별도 확정해야 한다.
