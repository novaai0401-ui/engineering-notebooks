// lab: promises
import assert from 'node:assert/strict';
const double = async value => value * 2;
const values = await Promise.all([double(2), double(3)]);
assert.deepEqual(values, [4,6]);
const outcomes = await Promise.allSettled([
  Promise.resolve('ok'), Promise.reject(new Error('unavailable'))
]);
assert.equal(outcomes[1].status, 'rejected');
console.log('Results and partial failures are explicit');
