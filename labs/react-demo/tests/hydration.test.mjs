import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import React,{act,useState} from 'react';
import {renderToString} from 'react-dom/server';
test('matching server markup hydrates and becomes interactive',async()=>{
 function Counter({initial}){const [count,setCount]=useState(initial);return React.createElement('button',{onClick:()=>setCount(c=>c+1)},`Count ${count}`);}
 const html=renderToString(React.createElement(Counter,{initial:1}));
 const dom=new JSDOM('<!doctype html><html><body><div id="app">'+html+'</div></body></html>',{url:'http://localhost'});
 globalThis.window=dom.window;globalThis.document=dom.window.document;
 Object.defineProperty(globalThis,'navigator',{value:dom.window.navigator,configurable:true});
 globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const {hydrateRoot}=await import('react-dom/client');const errors=[];let root;
 await act(async()=>{root=hydrateRoot(document.getElementById('app'),React.createElement(Counter,{initial:1}),{onRecoverableError:e=>errors.push(e)});});
 await act(async()=>{document.querySelector('button').dispatchEvent(new dom.window.MouseEvent('click',{bubbles:true}));});
 assert.equal(document.querySelector('button').textContent,'Count 2');assert.deepEqual(errors,[]);
 await act(async()=>root.unmount());dom.window.close();
});
