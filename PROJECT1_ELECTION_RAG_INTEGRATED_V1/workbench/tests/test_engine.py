from __future__ import annotations
from pathlib import Path
import json
import pytest
import pandas as pd
from app.engine import analyze, read_data, profile, recommend
from app.catalog import METHODS

SAMPLES=Path(__file__).resolve().parents[1]/'samples'
@pytest.fixture(scope='module')
def data():
    return {p.name:read_data(p.read_bytes(),p.name) for p in SAMPLES.iterdir() if p.suffix.lower() in ('.csv','.jsonl')}

CASES=[
 ('quality','sample_air.csv',{}),('summary','sample_air.csv',{'x':'pm10'}),
 ('histogram','sample_air.csv',{'x':'pm10'}),('frequency','sample_sales.csv',{'group':'category'}),
 ('group_summary','sample_sales.csv',{'x':'amount','group':'category','aggregation':'sum'}),
 ('timeseries','sample_air.csv',{'x':'pm10','date':'day','window':4}),
 ('correlation','sample_air.csv',{'x':'pm10','y':'pm25'}),
 ('regression','sample_air.csv',{'x':'pm10','y':'pm25'}),
 ('welch','sample_sales.csv',{'x':'amount','group':'channel'}),
 ('chi_square','sample_sales.csv',{'x':'channel','group':'category'}),
 ('bootstrap','sample_air.csv',{'x':'pm10','repeats':100}),
 ('kmeans','sample_air.csv',{'features':['pm10','pm25','temperature'],'clusters':3}),
 ('pca','sample_air.csv',{'features':['pm10','pm25','temperature']}),
 ('text_frequency','sample_news.jsonl',{'text':'title'}),
 ('election_votes','sample_election.csv',{}),
 ('election_margin','sample_election.csv',{}),
 ('election_progress','sample_election.csv',{}),
]
@pytest.mark.parametrize('method,sample,options',CASES)
def test_all_methods_return_chart_summary_and_rows(data,method,sample,options):
    result=analyze(data[sample],method,options)
    assert result['status']=='executed'
    assert result['rows']
    assert result['columns']
    assert result['chart']['kind'] in ('bar','line','scatter')
    assert result['summary']
    json.dumps(result,ensure_ascii=False,allow_nan=False)


def test_method_ids_have_executable_case():
    assert set(m['id'] for m in METHODS)==set(x[0] for x in CASES)

def test_csv_cp949():
    raw='지역,점수\n서울,10\n부산,20\n'.encode('cp949')
    d=read_data(raw,'abc.csv')
    assert list(d.columns)==['지역','점수']
    assert analyze(d,'summary',{'x':'점수'})['summary']['평균']==15

def test_filter_and_original_immutable(data):
    df=data['sample_air.csv'];old=len(df)
    result=analyze(df,'summary',{'x':'pm10'},filters=[{'column':'region','op':'equals','value':'서울'},{'column':'pm10','op':'gte','value':'20'}])
    assert result['filtered_rows']<old
    assert len(df)==old

def test_filter_date(data):
    d=data['sample_air.csv']
    r=analyze(d,'timeseries',{'x':'pm10','date':'day'},filters=[{'column':'day','op':'date_from','value':'2026-01-10'},{'column':'day','op':'date_to','value':'2026-01-15'}])
    assert 0<r['filtered_rows']<len(d)

def test_election_latest_not_sum_all_history(data):
    d=data['sample_election.csv'];r=analyze(d,'election_votes')
    assert r['summary']['최신 단계 대상 선거구']==34
    assert r['summary']['표수 합계']>0
    assert r['summary']['표수 합계']<sum(int(x) for x in d['votes'])
    assert abs(sum(row['득표율(%)'] for row in r['rows'])-100)<0.01

def test_election_reject_duplicate_latest(data):
    d=data['sample_election.csv']
    import pandas as pd
    clone=pd.concat([d,d.iloc[[-1]]],ignore_index=True)
    with pytest.raises(ValueError,match='중복'):
        analyze(clone,'election_votes')

def test_election_progress_never_over_100(data):
    r=analyze(data['sample_election.csv'],'election_progress')
    assert all(0<=row['선거인 대비 집계표 비율(%)']<=100 for row in r['rows'])
    assert '개표율' not in ''.join(r['summary'])

def test_invalid_method_and_columns(data):
    with pytest.raises(ValueError,match='등록되지'):
        analyze(data['sample_air.csv'],'magic')
    with pytest.raises(ValueError,match='수치 열'):
        analyze(data['sample_air.csv'],'summary',{'x':'non_existent'})

def test_zero_variance_corr_rejected():
    d=read_data(b'x,y\n1,2\n1,3\n1,4\n','t.csv')
    with pytest.raises(ValueError,match='분산'):
        analyze(d,'correlation',{'x':'x','y':'y'})

def test_limits_and_header():
    with pytest.raises(ValueError,match='중복'):
        read_data('a,a\n1,2'.encode(),'bad.csv')
    with pytest.raises(ValueError,match='12MiB'):
        read_data(b'1'*(13*1024*1024),'bad.csv')

def test_simulated_is_detectable(data):
    r=profile(data['sample_election.csv'])
    assert r['suggested_kind']=='election'
    assert r['election_columns_detected']
    assert any(m['id']=='election_votes' and m['status']=='available' for m in recommend(data['sample_election.csv'],'election'))

def test_welch_two_group_guard(data):
    with pytest.raises(ValueError,match='정확히 2개'):
        analyze(data['sample_sales.csv'],'welch',{'x':'amount','group':'region'})

def test_condition_difference(data):
    d=data['sample_sales.csv']
    a=analyze(d,'group_summary',{'x':'amount','group':'category','aggregation':'sum'})
    b=analyze(d,'group_summary',{'x':'amount','group':'category','aggregation':'mean'})
    assert a['summary']['계산 기준']=='합계'
    assert b['summary']['계산 기준']=='평균'
    assert a['rows'][0]['합계']!=b['rows'][0]['평균']

def test_election_candidate_filter_blocked(data):
    with pytest.raises(ValueError,match='분모'):
        analyze(data['sample_election.csv'],'election_votes',filters=[{'column':'candidate','op':'equals','value':'가상 후보 A'}])

def test_json_records():
    blob=b'{"records":[{"region":"A","amount":10},{"region":"B","amount":20}]}'
    data=read_data(blob,'data.json')
    assert len(data)==2
    assert analyze(data,'summary',{'x':'amount'})['summary']['평균']==15

def test_excel_roundtrip():
    from io import BytesIO
    from openpyxl import Workbook
    b=BytesIO();wb=Workbook();ws=wb.active
    ws.append(['region','value']);ws.append(['서울',12]);ws.append(['부산',24])
    wb.save(b)
    d=read_data(b.getvalue(),'data.xlsx')
    assert analyze(d,'summary',{'x':'value'})['summary']['평균']==18

def test_missing_value_imputation():
    d=read_data('x\n10\n\n20\n'.encode(),'a.csv')
    dropped=analyze(d,'summary',{'x':'x'},missing='drop')
    median=analyze(d,'summary',{'x':'x'},missing='median')
    assert dropped['summary']['유효 관측']<=median['summary']['유효 관측']

def test_processing_derived_and_original_preserved():
    from app.engine import transform_data
    data=read_data('region,x,y\nA,10,2\nA,20,0\nB,30,5\n'.encode(),'a.csv')
    copy,b=transform_data(data,[{'column':'region','op':'equals','value':'A'}],derived='ratio',x='x',y='y',new_column='rate')
    assert len(copy)==2
    assert copy.iloc[0]['rate']==5
    assert copy.iloc[1]['rate'] is pd.NA or pd.isna(copy.iloc[1]['rate'])
    assert 'rate' not in data.columns

def test_processing_source_cleaning():
    from app.engine import transform_data
    d=read_data('category,value\nA,10\nA,10\nB,\n'.encode(),'a.csv')
    out,stats=transform_data(d,deduplicate=True,missing_policy='drop_empty')
    assert len(out)==1
    assert stats['input_rows']==3
