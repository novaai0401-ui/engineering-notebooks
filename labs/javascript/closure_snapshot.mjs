// lab: closure_snapshot
import assert from 'node:assert/strict';
function makeRender(count){return {later:()=>count,increment:previous=>previous+1};}
const first=makeRender(0),second=makeRender(1);
assert.equal(first.later(),0);assert.equal(second.later(),1);
const updates=[first.increment,first.increment,first.increment];
assert.equal(updates.reduce((value,update)=>update(value),0),3);
console.log('Old callbacks retain their render binding; functional updates compose');
