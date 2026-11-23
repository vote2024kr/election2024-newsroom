"""TF-IDF sparse-document retrieval for local synthetic evidence.
Not LangChain, not generative, not external official facts. All hits retain evidence IDs.
"""
import json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
DOC_PATH=Path(__file__).parent/'newsroom'/'data'/'mock_documents.json'

def search(question:str,k:int=4):
    if not 2<=len(question.strip())<=300:
        raise ValueError('질문은 2~300글자')
    if not 1<=k<=10:raise ValueError('검색 문서 수는 1~10건')
    records=json.loads(DOC_PATH.read_text(encoding='utf-8'))
    bodies=[r['title']+' '+r['text'] for r in records]
    matrix=TfidfVectorizer(analyzer='char',ngram_range=(2,4),min_df=1,sublinear_tf=True).fit_transform(bodies+[question])
    sims=cosine_similarity(matrix[-1],matrix[:-1]).ravel()
    ranked=sorted(range(len(records)),key=lambda j:-sims[j])
    out=[]
    for j in ranked[:k]:
        if sims[j]<0.02:continue
        d=records[j]
        out.append({'id':d['id'],'title':d['title'],'publisher':d['publisher'],
                    'published':d['published'],'type':d['type'],
                    'text':d['text'],'similarity':round(float(sims[j]),4),
                    'origin':'SIMULATED_REFERENCE_ONLY','externally_verified':False})
    return {'mode':'offline_tfidf_sparse_vector','generator':'none',
       'warning':'교육용 문서만 검색합니다. 실제 선거 공식 출처, LangChain, LLM을 연결하지 않았습니다.',
       'question':question,'results':out,'count':len(out),'insufficient_evidence':not bool(out)}
