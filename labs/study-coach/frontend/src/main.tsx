import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
type Job={id:string;owner:string;question:string;status:string;answer:string;attempt:number;error:string};
type Session={authorization?:string;csrf:{header:string;token:string;parameter?:string}};
const terminal=(job:Job)=>['done','failed','cancelled'].includes(job.status);
function App(){
 const [session,setSession]=useState<Session|null>(null),[user,setUser]=useState('alice'),[password,setPassword]=useState('');
 const [question,setQuestion]=useState('What is a checkpoint?'),[job,setJob]=useState<Job|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [route,setRoute]=useState(location.hash||'#learn');const stream=useRef<AbortController|null>(null);
 const [authMode,setAuthMode]=useState('basic');
 useEffect(()=>{let active=true;void(async()=>{try{const config=await(await fetch('/config')).json();if(!active)return;setAuthMode(config.authMode);if(config.authMode==='oidc'){const me=await fetch('/api/me');if(me.ok){const who=await me.json();const response=await fetch('/api/csrf');if(response.ok&&active){setUser(who.user);setSession({csrf:await response.json()});}}}}catch{if(active)setError('Unable to load sign-in configuration.');}})();return()=>{active=false;};},[]);
 useEffect(()=>{const change=()=>setRoute(location.hash||'#learn');window.addEventListener('hashchange',change);return()=>window.removeEventListener('hashchange',change);},[]);
 useEffect(()=>()=>stream.current?.abort(),[]);
 async function request(path:string,method='GET',body?:unknown,key?:string){
  if(!session)throw Error('Please sign in');
  const response=await fetch(path,{method,headers:{...(session.authorization?{Authorization:session.authorization}:{}),[session.csrf.header]:session.csrf.token,'Content-Type':'application/json',...(key?{'Idempotency-Key':key}:{})},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok)throw Error(`Request failed (${response.status}). Check permissions, input, or sign in again.`);
  return response.json();
 }
 async function watch(id:string){
  stream.current?.abort();const controller=new AbortController();stream.current=controller;
  if(!session)return;
  try{
   const response=await fetch(`/api/jobs/${id}/events`,{headers:session.authorization?{Authorization:session.authorization}:{},signal:controller.signal});
   if(!response.ok||!response.body)throw Error('Cannot open answer stream');
   const reader=response.body.getReader(),decoder=new TextDecoder();let pending='';
   while(true){const {done,value}=await reader.read();if(done)break;pending+=decoder.decode(value,{stream:true}).replace(/\r\n/g,'\n');
    let end;while((end=pending.indexOf('\n\n'))>=0){const frame=pending.slice(0,end);pending=pending.slice(end+2);
     const data=frame.split('\n').filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trimStart()).join('\n');if(data&&!controller.signal.aborted)setJob(JSON.parse(data) as Job);
    }
   }
  }catch(e){if(!controller.signal.aborted)setError(String(e));}
 }
 async function action(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn();}catch(e){setError(String(e));}finally{setBusy(false);}}
 return <main><h1>Study Coach</h1><p>Learn from authorized evidence, with approval and a durable background job.</p><nav aria-label="Main"><a href="#learn">Learn</a><a href="#architecture">Architecture</a></nav>
 {route==='#architecture'?<section><h2>Follow one question</h2><p>React → authenticated Spring API → durable job → Python evidence retrieval → optional local model → streamed answer → React.</p><p>Extractive mode quotes evidence. Ollama mode generates a draft with citation checks; verify its meaning. Restart recovery depends on retaining the configured database.</p></section>:<section><h2>Your learning session</h2>
 {!session?(authMode==='oidc'?<p><a href="/oauth2/authorization/coach">Sign in with identity provider</a></p>:<form onSubmit={e=>{e.preventDefault();void action(async()=>{const authorization='Basic '+btoa(user+':'+password);const r=await fetch('/api/csrf',{headers:{Authorization:authorization}});if(!r.ok)throw Error('Sign-in failed');setSession({authorization,csrf:await r.json()});setPassword('');});}}>
 <label htmlFor="username">Learner</label><input id="username" value={user} onChange={e=>setUser(e.target.value)} autoComplete="username" required/>
 <label htmlFor="password">Password</label><input id="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password" required/>
 <button disabled={busy}>Sign in</button></form>):<><p>Signed in as {user}. {authMode==='oidc'?'Your browser uses a server-managed session.':"Credentials are kept in this page's memory."}</p>{authMode==='oidc'?<form action="/logout" method="post"><input type="hidden" name={session.csrf.parameter||'_csrf'} value={session.csrf.token}/><button>Sign out of identity session</button></form>:<button onClick={()=>{stream.current?.abort();setSession(null);setJob(null);}}>Forget page credentials</button>}
 <form onSubmit={e=>{e.preventDefault();void action(async()=>{stream.current?.abort();setJob(await request('/api/jobs','POST',{question},crypto.randomUUID()));});}}>
 <label htmlFor="question">Study question</label><textarea id="question" value={question} onChange={e=>setQuestion(e.target.value)} maxLength={500} required/><button disabled={busy}>Create study job</button></form>
 {job&&<article><h3>Question: {job.question}</h3><p className="status" role="status">Status: {job.status}; attempt: {job.attempt}</p>
 {job.status==='approval'&&<button disabled={busy} onClick={()=>void action(async()=>{const updated=await request(`/api/jobs/${job.id}/approve`,'POST');setJob(updated);void watch(job.id);})}>Approve question</button>}
 {!terminal(job)&&<button disabled={busy} onClick={()=>void action(async()=>{setJob(await request(`/api/jobs/${job.id}/cancel`,'POST'));})}>Cancel job</button>}
 <button disabled={busy} onClick={()=>void action(async()=>{const updated=await request(`/api/jobs/${job.id}`) as Job;setJob(updated);if(!terminal(updated))void watch(job.id);})}>Refresh and reconnect</button>
 <h3>Evidence-based answer</h3><p>{job.answer||'No answer yet.'}</p>{job.error&&<p className="error">{job.error}</p>}<small>Job ID: {job.id}. Refreshing the page clears its selection, but the job remains in the database.</small></article>}</>}
 </section>}{error&&<p role="alert" className="error">{error}</p>}<footer><p>Local teaching application. Sources are a small built-in, permission-filtered collection.</p></footer></main>;
}
createRoot(document.getElementById('root')!).render(<App/>);
