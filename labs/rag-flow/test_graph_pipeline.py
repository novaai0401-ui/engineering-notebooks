"""Actual model extraction, persisted provenance, Louvain communities, ACL and deletion."""
import json,secrets,time
from pathlib import Path
from graph_pipeline import GraphStore,extract
ROOT=Path(__file__).resolve().parent;RUN=ROOT.parents[1]/'.runtime'/('graph-pipeline-'+secrets.token_hex(4));RUN.mkdir()
docs=[{'id':'g1','owner':'public','text':'Atlas is maintained by Search.'},{'id':'g2','owner':'public','text':'Search is led by Noor.'},{'id':'g3','owner':'alice','text':'Vault is led by Sera.'}]
report={'passed':[],'limitations':'Small custom graph-RAG pipeline, not Microsoft GraphRAG. Actual model extraction; normalized exact-name resolution and extractive community summaries. Quote presence is provenance, not proof of relationship entailment. Three authored facts are reviewed by explicit expectations, not a broad extraction benchmark.'};began=time.monotonic()
try:
 edges,timings=extract(docs);report['extracted_edges']=edges;report['model_timings']=timings
 assert {(e['doc_id'],e['source'].casefold(),e['relation'],e['target'].casefold()) for e in edges}=={('g1','atlas','maintained_by','search'),('g2','search','led_by','noor'),('g3','vault','led_by','sera')}
 report['passed'].append('Actual local model extracted the three expected relationships from text')
 store=GraphStore(RUN/'graph.db')
 for doc in docs:store.ingest(doc,[e for e in edges if e['doc_id']==doc['id']])
 store=GraphStore(RUN/'graph.db');path=store.local('bob','ATLAS',2)
 assert [e['target'] for e in path]==['search','noor'] and all(e['digest'] for e in path)
 report['passed'].append('Reopened SQLite graph retains two-hop path and source hashes')
 assert not store.local('bob','Vault') and store.local('alice','Vault')[0]['target']=='sera'
 communities=store.communities('bob');assert len(communities)==1 and 'g3' not in json.dumps(communities) and 'Sera' not in json.dumps(communities)
 assert len(store.communities('alice'))==2
 report['communities_for_bob']=communities;report['passed'].append('Permission filtering precedes Louvain communities, summaries and local traversal')
 bad=dict(edges[0],quote='Invented support')
 try:store.ingest(docs[0],[bad])
 except ValueError:pass
 else:raise AssertionError('Invented provenance accepted')
 assert len(store.local('bob','Atlas'))==2
 store.ingest(dict(docs[1],owner='alice'),[e for e in edges if e['doc_id']=='g2'])
 assert len(store.local('bob','Atlas'))==1 and 'Noor' not in json.dumps(store.communities('bob'))
 report['passed'].append('Invalid support rejected atomically; permission change removes private derived summaries')
 store.delete('g2');assert len(store.local('alice','Atlas'))==1
 store.ingest(dict(docs[0],text='Atlas was retired.'),[]);assert not store.local('bob','Atlas')
 report['passed'].append('Document deletion cascades edges; changed source replaces old relationships')
 report['status']='passed'
except Exception as error:report.update(status='failed',error=type(error).__name__);raise
finally:
 report['seconds']=round(time.monotonic()-began,2);(ROOT/'graph-pipeline-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
