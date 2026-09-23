"""Optional cached-weight encoder; authorization must select docs before construction."""
from functools import lru_cache
@lru_cache(maxsize=1)
def model():
 import torch
 from sentence_transformers import SentenceTransformer
 torch.set_num_threads(2)
 return SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2',local_files_only=True,device='cpu')
class Index:
 def __init__(self,docs):
  self.docs=docs
  self.vectors=model().encode([d['text'] for d in docs],normalize_embeddings=True) if docs else None
 def rank(self,query,docs):
  if [d['id'] for d in docs]!=[d['id'] for d in self.docs]:raise ValueError('Do not reuse an index across authorization scopes')
  if not docs:return []
  scores=self.vectors@model().encode(query,normalize_embeddings=True)
  return sorted([(d['id'],float(s)) for d,s in zip(docs,scores)],key=lambda x:(-x[1],x[0]))
