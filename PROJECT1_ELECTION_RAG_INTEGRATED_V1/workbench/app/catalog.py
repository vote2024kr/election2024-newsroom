"""Source-grounded catalog: generic statistical methods + election aggregation cautions."""
from __future__ import annotations

KINDS = {
 "auto":"자동 분석", "general":"일반 통계", "election":"선거·개표", "air":"대기·환경",
 "commerce":"판매·매출", "news":"뉴스·텍스트", "education":"교육·실습"
}
METHODS = [
 {"id":"quality","category":"품질·정제","name":"결측·중복·자료형 진단","chart":"결측 막대","needs":"데이터 열","caution":"표본/전체와 자료형 자동 추론을 구분하세요","kinds":["all"]},
 {"id":"summary","category":"기술통계","name":"기술통계·사분위수","chart":"히스토그램","needs":"수치 열 1개","caution":"결측·이상치에 영향을 받습니다","kinds":["all"]},
 {"id":"frequency","category":"기술통계","name":"빈도·비율","chart":"범주 막대","needs":"범주 열 1개","caution":"범주 결측과 중복 집계를 확인하세요","kinds":["all"]},
 {"id":"group_summary","category":"집단 비교","name":"집단별 합계·평균·중앙값","chart":"그룹 막대","needs":"집단 열 + 수치 열","caution":"집단 크기가 다르면 단순 합계/평균 비교에 주의","kinds":["all"]},
 {"id":"histogram","category":"분포","name":"도수분포·히스토그램","chart":"도수 막대","needs":"수치 열 1개","caution":"구간 너비에 따라 모양이 달라집니다","kinds":["all"]},
 {"id":"timeseries","category":"시계열","name":"시간별 추세·이동평균","chart":"꺾은선","needs":"날짜 열 + 수치 열","caution":"시계열 간격·관측 누락을 검토하세요","kinds":["all"]},
 {"id":"correlation","category":"관계","name":"Pearson·Spearman 상관","chart":"산점도","needs":"수치 열 2개","caution":"상관은 인과를 뜻하지 않습니다","kinds":["all"]},
 {"id":"regression","category":"관계","name":"단순 선형회귀","chart":"산점도·적합선","needs":"수치 열 2개","caution":"훈련 적합도는 일반화 예측 성능이 아닙니다","kinds":["all"]},
 {"id":"welch","category":"차이 검정","name":"Welch 독립표본 t 검정","chart":"집단 평균 막대","needs":"수치 열 + 정확히 2집단","caution":"독립성·표본추출·다중검정 조건을 확인하세요","kinds":["all"]},
 {"id":"chi_square","category":"차이 검정","name":"카이제곱 독립성 검정","chart":"교차표·막대","needs":"범주 열 2개","caution":"기대빈도 및 독립 관측 조건을 확인하세요","kinds":["all"]},
 {"id":"bootstrap","category":"확률·추론","name":"부트스트랩 평균 신뢰구간","chart":"반복 표본평균 분포","needs":"수치 열 + 반복 수","caution":"표본 편향은 부트스트랩으로 해결되지 않습니다","kinds":["all"]},
 {"id":"kmeans","category":"군집","name":"KMeans 군집 분석","chart":"군집 산점도","needs":"수치 열 2개 이상","caution":"거리·스케일·군집 수·정당성을 검토하세요","kinds":["all"]},
 {"id":"pca","category":"차원 축소","name":"PCA 주성분 분석","chart":"2D 투영 산점도","needs":"수치 열 2개 이상","caution":"주성분은 원인·인과를 나타내지 않습니다","kinds":["all"]},
 {"id":"text_frequency","category":"텍스트","name":"단어 빈도·텍스트 전처리","chart":"단어 빈도 막대","needs":"텍스트 열","caution":"공백 토큰 분리는 형태소 분석이 아닙니다","kinds":["all"]},
 {"id":"election_votes","category":"선거","name":"선거 후보별 최신 집계 득표율","chart":"후보별 막대","needs":"선거구·후보·득표수·단계","caution":"모의 데이터를 실측/예측으로 표시하지 마세요","kinds":["election"]},
 {"id":"election_margin","category":"선거","name":"선거구별 1·2위 격차","chart":"격차 막대(%p)","needs":"선거구·후보·득표수·단계","caution":"득표율 격차 단위는 퍼센트포인트(%p)","kinds":["election"]},
 {"id":"election_progress","category":"선거","name":"집계표수 / 선거인 수 비율(교육용)","chart":"단계별 추세","needs":"선거구·후보·득표수·단계·선거인 수","caution":"이 값은 개표율·투표율이 아닙니다. target_voters는 선거인 수이며 실제 개표 대상 표수가 아닙니다.","kinds":["election"]}
]
METHOD_MAP={m['id']:m for m in METHODS}
