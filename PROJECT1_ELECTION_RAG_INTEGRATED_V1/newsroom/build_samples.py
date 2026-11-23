"""Rebuild explicitly fictional press releases and an unapproved training exercise."""
from pathlib import Path
from datetime import date
import csv, json
from html import escape
from training_pipeline import preview_content,to_csv,draft_jsonl
ROOT=Path(__file__).parent
OUT=ROOT/'samples'/'crawling_training'
OUT.mkdir(parents=True,exist_ok=True)
TOPICS=[
('모의 개표 데이터 화면 기준 정리','교육용 시각화 화면에서는 전국·시도·선거구의 표시 범위와 기준 단계를 구분한다.','수치 변화는 사전에 생성한 모의 데이터로만 재생하고 실제 개표 정보인 것처럼 표현하지 않는다.'),
('지역명 표준화 연습','교육용 자료는 지역명이 서로 다르게 적힌 경우 원본 필드를 보존한 채 표준 이름을 별도 열에 기록한다.','같은 이름처럼 보여도 선거구 획정 시기와 지역 코드가 다르면 단순히 합산하지 않는다.'),
('기사 속 득표수 검증 절차','교육용 기사 초안에 표수와 득표율을 넣기 전에 사용한 데이터 행과 계산식을 먼저 확인하도록 정했다.','근거 표의 기준 단계와 초안의 기준 단계가 다르면 자동 승인을 막고 편집자에게 검토를 요청한다.'),
('선거 통계 그래프 표시 원칙','교육용 차트는 전체 선거구의 득표 합계와 개별 지역구의 후보별 득표율을 같은 지표로 혼동하지 않도록 표시한다.','득표율·투표율·개표율은 각각 분모가 다른 지표이므로 원자료에 없는 값은 산출하지 않는다.'),
('가상 개표 갱신 재현','교육용 웹사이트는 동일 난수 시드와 단계 번호를 이용해 시연 환경에서 같은 결과를 재현하도록 구성한다.','화면에는 모의 개표라는 표지를 항상 나타내고 실제 선거관리기관 API와 연결되지 않았음을 밝힌다.'),
('원본 선거 CSV 보존 지침','선거 결과 CSV를 불러올 때는 파일 해시와 출처 URL, 이용자가 제공한 선거명을 메타데이터로 따로 기록한다.','출처 주소를 입력했다는 사실만으로 해당 CSV가 기관에서 발행한 원본임이 증명되는 것은 아니다.'),
('표본과 모집단의 구별','교육용 개표 결과의 일부 선거구만 골라 계산하면 전체 결과와 다른 분포가 나올 수 있음을 실습한다.','표본 선정 과정이 확률적으로 설계되지 않았다면 선거 예측의 오차범위처럼 표현해서는 안 된다.'),
('방송 기사 승인 기록','교육용 뉴스룸에서는 초안 생성자와 최종 확인자를 구분하고 수정 사유와 시각을 남기도록 운영 규칙을 세운다.','숫자나 지역 이름이 근거와 다르면 승인 대기로 전환하고 정정한 뒤 다시 확인하도록 한다.'),
('교육용 개인정보 수집 제한','교육용 개표 화면은 개인 유권자 이름이나 연락처를 필요로 하지 않으며 공개 통계와 가상 데이터를 중심으로 작동한다.','웹 자료를 자동 수집할 때도 로그인 자료나 비공개 개인정보는 수집 대상에서 명시적으로 제외한다.'),
('보도자료 수집 권한 확인','공식 기관 자료를 웹에서 가져오기 전 CSV 다운로드와 Open API를 먼저 찾고 허용된 접근 방식인지 점검한다.','크롤링이 필요할 때는 robots.txt와 이용약관, 자료 이용 조건을 확인한 뒤 낮은 요청 속도로 진행한다.'),
]
rows=[]
for i,(title,first,second) in enumerate(TOPICS,1):
    body=(first+' '+second+' '+'이 내용은 기자와 개발자가 숫자, 지역, 출처, 시각을 구별하는 과정을 연습하도록 만든 가상의 수업 문장이다. '*2+
          '실제 선거 현장 발언이나 중앙선거관리위원회 발표가 아니다. 독립적인 외부 검증 없이 기사에 인용해서는 안 된다.')
    rows.append({'제목':title,'본문':body,'출처URL':f'local-demo://press-{i:02d}',
                 '기관':'교육용 모의 뉴스룸','게시일':f'2026-11-{(i%10)+1:02d}'})
# Deliberate duplicate + short sample used by exclusion tests.
rows += [dict(rows[2]),{'제목':'제외되는 짧은 문장','본문':'이 문장은 200자 미만이므로 제외된다.','출처URL':'local-demo://short', '기관':'교육용 모의 뉴스룸','게시일':'2026-11-12'}]
with (OUT/'press_raw_DEMO.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (OUT/'press_sample_DEMO.html').open('w',encoding='utf-8') as f:
    f.write('<!doctype html><html lang="ko"><meta charset="utf-8"><title>교육용 합성 보도자료</title><body>\n')
    for row in rows:
        f.write(f'<article class="press-item" data-source="{escape(row["출처URL"])}" data-publisher="{escape(row["기관"])}" data-date="{escape(row["게시일"])}"><h2 class="press-title">{escape(row["제목"])}</h2><div class="press-body">{escape(row["본문"])}</div></article>\n')
    f.write('</body></html>')
text=(OUT/'press_raw_DEMO.csv').read_text(encoding='utf-8-sig')
result=preview_content(text,synthetic=True)
(OUT/'press_clean_DEMO.csv').write_text(to_csv(result['records']),encoding='utf-8-sig')
(OUT/'pairs_draft_UNREVIEWED.csv').write_text(to_csv(result['records']),encoding='utf-8-sig')
(OUT/'lead_draft_UNREVIEWED.jsonl').write_text(draft_jsonl(result['records']),encoding='utf-8')
(OUT/'exclusions_DEMO.json').write_text(json.dumps(result['excluded'],ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'summary_DEMO.json').write_text(json.dumps({k:v for k,v in result.items() if k not in ('records','excluded')},ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'RIGHTS_AND_SOURCE_LEDGER.md').write_text('''# 데이터 출처·권리 장부

- 출처: 자체 작성한 **교육용 합성 보도자료** 12건(10개 고유 본문 + 중복 1개 + 짧은 본문 1개).
- 실제 중앙선거관리위원회, 공공기관, 기자 발언, 정당·후보 자료 **아님**.
- 수집 방식: 외부 웹사이트에 접근하지 않고 로컬 HTML/CSV fixture로 HTML 파싱을 연습.
- 자료 이용 권한: 직접 생성한 예시 텍스트만 포함. 제3자 원문 보도자료는 포함하지 않음.
- 생성된 리드는 **규칙 기반 초안**이며 OpenAI API 또는 RAG의 결과물이 아님.
- 검수 완료 학습 데이터가 아님. JSONL 이름에 UNREVIEWED 표시.
- 실제 자료 연결 시 robots.txt, 사이트 이용약관, 공공누리·라이선스, 발행기관/URL/게시일 확인 후 수집.
''',encoding='utf-8')
print({k:v for k,v in result.items() if k not in ('records','excluded')})
