// lab: immutable_update
import assert from 'node:assert/strict';
const oldItems = [{id:1, done:false}, {id:2, done:false}];
const newItems = oldItems.map(item =>
  item.id === 2 ? {...item, done:true} : item);
assert.equal(oldItems[1].done, false);
assert.equal(newItems[1].done, true);
assert.equal(newItems[0], oldItems[0]);
console.log('Changed item copied; original state preserved');
