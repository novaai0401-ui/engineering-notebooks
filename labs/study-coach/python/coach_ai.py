"""Permission-filtered retrieval with optional real local model generation."""
import asyncio
import hmac
import json
import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from telemetry import TraceMiddleware
from prometheus_client import generate_latest,CONTENT_TYPE_LATEST
from fastapi.responses import Response

SERVICE_TOKEN = os.environ['COACH_SERVICE_TOKEN']
MODE = os.getenv('COACH_AI_MODE','extractive')
app = FastAPI(title='Study Coach evidence service')
app.add_middleware(TraceMiddleware)
DOCUMENTS = [
    ('checkpoint', 'public', 'A checkpoint saves workflow state so a process can resume after a restart. Side effects still need idempotency keys.'),
    ('transaction', 'public', 'A transaction commits related database changes together or rolls them back. Isolation controls concurrent observations.'),
    ('react-state', 'public', 'React state is a snapshot for one render. A functional state update receives the pending state and avoids stale closure updates.'),
    ('alice-plan', 'alice', 'Alice private plan: practice graph traversal and approval workflows on Tuesday.'),
    ('bob-plan', 'bob', 'Bob private plan: practice database transactions and Java concurrency on Friday.'),
]

def retrieve(question: str, user: str):
    allowed = [item for item in DOCUMENTS if item[1] in ('public', user)]
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform([item[2] for item in allowed])
    scores = (matrix @ vectorizer.transform([question]).T).toarray().ravel()
    ranked = sorted(zip(scores, allowed), key=lambda item: (-item[0], item[1][0]))
    return [{'id': item[0], 'text': item[2], 'score': float(score)}
            for score, item in ranked[:2] if score > 0]

class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    user: str = Field(min_length=1,max_length=80,pattern='^[a-zA-Z0-9._-]+$')

@app.get('/metrics')
def metrics(authorization:str=Header(default='')):
    if not hmac.compare_digest(authorization,'Bearer '+SERVICE_TOKEN):raise HTTPException(401,'service credential required')
    return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)

@app.get('/health')
def health():
    return {'status': 'up', 'mode': MODE}

@app.post('/answer')
async def answer(body: Question, authorization: str = Header(default='')):
    if not hmac.compare_digest(authorization, 'Bearer '+SERVICE_TOKEN):
        raise HTTPException(401, 'service credential required')
    evidence = retrieve(body.question.strip(), body.user)
    if MODE=='ollama':
        from ollama_agent import generate_evidence
        async def generated():
            try:
                async for event in generate_evidence(body.question,evidence):
                    yield json.dumps(event)+'\n'
            except (ValueError,TimeoutError) as error:
                yield json.dumps({'error':'generation or citation validation failed'})+'\n'
        return StreamingResponse(generated(),media_type='application/x-ndjson')
    text = (' '.join(f"[{x['id']}] {x['text']}" for x in evidence)
            if evidence else 'No supporting evidence was found in your authorized documents.')
    async def chunks():
        for word in text.split():
            yield json.dumps({'delta': word+' '})+'\n'
            await asyncio.sleep(0.025)
        yield json.dumps({'done': True, 'sources': [x['id'] for x in evidence]})+'\n'
    return StreamingResponse(chunks(), media_type='application/x-ndjson')
