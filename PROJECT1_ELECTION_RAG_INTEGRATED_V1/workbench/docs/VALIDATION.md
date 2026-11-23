# QA 검증 기록 — 2026-11-13

## 검증 기준
- 17개 기법별 샘플에서 모두 실수치 계산·표·차트 JSON 반환.
- 정상/비정상 필터, 필수 열, 데이터 크기·중복 헤더·선거 중복 집계 확인. 별도 가공 CSV의 계산 열/원본 불변/엑셀 수식 삽입 위험 차단 확인.
- FastAPI `TestClient`로 업로드·메타·조건 변경·계산·오류 코드 검증.
- Chromium 화면은 로컬 네트워크 차단으로 `http://127.0.0.1`에 직접 접속하지 못했음. 실제 서버의 `TestClient` 분석 응답 JSON을 브라우저 가상 `fetch`로 전달해 JS 실행/차트 렌더링 확인.

## 자동 테스트
`python -m pytest -q` 실행 결과 **44개 테스트 통과**. 테스트 코드: `tests/test_engine.py`, `tests/test_api.py`.

## 브라우저 렌더링 확인
- 처음 열기: `sample_election.csv` 자동 선택, `election_votes` 막대그래프 3개·요약카드·결과표 생성.
- 샘플 변경: `sample_air.csv` 선택, X=pm10/Y=pm25, Pearson/Spearman 산점도 280개 원본점 표시(렌더 한도 내), 표 생성, JavaScript 예외 0.
- 검증 화면: `output/BROWSER_RENDER_01_ELECTION.png`, `output/BROWSER_RENDER_02_CORRELATION.png`.
- **검증 방법은 브라우저의 네트워크를 가상화한 것으로, 실제 Windows PC 접속/E2E 검증과 다름.**

## 경고와 제한
- PC 실제 실행의 SmartScreen/방화벽/포트 점유, Windows Python 3.12 실제 설치와 UI 클릭 검사는 사용자 PC에서 필요.
- 서버 종료 시 업로드한 원본은 사라지며 이력도 지워짐. 외부 공개 금지.
- HTML 그래프 레이아웃은 CPU/브라우저와 해상도에 따라 달라질 수 있음.
- 선거 모의 자료는 교육용이며 진짜 투표/당선 확률이 아님. 공식 결과 데이터 업로드만으로 출처 진위를 자동 확인하지 못함.
- Welch/카이제곱/상관/회귀 등 통계 해석은 표본 설계·독립성·다중검정 검토가 필요.
