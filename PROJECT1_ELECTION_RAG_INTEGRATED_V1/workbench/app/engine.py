"""Bounded, reproducible, data-driven statistical analyses. No source mutation."""
from __future__ import annotations
from collections import Counter
from io import BytesIO, StringIO
from pathlib import Path
import csv
import json
import math
import re

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from .catalog import METHODS, METHOD_MAP

MAX_FILE=12*1024*1024
MAX_ROWS=50000
MAX_COLS=120
MAX_CHART=40
MAX_TABLE=500


def _safe_float(x):
    try:
        if pd.isna(x):return None
        v=float(x)
        return round(v,7) if math.isfinite(v) else None
    except (ValueError,TypeError):return None


def _safe_val(x):
    if isinstance(x,(int,np.integer)):return int(x)
    if isinstance(x,(np.floating,float)):return _safe_float(x)
    if isinstance(x,pd.Timestamp):return x.isoformat()
    if x is None:return None
    if isinstance(x,(pd._libs.missing.NAType,)):return None
    if isinstance(x,str):return x[:1000]
    try:
        if pd.isna(x):return None
    except (ValueError,TypeError):pass
    return str(x)[:1000]


def table_rows(df,limit=MAX_TABLE):
    return [{str(k):_safe_val(v) for k,v in row.items()} for row in df.head(limit).to_dict(orient='records')]


def read_data(data:bytes,filename:str)->pd.DataFrame:
    if len(data)>MAX_FILE:raise ValueError('파일은 12MiB 이하로 제한합니다. 대용량 엔진은 별도 검증이 필요합니다.')
    ext=Path(filename).suffix.lower()
    if ext=='.csv':
        decoded=None
        for enc in ('utf-8-sig','cp949'):
            try:decoded=data.decode(enc);break
            except UnicodeDecodeError:continue
        if decoded is None:raise ValueError('CSV 인코딩: UTF-8(Sig) 또는 CP949만 지원합니다.')
        reader=csv.reader(StringIO(decoded))
        header=next(reader,[])
        if not header:raise ValueError('CSV 헤더가 없습니다.')
        if any(not x.strip() for x in header) or len(set(header))!=len(header):
            raise ValueError('CSV 헤더의 공백·중복 열 이름을 수정하세요.')
        try:df=pd.read_csv(StringIO(decoded),dtype='string',keep_default_na=False,on_bad_lines='error',nrows=MAX_ROWS+1)
        except pd.errors.ParserError as exc:raise ValueError(f'CSV 구조 오류: {exc}') from exc
    elif ext in ('.xlsx','.xlsm'):
        try:
            from openpyxl import load_workbook
            wb=load_workbook(BytesIO(data),read_only=True,data_only=True)
            ws=wb.active
            if ws.max_column and ws.max_column>MAX_COLS:raise ValueError('열 수 상한 초과')
            raw=ws.iter_rows(values_only=True)
            header=[str(x or '').strip() for x in next(raw,())]
            if not header or any(not c for c in header) or len(header)!=len(set(header)):
                raise ValueError('Excel 첫 행의 헤더 누락/중복')
            rows=list(__import__('itertools').islice(raw,MAX_ROWS+1))
            df=pd.DataFrame(rows,columns=header).astype('string').fillna('')
        except (OSError,ValueError) as exc:raise ValueError(f'Excel 읽기 실패: {exc}') from exc
    elif ext in ('.json','.jsonl'):
        try:
            if ext=='.jsonl':raw=[json.loads(line) for line in data.decode('utf-8-sig').splitlines() if line.strip()]
            else:
                raw=json.loads(data.decode('utf-8-sig'))
                if isinstance(raw,dict):raw=raw.get('records',raw.get('data',None))
            if not isinstance(raw,list) or any(not isinstance(x,dict) for x in raw):
                raise ValueError('JSON은 객체들의 배열 또는 {"records":[...]} 형식이어야 합니다.')
            df=pd.DataFrame(raw).astype('string').fillna('')
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise ValueError('JSON 파싱 실패') from exc
    else:raise ValueError('CSV, XLSX, JSON, JSONL 파일을 사용하세요.')
    if len(df)>MAX_ROWS or len(df.columns)>MAX_COLS:raise ValueError('한 번에 50,000행·120열까지만 처리합니다.')
    if df.empty:raise ValueError('분석할 데이터 행이 없습니다.')
    if not df.columns.is_unique or any(not str(x).strip() for x in df.columns):raise ValueError('중복/빈 열 이름')
    if any(str(x).startswith('__') for x in df.columns):raise ValueError('내부 예약 열 이름(__*)은 사용할 수 없습니다.')
    return df


def profile(df:pd.DataFrame)->dict:
    meta=[]
    for c in df.columns:
        x=df[c].astype('string').str.strip()
        nonempty=x[x.notna() & x.ne('')]
        numeric=pd.to_numeric(nonempty.str.replace(',','',regex=False),errors='coerce')
        num_ratio=float(numeric.notna().mean()) if len(nonempty) else 0
        datehint=bool(re.search('date|day|time|날짜|일시|연월|일자',str(c),re.I))
        typ='numeric' if num_ratio>=.85 and len(nonempty) else ('datetime_hint' if datehint else 'categorical_or_text')
        meta.append({'column':str(c),'kind':typ,'missing':int(len(x)-len(nonempty)),
                     'distinct':int(nonempty.nunique()),'examples':nonempty.head(3).tolist()})
    names={x['column'] for x in meta}
    is_election={'district','candidate','votes','step'}.issubset(names)
    return {'rows':len(df),'columns':meta,'column_names':list(map(str,df.columns)),
            'suggested_kind':'election' if is_election else ('air' if 'pm10' in names else 'general'),
            'election_columns_detected':is_election}


def recommend(df:pd.DataFrame,kind:str='auto')->list[dict]:
    info=profile(df);kind=kind if kind!='auto' else info['suggested_kind']
    numeric=[c['column'] for c in info['columns'] if c['kind']=='numeric']
    dates=[c['column'] for c in info['columns'] if c['kind']=='datetime_hint']
    names=set(df.columns)
    out=[]
    for m in METHODS:
        missing=[]
        mid=m['id']
        if mid in ('summary','histogram','bootstrap') and not numeric:missing=['수치 열 1개']
        if mid in ('group_summary','welch') and (not numeric or len(names)<2):missing=['범주 열+수치 열']
        if mid in ('correlation','regression','kmeans','pca') and len(numeric)<2:missing=['서로 다른 수치 열 2개']
        if mid=='timeseries' and (not dates or not numeric):missing=['날짜·수치 열 확인']
        if mid.startswith('election_') and not {'district','candidate','votes','step'}.issubset(names):missing=['district/candidate/votes/step 필요']
        if mid=='election_progress' and 'target_voters' not in names:missing+=['target_voters 필요']
        item=dict(m,status='needs_columns' if missing else 'available',missing=missing,kind_match=('all' in m['kinds'] or kind in m['kinds']))
        out.append(item)
    return sorted(out,key=lambda m:(not m['kind_match'],m['status']!='available',m['category']))


def _need(df,col,label):
    if not col or col not in df.columns:raise ValueError(f'{label}을(를) 데이터 열에서 선택하세요.')
    return col


def _num(df,col):
    col=_need(df,col,'수치 열')
    s=pd.to_numeric(df[col].astype('string').str.replace(',','',regex=False),errors='coerce')
    return s.replace([np.inf,-np.inf],np.nan)


def _group(df,col):
    col=_need(df,col,'범주/집단 열')
    return df[col].astype('string').str.strip().replace('',pd.NA)


def _date(df,col):
    col=_need(df,col,'날짜 열')
    return pd.to_datetime(df[col],errors='coerce')


def apply_filters(df,filters):
    if not isinstance(filters,list) or len(filters)>4:raise ValueError('필터는 최대 4개입니다.')
    out=df.copy()
    for fil in filters:
        col=_need(out,fil.get('column'),'필터 열')
        op=fil.get('op','equals');value=str(fil.get('value',''))
        if op in ('equals','contains','not_equals'):
            field=out[col].astype('string').fillna('')
            m=field.eq(value) if op=='equals' else (field.ne(value) if op=='not_equals' else field.str.contains(value,regex=False,case=False,na=False))
        elif op in ('gt','gte','lt','lte'):
            try:val=float(value)
            except ValueError:raise ValueError('수치 필터의 기준은 숫자여야 합니다.')
            v=_num(out,col)
            m={'gt':v>val,'gte':v>=val,'lt':v<val,'lte':v<=val}[op]
        elif op in ('date_from','date_to'):
            dt=_date(out,col)
            try:cutoff=pd.to_datetime(value,errors='raise')
            except (ValueError,TypeError):raise ValueError('날짜 기준값은 YYYY-MM-DD 형식입니다.')
            m=dt>=cutoff if op=='date_from' else dt<=cutoff
        else:raise ValueError('지원하지 않는 필터 연산자')
        out=out[m.fillna(False)]
    return out


def _chart(kind,labels=None,series=None,points=None,unit='',title=''):
    return {'kind':kind,'labels':list(labels or []),'series':series or [],'points':points or [],'unit':unit,'title':title}


def _bars(labels,values,name,unit='',title=''):
    return _chart('bar',[str(x) for x in labels], [{'name':name,'values':[_safe_float(v) or 0 for v in values]}],unit=unit,title=title)


def _histo(x,bins=10,title=''):
    counts,edges=np.histogram(x,bins=bins)
    labels=[f'{edges[i]:.2f}~{edges[i+1]:.2f}' for i in range(len(counts))]
    return _bars(labels,counts,'관측 건수','건',title),pd.DataFrame({'구간':labels,'건수':counts.astype(int)})


def _stats(x)->dict:
    return {k:_safe_float(v) for k,v in {'평균':x.mean(),'중앙값':x.median(),'표준편차(표본)':x.std(ddof=1),
        '최솟값':x.min(),'Q1':x.quantile(.25),'Q3':x.quantile(.75),'최댓값':x.max()}.items()}


def _election_latest(df):
    for c in ('district','candidate','votes','step'):_need(df,c,f'선거 데이터 {c}')
    work=df.copy();work['_step']=_num(work,'step');work['_votes']=_num(work,'votes')
    work=work.dropna(subset=['_step','_votes'])
    if work.empty:raise ValueError('유효한 개표 단계/표수가 없습니다.')
    if (work['_votes']<0).any():raise ValueError('득표수가 음수입니다.')
    # The latest stage is per district, not the last row of the entire national feed.
    dmax=work.groupby('district')['_step'].transform('max')
    latest=work[work['_step'].eq(dmax)].copy()
    if latest.duplicated(['district','candidate']).any():raise ValueError('최신 단계에 선거구·후보 중복 행이 있습니다.')
    return latest


def analyze(df,method:str,options:dict|None=None,filters:list|None=None,missing='drop')->dict:
    if method not in METHOD_MAP:raise ValueError('등록되지 않은 통계기법입니다.')
    opts=options or {};filters=filters or []
    if missing not in ('drop','median','zero'):raise ValueError('결측 처리: 제외/중앙값 대치/0 대치만 지원')
    raw_rows=len(df)
    w=apply_filters(df,filters)
    if w.empty:raise ValueError('조건에 맞는 데이터가 없습니다. 필터 조건을 완화하세요.')
    xcol=opts.get('x');ycol=opts.get('y');groupcol=opts.get('group');datecol=opts.get('date')
    warnings=[METHOD_MAP[method]['caution']]
    rows=pd.DataFrame();summary={};chart=_chart('bar');notes=[]
    def numeric(col):
        s=_num(w,col)
        if missing=='zero':return s.fillna(0)
        if missing=='median':
            if s.notna().sum()==0:raise ValueError('중앙값을 계산할 유효 수치가 없습니다.')
            return s.fillna(s.median())
        return s
    def number(opt,default,lo,hi):
        try:z=int(opts.get(opt,default))
        except (TypeError,ValueError):raise ValueError(f'{opt} 항목은 정수입니다.')
        if z<lo or z>hi:raise ValueError(f'{opt} 범위는 {lo}~{hi}')
        return z
    if method=='quality':
        fields=[]
        for c in w.columns:
            s=w[c].astype('string').str.strip()
            empt=int(s.isna().sum() + s.eq('').sum())
            fields.append({'열':str(c),'결측':empt,'비결측':int(len(s)-empt),'고유값':int(s.nunique(dropna=True))})
        rows=pd.DataFrame(fields)
        summary={'전체 행':len(w),'열 수':len(w.columns),'중복 행':int(w.duplicated().sum()),'총 결측 셀':sum(f['결측'] for f in fields)}
        chart=_bars(rows['열'].head(MAX_CHART),rows['결측'].head(MAX_CHART),'결측 셀','개')
    elif method in ('summary','histogram','bootstrap'):
        x=numeric(xcol).dropna()
        if len(x)==0:raise ValueError('유효 수치가 없어 계산할 수 없습니다.')
        if method=='summary':
            summary={'유효 관측':len(x),'제외/필터 후 행':len(w),**_stats(x)}
            chart,rows=_histo(x.to_numpy(),number('bins',10,3,40),'수치 분포')
        elif method=='histogram':
            chart,rows=_histo(x.to_numpy(),number('bins',10,3,40),'도수분포')
            summary={'유효 관측':len(x),**_stats(x)}
        else:
            if len(x)<5:raise ValueError('부트스트랩에는 유효 관측 5개 이상 필요')
            repeats=number('repeats',500,100,3000)
            rng=np.random.default_rng(number('seed',42,0,999999))
            means=np.mean(rng.choice(x.to_numpy(),size=(repeats,len(x)),replace=True),axis=1)
            ci=np.quantile(means,[.025,.975]);summary={'유효 표본':len(x),'반복 횟수':repeats,'원본 평균':_safe_float(x.mean()),'95% 하한':_safe_float(ci[0]),'95% 상한':_safe_float(ci[1])}
            chart,rows=_histo(means,number('bins',16,3,40),'부트스트랩 표본평균 분포')
            warnings.append('95% 구간은 분위수 방식이며, 무작위 표본·대표성 가정을 별도 확인해야 합니다.')
    elif method=='frequency':
        x=_group(w,groupcol or xcol).fillna('(결측)')
        counts=x.value_counts().head(MAX_TABLE)
        rows=pd.DataFrame({'범주':counts.index.tolist(),'건수':counts.values.tolist(),'비율(%)':(counts/len(w)*100).round(3).tolist()})
        summary={'전체 행':len(w),'범주 수':int(x.nunique()),'표시 범주':len(rows)}
        chart=_bars(rows['범주'].head(MAX_CHART),rows['건수'].head(MAX_CHART),'빈도','건')
    elif method=='group_summary':
        group=_group(w,groupcol);v=numeric(xcol)
        t=pd.DataFrame({'집단':group,'값':v}).dropna()
        if t.empty:raise ValueError('유효한 집단·수치 쌍이 없습니다.')
        r=t.groupby('집단',sort=True)['값'].agg(['size','sum','mean','median']).reset_index()
        r.columns=['집단','건수','합계','평균','중앙값']
        metric=opts.get('aggregation','mean'); metrics={'sum':'합계','mean':'평균','median':'중앙값','count':'건수'}
        if metric not in metrics:raise ValueError('집계법은 sum/mean/median/count')
        r=r.sort_values(metrics[metric],ascending=False).head(MAX_TABLE)
        rows=r
        summary={'비교 집단 수':len(rows),'유효 자료':len(t),'계산 기준':metrics[metric]}
        chart=_bars(rows['집단'].head(MAX_CHART),rows[metrics[metric]].head(MAX_CHART),metrics[metric])
    elif method=='timeseries':
        dt=_date(w,datecol);v=numeric(xcol)
        valid=pd.DataFrame({'날짜':dt,'값':v}).dropna()
        if valid.empty:raise ValueError('유효 날짜·수치 쌍이 없습니다.')
        freq=opts.get('frequency','D')
        if freq not in ('D','W','MS'):raise ValueError('시간 단위: 일/주/월')
        agg=opts.get('aggregation','mean')
        if agg not in ('mean','sum','count'):raise ValueError('시계열 집계: mean/sum/count')
        grouped=valid.set_index('날짜')['값'].resample(freq).agg(agg).dropna()
        if grouped.empty:raise ValueError('시계열 결과 없음')
        window=number('window',3,2,90)
        smooth=grouped.rolling(window,min_periods=window).mean()
        rows=pd.DataFrame({'날짜':grouped.index.strftime('%Y-%m-%d'),'집계값':grouped.values,'이동평균':smooth.values})
        rows=rows.tail(MAX_TABLE)
        summary={'시계열 점':len(grouped),'유효 행':len(valid),'이동평균 창':window,'시간 단위':freq}
        chart=_chart('line',rows['날짜'].tolist(),[{'name':'집계값','values':[_safe_float(v) for v in rows['집계값']]},{'name':f'{window}기간 이동평균','values':[_safe_float(v) for v in rows['이동평균']]}],title='기간별 변화')
    elif method in ('correlation','regression'):
        if xcol==ycol:raise ValueError('서로 다른 수치 열 2개를 선택하세요.')
        t=pd.DataFrame({'x':numeric(xcol),'y':numeric(ycol)}).dropna()
        if len(t)<3 or t['x'].nunique()<2 or t['y'].nunique()<2:raise ValueError('유효한 관측 쌍 최소 3개, 양쪽 변수의 분산 필요')
        pear=stats.pearsonr(t['x'],t['y'])
        spearman=stats.spearmanr(t['x'],t['y'])
        summary={'관측 쌍':len(t),'Pearson r':_safe_float(pear.statistic),'Spearman ρ':_safe_float(spearman.statistic)}
        pointss=[{'x':_safe_float(v['x']),'y':_safe_float(v['y']),'group':'관측'} for _,v in t.head(300).iterrows()]
        chart=_chart('scatter',points=pointss,title=f'{xcol} · {ycol}')
        rows=t.head(MAX_TABLE).rename(columns={'x':xcol,'y':ycol})
        if method=='regression':
            fit=stats.linregress(t['x'],t['y'])
            summary.update({'기울기':_safe_float(fit.slope),'절편':_safe_float(fit.intercept),'설명력 R²(같은 자료)':_safe_float(fit.rvalue**2),'p값':_safe_float(fit.pvalue)})
            chart['fit']={'slope':_safe_float(fit.slope),'intercept':_safe_float(fit.intercept)}
            warnings.append('이 모델은 학습 자료 적합도를 표시하며 미래 예측 정확도를 뜻하지 않습니다.')
    elif method=='welch':
        t=pd.DataFrame({'group':_group(w,groupcol),'x':numeric(xcol)}).dropna()
        if t['group'].nunique()!=2:raise ValueError('Welch t 검정은 정확히 2개 집단만 선택해야 합니다. 필터를 적용하세요.')
        names=sorted(t['group'].unique())
        a=t[t['group']==names[0]]['x'];b=t[t['group']==names[1]]['x']
        if len(a)<2 or len(b)<2:raise ValueError('각 집단에 최소 2개 관측 필요')
        test=stats.ttest_ind(a,b,equal_var=False)
        if not np.isfinite(test.statistic):raise ValueError('분산이 없어 검정 불가능')
        rows=pd.DataFrame({'집단':names,'표본수':[len(a),len(b)],'평균':[a.mean(),b.mean()],'표준편차':[a.std(),b.std()]})
        chart=_bars(names,rows['평균'],'평균')
        summary={'검정 통계량 t':_safe_float(test.statistic),'p값':_safe_float(test.pvalue),'평균 차이(A-B)':_safe_float(a.mean()-b.mean())}
    elif method=='chi_square':
        x=_group(w,xcol);g=_group(w,groupcol)
        t=pd.crosstab(x,g)
        if min(t.shape)<2:raise ValueError('각 범주 열에 서로 다른 범주 2개 이상 필요')
        if t.size>400:raise ValueError('교차표 규모 제한: 최대 400셀')
        test=stats.chi2_contingency(t)
        rows=t.reset_index().rename(columns={xcol:'범주'})
        summary={'χ² 통계량':_safe_float(test.statistic),'자유도':int(test.dof),'p값':_safe_float(test.pvalue),'기대빈도 5 미만 셀':int((test.expected_freq<5).sum())}
        counts=t.sum(axis=1).sort_values(ascending=False).head(MAX_CHART)
        chart=_bars(counts.index,counts,'관측 건수','건')
        if (test.expected_freq<5).any():warnings.append('기대빈도 5 미만 셀이 있으므로 카이제곱 근사 해석에 주의하세요.')
    elif method in ('kmeans','pca'):
        features=opts.get('features') or [xcol,ycol]
        features=list(dict.fromkeys([x for x in features if x]))
        if len(features)<2 or len(features)>8:raise ValueError('서로 다른 수치 특성 2~8개를 고르세요.')
        for f in features:_need(w,f,'특성 열')
        t=pd.DataFrame({f:numeric(f) for f in features}).dropna()
        if len(t)<5:raise ValueError('유효 관측 5개 이상이 필요합니다.')
        if len(t)>10000:raise ValueError('군집·PCA는 분석 후 10,000행 이하로 제한합니다.')
        scaler=StandardScaler();z=scaler.fit_transform(t)
        if method=='kmeans':
            k=number('clusters',3,2,8)
            if k>=len(t) or len(np.unique(z,axis=0))<k:raise ValueError('군집 수보다 서로 다른 관측이 많아야 합니다.')
            labels=KMeans(n_clusters=k,random_state=number('seed',42,0,999999),n_init=10).fit_predict(z)
            coords=z[:,:2]
            rows=t.head(MAX_TABLE).copy();rows['군집']=labels[:len(rows)]+1
            summary={'유효 행':len(t),'군집 수':k,'특성 수':len(features)}
            chart=_chart('scatter',points=[{'x':_safe_float(v[0]),'y':_safe_float(v[1]),'group':f'군집 {int(labels[i])+1}'} for i,v in enumerate(coords[:350])],title='표준화된 첫 2개 특성 (시각화)')
        else:
            p=PCA(n_components=2,random_state=42);coords=p.fit_transform(z)
            rows=pd.DataFrame({'PC1':coords[:MAX_TABLE,0],'PC2':coords[:MAX_TABLE,1]})
            summary={'유효 행':len(t),'특성 수':len(features),'PC1 설명분산율':_safe_float(p.explained_variance_ratio_[0]),'PC2 설명분산율':_safe_float(p.explained_variance_ratio_[1])}
            chart=_chart('scatter',points=[{'x':_safe_float(v[0]),'y':_safe_float(v[1]),'group':'관측'} for v in coords[:350]],title='PCA 2D 투영')
    elif method=='text_frequency':
        col=_need(w,opts.get('text') or groupcol or xcol,'텍스트 열')
        tokens=[]
        for s in w[col].dropna().astype(str).head(10000):
            tokens.extend(t.lower() for t in re.findall(r'[가-힣a-zA-Z0-9]{2,}',s))
            if len(tokens)>250000:break
        counts=Counter(tokens).most_common(100)
        if not counts:raise ValueError('텍스트에서 토큰을 추출하지 못했습니다.')
        rows=pd.DataFrame(counts,columns=['단어','빈도'])
        summary={'분석 행':min(len(w),10000),'서로 다른 토큰':len(set(tokens)),'추출 토큰':len(tokens)}
        chart=_bars(rows['단어'].head(20),rows['빈도'].head(20),'빈도','건')
        warnings.append('문장 구조·형태소·의미 유사도 분석이 아닌 단순 단어 빈도입니다.')
    elif method.startswith('election_'):
        if any(f.get('column')=='candidate' for f in filters):
            raise ValueError('후보 필터는 득표율·개표율의 분모를 왜곡할 수 있어 선거 전용 기법에서는 차단합니다. 지역·선거구·단계를 선택하세요.')
        for c in ('district','candidate','votes','step'):_need(w,c,'선거 데이터')
        if method in ('election_votes','election_margin'):
            last=_election_latest(w)
            # Only the current/latest stage for EACH selected district.
            if method=='election_votes':
                vote=last.groupby('candidate')['_votes'].sum().sort_values(ascending=False)
                total=vote.sum()
                if total<=0:raise ValueError('유효 득표 총합 0')
                rows=pd.DataFrame({'후보':vote.index,'득표수':vote.astype(int).values,'득표율(%)':(vote/total*100).round(4).values})
                chart=_bars(rows['후보'],rows['득표율(%)'],'득표율','%')
                summary={'최신 단계 대상 선거구':last['district'].nunique(),'표수 합계':int(total),'후보 수':len(vote)}
            else:
                vals=[]
                for district,g in last.groupby('district'):
                    sums=g.groupby('candidate')['_votes'].sum().sort_values(ascending=False)
                    if len(sums)<2 or sums.sum()==0:continue
                    vals.append({'선거구':district,'1위':str(sums.index[0]),'2위':str(sums.index[1]),'격차(표)':int(sums.iloc[0]-sums.iloc[1]),'격차(%p)':round((sums.iloc[0]-sums.iloc[1])/sums.sum()*100,3)})
                rows=pd.DataFrame(vals).sort_values('격차(%p)',ascending=False).head(MAX_TABLE) if vals else pd.DataFrame()
                if rows.empty:raise ValueError('비교 가능한 후보가 2명 이상인 선거구가 없습니다.')
                summary={'비교 선거구':len(rows),'평균 격차(%p)':_safe_float(rows['격차(%p)'].mean())}
                chart=_bars(rows['선거구'].head(MAX_CHART),rows['격차(%p)'].head(MAX_CHART),'1·2위 격차','%p')
        else:
            _need(w,'target_voters','목표 투표수')
            work=w.copy();work['_step']=_num(work,'step');work['_votes']=_num(work,'votes');work['_target']=_num(work,'target_voters')
            work=work.dropna(subset=['_step','_votes','_target'])
            if work.empty or (work['_target']<=0).any() or (work['_votes']<0).any():raise ValueError('유효하지 않은 목표 표수/득표수')
            if work.duplicated(['district','candidate','_step']).any():raise ValueError('선거구·후보·단계가 중복되었습니다.')
            by=work.groupby(['district','_step'],as_index=False).agg({'_votes':'sum','_target':['min','max']})
            by.columns=['district','step','counted','target_min','target_max']
            if not (by['target_min']==by['target_max']).all():raise ValueError('선거구·단계별 목표 투표수가 불일치합니다.')
            step=by.groupby('step').agg({'counted':'sum','target_min':'sum'}).sort_index()
            if (step['counted']>step['target_min']).any():raise ValueError('집계 표수가 목표 표수보다 많습니다.')
            rows=pd.DataFrame({'단계':step.index,'집계 표수':step['counted'].astype(int),'선거인 수':step['target_min'].astype(int),'선거인 대비 집계표 비율(%)':(step['counted']/step['target_min']*100).round(4)})
            rows=rows.tail(MAX_TABLE)
            summary={'분석 단계':len(rows),'마지막 단계 선거인 대비 집계표 비율(%)':_safe_float(rows['선거인 대비 집계표 비율(%)'].iloc[-1])}
            chart=_chart('line',rows['단계'].astype(str).tolist(),[{'name':'선거인 대비 집계표 비율','values':rows['선거인 대비 집계표 비율(%)'].tolist()}],unit='%',title='교육용 집계표수/선거인 수 비율(개표율 아님)')
            # Multiple districts can enter at different stages; never imply this is official timeline.
            warnings.append('단계별 집계 분모는 해당 단계에 포함된 선거구만 계산한 값입니다. 누락 단계는 원자료 확인이 필요합니다.')
            warnings.append('target_voters는 선거인 수이며 실제 개표 대상 표수가 아닙니다. 이 비율은 개표율 또는 투표율로 보도할 수 없습니다.')
        warnings.append('입력 데이터의 공식성은 검증하지 않았습니다. 모의 자료인 경우 실제 선거 결과로 게시하지 마세요.')
    else:raise ValueError('미구현 기법')
    if isinstance(rows,pd.DataFrame) and len(rows)>MAX_TABLE:rows=rows.head(MAX_TABLE)
    return {'method':method,'method_name':METHOD_MAP[method]['name'],'input_rows':raw_rows,'filtered_rows':len(w),
            'excluded_by_filter':raw_rows-len(w),'summary':{str(k):_safe_val(v) for k,v in summary.items()},
            'chart':chart,'columns':list(map(str,rows.columns)),'rows':table_rows(rows),
            'total_result_rows':len(rows),'warnings':warnings,'status':'executed','mode':'user_data_or_clearly_labeled_demo',
            'conditions':{'filters':filters,'options':opts,'missing':missing}}


def transform_data(df,filters=None,missing_policy='keep',deduplicate=False,derived='none',x=None,y=None,new_column='derived_value'):
    """Create an explicitly processed COPY; never mutate original imported data."""
    if missing_policy not in ('keep','drop_empty','median','zero'):
        raise ValueError('가공 결측 정책: 유지/빈 행 제거/수치 중앙값/수치 0 대치')
    if derived not in ('none','sum','difference','ratio','percent'):
        raise ValueError('지원하지 않는 계산 열 생성 방식')
    out=apply_filters(df,filters or []).copy()
    before=len(out)
    if deduplicate:out=out.drop_duplicates().copy()
    if missing_policy=='drop_empty':
        out=out.replace('',np.nan).dropna().copy()
    elif missing_policy in ('median','zero'):
        info=profile(out)
        cols=[c['column'] for c in info['columns'] if c['kind']=='numeric']
        for col in cols:
            vals=pd.to_numeric(out[col].astype('string').str.replace(',','',regex=False),errors='coerce')
            if missing_policy=='median' and vals.notna().sum()==0:continue
            filled=vals.fillna(vals.median() if missing_policy=='median' else 0)
            out[col]=filled.map(lambda v: '' if pd.isna(v) else str(v))
    if derived!='none':
        _need(out,x,'첫 번째 계산 수치 열');_need(out,y,'두 번째 계산 수치 열')
        if x==y:raise ValueError('서로 다른 두 수치 열을 선택하세요.')
        name=str(new_column).strip()
        if not name or len(name)>80 or name in out.columns or name.startswith('__'):
            raise ValueError('새 열 이름을 확인하세요(기존 열과 중복 불가, 80자 제한).')
        a=_num(out,x);b=_num(out,y)
        if derived=='sum':z=a+b
        elif derived=='difference':z=a-b
        else:z=a.div(b.where(b!=0))*(100 if derived=='percent' else 1)
        out[name]=z.replace([np.inf,-np.inf],np.nan)
    if out.empty:raise ValueError('가공 조건 적용 후 남은 행이 없습니다.')
    if len(out.columns)>MAX_COLS:raise ValueError('가공된 데이터가 최대 열 수를 초과합니다.')
    return out,{'input_rows':len(df),'filtered_rows':before,'output_rows':len(out),'removed_by_dedup_or_missing':before-len(out),'derived':derived,'missing_policy':missing_policy}
