// lab: event_loop_order
import assert from 'node:assert/strict';
const events=[];
events.push('sync-start');
Promise.resolve().then(()=>events.push('microtask'));
const timer=new Promise(resolve=>setTimeout(()=>{events.push('timer');resolve();},0));
events.push('sync-end');
await timer;
assert.deepEqual(events,['sync-start','sync-end','microtask','timer']);
console.log(events.join(' -> '));
