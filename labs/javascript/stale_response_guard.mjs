// lab: stale_response_guard
import assert from 'node:assert/strict';
let generation=0,display='';
function startRequest(){const mine=++generation;return value=>{if(mine===generation)display=value;};}
const finishOld=startRequest(),finishNew=startRequest();
finishNew('new answer');finishOld('old answer');
assert.equal(display,'new answer');
console.log('A generation check prevents an old response overwriting a newer one');
