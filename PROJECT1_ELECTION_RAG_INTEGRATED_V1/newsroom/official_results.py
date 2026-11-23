"""Local, user-uploaded FINAL vote results. Never claims live or certified access.

Supports documented NEC 2024 constituency CSV columns, and 2026 variants.
Does not extrapolate official counting progress, turnout, parties, or seat totals.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from io import StringIO
import csv
import math
import random
from urllib.parse import urlsplit

MAX_BYTES = 35 * 1024 * 1024
MAX_ROWS = 250_000
SUMMARY = {'계','합계','소계','총계','전체','전국','시도계','구시군계','선거구계','소계(합계)'}
# The NEC raw file mixes candidate vote rows with electors/ballots/invalid/abstention
# rows under the same `후보자` column. Never sum these as candidates.
NON_CANDIDATES = {'선거인수','투표수','무효투표수','유효투표수','기권자수','기권수','무효표','유효표','투표자수','선거인','투표인수','사전투표수'}
COLUMNS = {
 'region':['시도명','시·도명','시도'],
 'district':['선거구명','지역구명','선거구'],
 'candidate':['후보자','후보자명','후보명'],
 'votes':['득표수','후보자득표수','득표'],
 'neighborhood':['법정읍면동명','읍면동명','읍면동'],
 'poll':['투표구명','구분명','투표구분','투표구'],
}
ALLOWED_HOSTS={'data.go.kr','www.data.go.kr','data.nec.go.kr','info.nec.go.kr'}

class DataError(ValueError): pass


def safe_source_url(url: str) -> str:
    u=urlsplit(url.strip())
    if u.scheme!='https' or (u.hostname or '').lower() not in ALLOWED_HOSTS or u.username or u.password:
        raise DataError('출처는 https://www.data.go.kr 또는 선관위 공식 https 주소여야 합니다.')
    return url.strip()


def _decode(data: bytes):
    if not data or len(data)>MAX_BYTES:
        raise DataError('CSV 용량은 1바이트 이상, 최대 35MiB입니다.')
    for encoding in ('utf-8-sig','cp949','euc-kr'):
        try:return data.decode(encoding),encoding
        except UnicodeDecodeError:continue
    raise DataError('문자 인코딩은 UTF-8 또는 CP949 계열을 사용해 주세요.')


def _cols(fieldnames):
    fields={x.strip().lstrip('\ufeff'):x for x in fieldnames if x}
    resolved={kind:next((fields[k] for k in opts if k in fields),None) for kind,opts in COLUMNS.items()}
    required=['region','district','candidate','votes']
    if any(not resolved[k] for k in required):
        raise DataError('필수 열: 시도명, 선거구명, 후보자, 득표수. 확인된 헤더: '+', '.join(fields))
    # Without poll-level fields duplicate records may be ambiguous; still permit district-level compact summary.
    return resolved


def parse_csv(data: bytes, *, source_url: str, election_name: str='사용자 제공 선거 결과', demo_mode: bool=False) -> dict:
    url='LOCAL_SYNTHETIC_DEMO' if demo_mode else safe_source_url(source_url)
    text,encoding=_decode(data)
    reader=csv.DictReader(StringIO(text, newline=''))
    if not reader.fieldnames:
        raise DataError('첫 줄에 CSV 헤더가 필요합니다.')
    cols=_cols(reader.fieldnames)
    counts=defaultdict(int)
    poll_counts=Counter()
    seen=set(); accepted=0; ignored=0
    for line,row in enumerate(reader,2):
        if line>MAX_ROWS+1:raise DataError('행 수 상한 250,000건 초과')
        if None in row:raise DataError(f'{line}행의 열 개수가 헤더보다 많습니다.')
        region=(row.get(cols['region']) or '').strip()
        district=(row.get(cols['district']) or '').strip()
        cand=(row.get(cols['candidate']) or '').strip()
        raw=(row.get(cols['votes']) or '').strip()
        neighborhood=(row.get(cols['neighborhood']) or '').strip() if cols['neighborhood'] else ''
        poll=(row.get(cols['poll']) or '').strip() if cols['poll'] else ''
        if any(x in SUMMARY for x in (region,district,cand,neighborhood,poll)) or cand in NON_CANDIDATES:
            ignored+=1
            continue
        if not region or not district or not cand or not raw:
            raise DataError(f'{line}행: 지역·선거구·후보·득표수의 빈 값')
        vote_str=raw.replace(',','').replace(' ','')
        if not vote_str.isdecimal():
            raise DataError(f'{line}행: 득표수가 0 이상의 정수가 아닙니다: {raw[:24]}')
        votes=int(vote_str)
        if votes>100_000_000:
            raise DataError(f'{line}행: 비정상적으로 큰 득표수')
        # Same candidate is expected at multiple distinct polling stations, but NEVER duplicate same key.
        key=(region,district,neighborhood,poll,cand)
        if key in seen:
            raise DataError(f'{line}행: 원본 중복 키 {region}/{district}/{poll}/{cand}. 중복 합산 금지')
        seen.add(key)
        counts[(region,district,cand)]+=votes
        poll_counts[(region,district,neighborhood,poll)]+=votes
        accepted+=1
    if not accepted:raise DataError('분석 가능한 행이 없습니다. 합계 행만 있는지 확인해 주세요.')
    if len(counts)>100_000:raise DataError('후보·선거구 조합이 너무 많습니다.')
    regions=sorted({r for r,d,c in counts})
    districts=sorted({(r,d) for r,d,c in counts})
    if len(districts)>10_000:raise DataError('선거구 수 상한을 초과했습니다.')
    # Strict provenance: URL is supplied metadata, NOT independent certification.
    return {'mode':'SYNTHETIC_SAMPLE_NOT_OFFICIAL' if demo_mode else 'USER_UPLOADED_FINAL_RESULT','verified':False,'source_status':'교육용 가상 CSV · 공식 선거 결과 아님' if demo_mode else '출처 URL은 사용자 입력. 실제 기관 원본과 독립 대조하지 않음',
            'source_url':url,'election_name':election_name[:120],
            'sha256':sha256(data).hexdigest(),'encoding':encoding,'rows':accepted,
            'summary_rows_excluded':ignored,'region_count':len(regions),'district_count':len(districts),
            'regions':regions,'districts':[{'region':r,'district':d} for r,d in districts],
            'votes':[{'region':r,'district':d,'candidate':c,'votes':v} for (r,d,c),v in sorted(counts.items())]}


def _group(ds:dict,region:str='',district:str=''):
    if district and not region:raise DataError('선거구를 지정하려면 시도를 함께 지정해 주세요.')
    if region and region not in ds['regions']:raise DataError('존재하지 않는 시도입니다.')
    if district and not any(d['region']==region and d['district']==district for d in ds['districts']):
        raise DataError('해당 시도의 선거구가 아닙니다.')
    return [x for x in ds['votes'] if (not region or x['region']==region) and (not district or x['district']==district)]


def analyze(ds:dict,method:str='district_votes',region:str='',district:str='',limit:int=25)->dict:
    if not isinstance(limit,int) or not 1<=limit<=60:raise DataError('표시 개수는 1~60입니다.')
    relevant=_group(ds,region,district)
    if not relevant:raise DataError('해당 조건의 데이터가 없습니다.')
    sums=defaultdict(Counter)
    for v in relevant:sums[(v['region'],v['district'])][v['candidate']]+=v['votes']
    district_totals={(r,d):sum(c.values()) for (r,d),c in sums.items()}
    method_name={
      'district_votes':'선거구별 득표수',
      'candidate_share':'선거구 후보별 득표율',
      'lead_margin':'선거구별 1·2위 격차',
      'region_votes':'시도별 후보 득표수 합계',
      'candidate_count':'선거구별 후보자 수',
      'vote_distribution':'선거구별 후보 득표수 합계 분포',
      'region_district_count':'시도별 선거구 수',
      'region_avg_votes':'시도별 선거구 평균 후보득표 합계',
      'candidate_vote_distribution':'후보자별 득표수 분포',
      'margin_distribution':'선거구 1·2위 격차 분포',
      'close_races':'근소 격차 선거구 순위',
      'district_leader_share':'선거구별 1위 후보 득표율',
    }
    if method not in method_name:raise DataError('지원하지 않는 기법입니다.')
    if method=='candidate_share' and not district:
        raise DataError('후보자 개인의 득표율은 개별 선거구에서만 계산합니다. 전국 후보 합산은 불가합니다.')
    rows=[]
    if method=='candidate_share':
        total=sum(x['votes'] for x in relevant)
        rows=[{'label':x['candidate'],'value':round(x['votes']/total*100,3) if total else 0,
               'votes':x['votes'],'unit':'%'} for x in sorted(relevant,key=lambda x:-x['votes'])]
    elif method=='region_votes':
        regions=Counter()
        for (r,d),total in district_totals.items(): regions[r]+=total
        rows=[{'label':r,'value':v,'unit':'표'} for r,v in regions.most_common()]
    elif method=='region_district_count':
        rc=Counter(r for r,d in district_totals)
        rows=[{'label':r,'value':v,'unit':'선거구'} for r,v in rc.most_common()]
    elif method=='region_avg_votes':
        rc=defaultdict(list)
        for (r,d),v in district_totals.items():rc[r].append(v)
        rows=[{'label':r,'value':round(sum(v)/len(v),2),'unit':'표/선거구'} for r,v in rc.items()]
        rows.sort(key=lambda x:-x['value'])
    elif method=='district_votes':
        rows=[{'label':f'{r} / {d}','value':v,'unit':'표'} for (r,d),v in sorted(district_totals.items(),key=lambda x:-x[1])]
    elif method=='candidate_count':
        rows=[{'label':f'{r} / {d}','value':len(c),'unit':'명'} for (r,d),c in sorted(sums.items(),key=lambda x:-len(x[1]))]
    elif method=='close_races':
        for (r,d),cs in sums.items():
            scores=sorted(cs.values(),reverse=True);total=sum(scores)
            margin=(scores[0]-scores[1])/total*100 if len(scores)>1 and total else None
            rows.append({'label':f'{r} / {d}','value':round(margin,3) if margin is not None else None,'unit':'%p'})
        rows.sort(key=lambda x:(x['value'] is None,x['value'] if x['value'] is not None else 1000))
    elif method=='district_leader_share':
        for (r,d),cs in sums.items():
            total=sum(cs.values()); leader=max(cs.values()) if total else 0
            rows.append({'label':f'{r} / {d}', 'value':round(100*leader/total,3) if total else 0,'unit':'%'})
        rows.sort(key=lambda x:-x['value'])
    elif method=='lead_margin':
        for (r,d),cs in sums.items():
            scores=sorted(cs.values(),reverse=True)
            total=sum(scores)
            margin=(scores[0]-scores[1])/total*100 if len(scores)>1 and total else None
            rows.append({'label':f'{r} / {d}', 'value':round(margin,3) if margin is not None else None,'unit':'%p',
                         'status':'단독후보' if margin is None else '정상'})
        rows.sort(key=lambda x:(x['value'] is None,-(x['value'] or 0)))
    elif method=='margin_distribution':
        hist=Counter()
        for cs in sums.values():
            scores=sorted(cs.values(),reverse=True);tot=sum(scores)
            if tot and len(scores)>1:hist[min(9,int(100*(scores[0]-scores[1])/tot)//10)]+=1
        rows=[{'label':f'{i*10}~{(i+1)*10}%p','value':hist[i],'unit':'선거구'} for i in range(10)]
    else:
        amounts=[v['votes'] for v in relevant] if method=='candidate_vote_distribution' else list(district_totals.values())
        top=max(amounts) or 1
        width=max(1,math.ceil((top+1)/10)); hist=Counter(min(9,v//width) for v in amounts)
        unit='후보자-투표구 행' if method=='candidate_vote_distribution' else '선거구'
        rows=[{'label':f'{i*width}~{(i+1)*width-1}표','value':hist[i],'unit':unit} for i in range(10)]
    clean=[x for x in rows if x['value'] is not None]
    return {'mode':ds['mode'],'source_status':ds['source_status'],'verified':False,
            'source_url':ds['source_url'],'sha256':ds['sha256'],'method':method,'method_label':method_name[method],
            'region':region,'district':district,'rows':rows[:limit], 'all_rows':len(rows),
            'total_candidate_votes':sum(district_totals.values()),'scope_districts':len(sums),
            'caution':('교육용 가상 데이터이며 실제 선거 결과가 아닙니다. ' if ds['mode']=='SYNTHETIC_SAMPLE_NOT_OFFICIAL' else '') + '최종 결과 파일의 공간별 집계이며 당시 개표 진행 시간·실시간 개표율·실제 투표율·당선예측을 계산하지 않습니다. 자료는 사용자 업로드 원본과 별도 대조가 필요합니다.'}


def replay(ds:dict, region:str, district:str, stages:int=20) -> dict:
    _group(ds,region,district)
    if not region or not district:raise DataError('재생은 개별 선거구만 지원합니다.')
    if not isinstance(stages,int) or not 2<=stages<=50:raise DataError('단계 2~50')
    votes=[v for v in ds['votes'] if v['region']==region and v['district']==district]
    if not votes:raise DataError('해당 선거구 자료 없음')
    series=[]
    for v in votes:
        rng=random.Random(int(sha256((ds['sha256']+region+district+v['candidate']).encode()).hexdigest()[:16],16))
        weights=[rng.uniform(.3,2.0) for _ in range(stages)]
        s=sum(weights); raw=[v['votes']*w/s for w in weights]
        parts=[int(x) for x in raw]
        leftover=v['votes']-sum(parts)
        indexes=sorted(range(stages),key=lambda i:raw[i]-parts[i],reverse=True)
        for i in indexes[:leftover]:parts[i]+=1
        cum=0;points=[0]
        for p in parts:cum+=p;points.append(cum)
        series.append({'candidate':v['candidate'],'final_votes':v['votes'],'points':points})
    return {'mode':'SYNTHETIC_REPLAY_OF_FINAL_RESULTS','actual_counting_timestamps':False,
            'verified':False,'source_sha256':ds['sha256'],'region':region,'district':district,
            'stages':stages,'series':series,'notice':'개표 당시 시각별 기록이 없으므로, 최종 득표수만 이용해 난수로 증가 순서를 가상 재현했습니다. 실제 개표 추이·실시간 결과가 아닙니다.'}
