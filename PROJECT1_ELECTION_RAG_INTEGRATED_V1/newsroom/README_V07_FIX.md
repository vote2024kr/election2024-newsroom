# NEWSROOM LAB · ELECTION CONTROL CENTER V0.7 — 통계 화면 오류 수정본

## 이번 버전에서 고친 부분
- `static/app.js`에 없던 **통계 조건 선택 → `/api/analytics` 호출 → 그래프·요약 카드·원본 계산 표 렌더링**을 연결했습니다.
- `static/style.css`에 빠진 `.stat-*` 레이아웃과 반응형 스타일을 추가했습니다.
- 모의 개표 WebSocket 업데이트를 수신하면 현재 통계 조건으로 자동 재집계합니다. 업데이트 충돌 시 최근 요청만 화면에 반영합니다.
- 전국/시·도/선거구 변경 시 해당 선택값을 점검해 잘못된 범위·조합을 방지합니다.
- 8종 모두 막대·추이선·산점도로 표시합니다. 서버가 결과가 없거나 API 오류를 반환하면 빈 화면이 아닌 원인을 안내합니다.
- 1회 초기화 직후에 `단계별 추가 집계량`은 자료가 1단계만 있어 계산할 수 없습니다. `↻ 1단계 진행`으로 두 단계를 확보한 뒤 표시합니다.
- 계산 결과를 다운로드하는 CSV 버튼은 현재 조건을 반영합니다.
- 기존 V0.6의 선거·RAG·검증·승인·공식 결과 CSV·보도자료 학습·기존 사진 영역은 삭제·변경하지 않았습니다. **동영상·CG 신규 제작 없음. GitHub 미등록.**

## Windows 11 실행
1. ZIP을 다운로드하고 압축 풀기. 예: `C:\workspace\NEWSROOM_LAB_ELECTION_V07`
2. 해당 폴더의 `START_NEWSROOM_LAB_V07.bat` 더블클릭.
3. 자동으로 열리지 않으면 브라우저에서 **http://127.0.0.1:8512/** 열기.
4. 사이드바 **통계 · 그래프** → **분석 범위/기법 선택** → **조건 재계산**. 2초마다 WebSocket 업데이트 시 갱신.
5. 운영 종료: 시작된 서버 명령창에서 `Ctrl+C`.

`Python 3.12`가 설치되어 있어야 합니다. 실행기가 `.venv`와 `tzdata` 등 패키지를 설치합니다. 기존 다른 폴더의 `.venv`는 사용하지 않습니다.

### Windows 수동 실행
```powershell
cd C:\workspace\NEWSROOM_LAB_ELECTION_V07
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PORT = '8512'
.\.venv\Scripts\python.exe server.py
```

### 테스트
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 검증 상태 및 한계
- 이번 빌드에서 Python 테스트 **60/60 통과**, Node 구문 검사 통과.
- 브라우저 DOM 실행: 서버 TestClient가 만든 **실제 분석 API JSON을 브라우저의 가짜 네트워크 계층에 넣어** 8개 차트, 표, 요약 카드, 범위 변경 동작을 검사. JS 예외 0건.
- **실제 Chrome의 `http://127.0.0.1` 접속·Windows 사용자 PC 클릭 검증은 이 도구 환경의 보안 차단으로 미검증**. 실기기에서 최종 확인 필요.
- 기존 메모리 이력은 최대 121개 스냅샷이고 재시작 시 초기화됩니다. 데이터베이스는 아직 없습니다.
- `SIMULATION_ONLY`는 17개 시·도/254개 가상 선거구의 **교육용 난수 자료**입니다. 공식 데이터 또는 예측이 아닙니다.
- 별도 공식 결과 CSV 모듈은 `USER_UPLOADED_FINAL_RESULT` 모드이며 사용자가 올린 자료를 공식 원본과 독립 검증하지 않습니다. 실제 개표 생중계 API는 아닙니다.
- 보도자료 학습 모듈은 외부 자동 크롤링이나 AI 파인튜닝을 하지 않습니다.
- 현행 사이트에 있는 기존 방송 CG·사진 영역은 유지했으나 신규 영상·CG는 제작하지 않았습니다.

## 설계 문서
- [데이터 흐름과 로직 점검](docs/LOGIC_AND_QA_V07.md)
- [현재 메모리 구조·향후 DB 설계 ERD](docs/ERD_AND_SCHEMA_V07.md)
- [ERD 이미지](docs/ERD_PROPOSED_V07.png)
- [처리 흐름 이미지](docs/DATA_FLOW_V07.png)
- [기법별 체크 표](docs/ANALYTICS_METHOD_CHECK_V07.csv)
- [검증 화면](docs/ANALYTICS_RENDER_VERIFICATION.png) (가상 전송, 실제 사용자 PC 실행 화면 아님)
