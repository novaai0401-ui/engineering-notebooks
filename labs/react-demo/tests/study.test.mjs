import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
const dom = new JSDOM('<!doctype html><html><body></body></html>', {url:'http://localhost/'});
globalThis.window = dom.window;
globalThis.document = dom.window.document;
Object.defineProperty(globalThis, 'navigator', {value:dom.window.navigator, configurable:true});
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.Node = dom.window.Node;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const React = await import('react');
const {render,screen,cleanup} = await import('@testing-library/react');
const {default:userEvent} = await import('@testing-library/user-event');
const {default:StudyApp,reducer} = await import('../dist/StudyApp.mjs');

test('reducer preserves previous state and rejects blank input',()=>{
  const previous=[{id:'1',title:'Agents',done:false}];
  const next=reducer(previous,{type:'toggle',id:'1'});
  assert.equal(previous[0].done,false);
  assert.equal(next[0].done,true);
  assert.equal(reducer(previous,{type:'add',id:'2',title:'  '}),previous);
});

test('learner adds and completes a topic through accessible controls',async()=>{
  const user=userEvent.setup({document:dom.window.document});
  render(React.createElement(StudyApp));
  try {
    assert.equal(screen.getByRole('button',{name:'Add topic'}).disabled,true);
    await user.type(screen.getByLabelText('Topic to practice'),'LangGraph');
    await user.click(screen.getByRole('button',{name:'Add topic'}));
    assert.equal(screen.getByRole('status').textContent,'0 of 1 completed');
    await user.click(screen.getByRole('checkbox',{name:'LangGraph'}));
    assert.equal(screen.getByRole('status').textContent,'1 of 1 completed');
    assert.equal(screen.getByLabelText('Topic to practice').value,'');
  } finally {cleanup();}
});
