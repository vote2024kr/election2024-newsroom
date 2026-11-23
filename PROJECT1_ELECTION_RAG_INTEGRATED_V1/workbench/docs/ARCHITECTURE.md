# 통합 통계툴 V1.0 — 기술 설계 및 코드 구조

## 목표
데이터의 종류와 관계없이 입력 형식과 필드 역할을 표준화하고, 통계기법마다 필요한 조건을 검사한 뒤 실행·시각화·표로 출력한다. 과거의 전용 시스템(NEWSROOM 선거방송, 통계기법 AI V1.2)은 원본 수정 없이 보관한다.

## 계층
- `app/catalog.py` **기법 사전**: ID, 분야, 이름, 필수 열, 차트 종류, 사용 시 주의.
- `app/engine.py` **데이터/통계 엔진**: CSV·Excel·JSON·JSONL 파일 파서, 컬럼 프로필, 열 기반 추천, 최대 4개 필터, 결측 정책, 가공 CSV 내보내기(중복제거/계산 열), 17개 분석 메서드, 공통 차트 JSON·결과 표.
- `app/server.py` **API/세션**: 인메모리 원본 테이블, 데이터셋 id, 필터·옵션 요청, 결과 이력 최대 20회. 실제 DB가 아님.
- `app/static/index.html|style.css|app.js` **UI**: 독립적인 기존과 다른 신규 UI. 기법선택→해당 변수만 표시→API 실행→SVG 차트·카드·근거표. CDN 불필요.
- `samples/` **모두 합성 데이터**, `legacy/` **기존 소스 변경 없는 보관본**.

## 데이터 흐름
1. 입력 파일 12MiB 제한, UTF-8/CP949 CSV 또는 XLSX/JSON/JSONL 판독.
2. 50,000행·120열 이내, 헤더 공백/중복 검사 및 컬럼 프로필 작성.
3. 데이터 분야 자동 감지 또는 선택, 기법 후보 우선순위 표시.
4. 사용자가 필수 열·집계법·결측 정책·조건 필터를 고름.
5. 데이터 프레임을 복사해 필터하고, 기법별 전제조건 검사(표본수·두 집단·중복·분모 등).
6. 실패 시 HTTP 422와 구체 오류. 성공하면 요약/차트(JSON)/결과표/출처 표시 반환.
7. 브라우저에서 SVG 차트 생성, 결과 CSV·JSON 다운로드, 이력 기록.

## 선거 분석의 특수 규칙
- `election_votes`, `election_margin`은 각 **선거구의 마지막 집계 단계**만 사용해 과거 단계 중복 합산을 방지.
- `election_progress`에서 `target_voters`는 후보마다 중복 저장되어도 선거구·단계당 한 번만 집계.
- 득표율(%), 후보 격차(%p), 집계표수/선거인수 비율(%)은 각각 다른 분자·분모/단위. 마지막 비율은 실제 개표율 또는 투표율이 아님.
- `candidate` 후보 필터가 분모를 축소할 수 있으므로 선거 기법에서는 차단.
- 샘플 `SIMULATION_ONLY`는 공식 선거 결과나 실시간 개표가 아니며, 다른 데이터도 원본 공식성은 서버가 검증하지 않음.

## API

| HTTP | 경로 | 목적 |
|---|---|---|
| GET | `/api/health` | 서버 가동 확인 |
| GET | `/api/catalog` | 분야·기법·제한 |
| GET | `/api/samples` | 샘플 목록 |
| POST | `/api/samples/{name}/load` | 샘플 로드 |
| POST | `/api/datasets/upload` | CSV·Excel·JSON 파일 업로드 |
| GET | `/api/datasets/{id}` | 메타/프로필 조회 |
| PATCH | `/api/datasets/{id}/kind` | 분야 변경 |
| POST | `/api/analyze` | 통계 계산 (원본 변경 없음) |
| GET | `/api/datasets/{id}/history` | 조건별 이력 |
| POST | `/api/transform/export` | 선택한 필터/중복/결측/계산 열로 **복사본 CSV** 만들기 |

요청 예시:

```json
{
  "dataset_id":"UI가 돌려준 데이터셋 ID",
  "method":"group_summary",
  "options":{"x":"amount","group":"region","aggregation":"sum"},
  "filters":[{"column":"category","op":"equals","value":"식품"}],
  "missing":"drop"
}
```

## 패키지 내 기존 소스 사용 전략
- 기존 두 프로젝트 ZIP은 SHA-256 해시와 함께 **보존**. 현재 통합툴은 선거 전용 화면/기사/승인 기능을 재구현하지 않음.
- 다음 단계: `adapters/`에 기존 뉴스룸 `/api/analytics`·통계기법 AI V1.2 `run_scenario` 변환기를 만들고, 전용 UI에는 기존 경로·스타일을 유지하도록 독립 서브앱 라우팅/포트 연결.
- GitHub 등록·외부 데이터 자동 크롤링·뉴스 영상/CG 제작은 하지 않음.
