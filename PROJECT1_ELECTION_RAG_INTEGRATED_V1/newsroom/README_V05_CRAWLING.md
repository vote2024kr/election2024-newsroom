# 선거 데이터 분석 사이트 V0.5 — 보도자료 수집·정제·학습데이터 샘플

**개발 상태:** 기존 V0.4 기능 모두 보존 + 별도 `보도자료 · 학습데이터` 메뉴 추가. **GitHub 미등록 / 동영상·CG 신규 제작 없음**.

## 첨부 교재에 따라 추가한 흐름

`파일/API 먼저 찾기 → (허용된 경우) 크롤링 → 제목·본문 추출 → 공백·중복·길이 정제 → 리드 초안 → 사람이 수정·검수 → JSONL 내보내기`

- 웹 크롤링은 **지금 실행하지 않음**. 파일만 사용하며 HTML에서 `article.press-item`, `.press-title`, `.press-body` 구조를 로컬로 파싱함. 다른 기관 사이트에 그대로 적용되는 일반 수집기는 아님.
- `training_pipeline.py`: 정제 (200~2,500자), 중복 제거, `SHA-256` 검산, 출처/기관 필수 조건, 기사 리드 규칙 기반 임시 초안, 검수 게이트, JSONL 생성.
- `build_samples.py`: 수업용 가상 선거보도자료 12건 생성. **10건 통과 / 중복 1건·짧은 본문 1건 제외**.
- `samples/crawling_training`: 원본 CSV, 연습 HTML, 정제 CSV, 미검수 초안 CSV, 미검수 Alpaca JSONL, 제외 이유, 품질요약, 권리 장부.
- `static/training.js`: 로컬 CSV/HTML 읽기 → 검수 전 요약·표 → 미검수 CSV/JSONL 다운로드 → 담당자가 수정/확인한 건만 별도 JSONL 다운로드.

## VS Code 로컬 실행

ZIP을 `C:\workspace` 폴더에서 압축 해제하여 `C:\workspace\election_site_v05_crawling` 폴더를 엽니다.

```powershell
cd C:\workspace\election_site_v05_crawling
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py
```

브라우저 `http://127.0.0.1:8502` → 왼쪽 **보도자료 · 학습데이터** → **교육용 샘플 12건 불러오기**. 저장 버튼들은 실제 파일을 브라우저 다운로드로 내보냅니다.

실습 샘플을 재생성하려면:

```powershell
.\.venv\Scripts\python.exe build_samples.py
.\.venv\Scripts\python.exe -m pytest -q
```

## 실제 기관 보도자료 연결 원칙

1. 공식 CSV 다운로드 또는 Open API 우선, 없을 때만 수집 허용 여부 확인 후 크롤링 검토.
2. 사이트별 robots.txt·약관·공공누리 표시·개인정보 처리·재학습 권리 확인.
3. 파일에 `제목`, `본문`, `출처URL`, `기관`, `게시일` 입력. 게시일 없으면 사람이 보완해도 되지만 뉴스로 출고할 때는 검증 필수.
4. 출처 URL이 HTTPS 형식이라는 검사는 **링크의 진실성 검증이 아님**. 원문 수치·사실은 사람이 대조해야 함.
5. 웹 UI는 인터넷에서 자료를 긁어오지 않음. 나중에 승인된 공식 API 어댑터만 별도 개발.
6. `lead_draft_UNREVIEWED.jsonl`은 형식 연습 샘플이며 실제 미세조정 학습에 사용하지 말 것.
7. 실제 교육자료 목표 **100쌍 이상**은 교재의 목표. 현재는 **10개 미검수 초안**이며 목표 달성 아님.

## 기존 선거통계 시스템과의 구분

| 영역 | 자료 | 계산·기능 | 상태 |
|---|---|---|---|
| 모의 개표 시뮬레이터 | 난수 254개 가상 선거구 | WebSocket 그래프·표 | 기존 보존 |
| 공식 결과 CSV 분석실 | 사용자 입력 선관위 결과 CSV | 지역·선거구별 6종 통계 | 기존 보존, 원본 검산 별도 |
| 새 보도자료·학습자료실 | HTML/CSV 텍스트 | 본문 정제·리드 초안·검수 JSONL | V0.5 추가 |

**검증:** 오프라인 단위/API 테스트 49개 통과. Playwright 코드 호출 시 브라우저 바이너리 부재로 실제 클릭·렌더링 시연은 미완료. 사용자 Windows 환경 별도 확인 필요.

**AI 투명성:** 현재 초안은 GPT 모델 출력이 아니라 `규칙 기반`이고, 실제 크롤링, 파인튜닝, 공식 선거 데이터 수집은 수행하지 않았습니다.
