# 2024년 제22대 국회의원선거 데이터 상황실

**웹사이트 최종 확정: 2026-11-24** · GitHub 프로젝트: [PROJECT1_ELECTION_RAG_INTEGRATED_V1](PROJECT1_ELECTION_RAG_INTEGRATED_V1/)

2024년 당시 확인된 전국 시간별 투표·개표 기록과 중앙선거관리위원회 최종 선거 결과를 구분하여 시각화하는 **데이터 저널리즘 교육용 웹사이트**입니다. **선관위 실시간 개표 서버와 연결된 서비스가 아닙니다.**

## 빠른 시작
1. [프로젝트의 현재 README](PROJECT1_ELECTION_RAG_INTEGRATED_V1/README.md) 읽기
2. [산출물 한눈에 보기](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_산출물_목록_최종.md)에서 기획·설계·구현·테스트·발표 자료 확인
3. [최종 화면 구성도](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_화면설계서_20261124.md)와 [사용자 매뉴얼](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_사용자매뉴얼_최종.md) 확인
4. 프로젝트 폴더의 기존 `RUN_POSTGRES_NEWSROOM.cmd` 실행(`Election2024` PostgreSQL 환경이 준비돼 있어야 함). 디자인만 보려면 기존 검토용 실행기/HTML 이용

## 현재 최종 화면
| 메뉴 | 핵심 특징 |
|---|---|
| 2024 투·개표 상황 | **41개 과거 확인 시점**, 5/10/15초 재생, 13시 사전투표 포함 화살표, 최종 결과 공개 |
| 전국 확정 개표 | 전국 지도·지역구 **254석**·비례 **46석**·국회 **300석** 시각화 |
| 지역·선거구 탐색 | 확대된 전국/선택 지역 지도/후보 결과 **상단 3열**, 시도/시군 목록 **하단 2열** |
| 투표율·개표·비례 | 공식 최종·표본·전수조사 값을 구분하여 분석 |
| 미디어 | **정적 데이터 CG 6종**. 시연 MP4는 별도 제작 대상 |

### 자료 해석 원칙
전국 **실제 최종 67.0%**, 표본조사 **67.2%**, 사전투표 **31.3%**, 선거일 대상 표본 **51.8%**를 혼용하지 않습니다. 2024-04-11 **10:25**는 당시 보도에 근거한 사이트 재현용 완료시각입니다.

## 문서
[기획서](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_기획서_20261124.md) · [요구사항](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_요구사항정의서_20261124.md) · [WBS](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_WBS_20261124.md) · [기능정의](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_기능정의서_20261124.md) · [ERD/데이터 사전](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_ERD_데이터사전_20261124.md) · [API](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_API_명세서_20261124.md) · [아키텍처](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_시스템아키텍처_20261124.md) · [검증기록](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_검증기록_20261124.md) · [최종보고서](PROJECT1_ELECTION_RAG_INTEGRATED_V1/docs/V5_최종보고서_20261124.md)

**웹 최종 승인과 제출용 PPT·MP4 파일의 제작 완료는 별개입니다.** 현재 슬라이드 원고와 영상 스토리보드가 문서로 제공되며 실제 완제품 파일의 등록은 확인되지 않았습니다.

기존 교육용 NEWSROOM LAB 모의 개표·프로젝트1 TF-IDF 근거 검색·STAT WORKBENCH 코드는 보존됩니다.
