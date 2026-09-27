# Experiments without sliders

These examples provide the essential reasoning of the HTML experiments. PDF and EPUB do not execute browser code. Notes and progress are not synchronized across formats.

## Predict a gradient step
For points (1,2) and (2,4), start w=0 and b=0 in prediction=w*x+b. Mean squared loss is 10. The gradients are -10 and -6. At learning rate 0.1, w becomes 1 and b becomes 0.6. Predictions become 1.6 and 2.6; loss becomes 1.06. At rate 0.6, w=6 and b=3.6; predictions are 9.6 and 15.6, so loss is 96.16. A larger step can overshoot. Neither result establishes performance on unseen data.

## Trace binary search
Array [2,4,4,9,13], target 4. Maintain [lo,hi). Start [0,5). Midpoint 2 has value 4: keep it by setting hi=2. Midpoint 1 has 4: set hi=1. Midpoint 0 has 2: set lo=1. Result is index 1. For target 14 the result is index 5, a no-match position; do not dereference it.

## Predict a retry
The worker stores pending operation PAY-17. The receiver commits one payment. The worker crashes before recording completion, then retries PAY-17. With atomic receiver deduplication, it receives the old receipt and charges remain 1. Without deduplication, charges can become 2. A workflow checkpoint is not a payment receipt.

## Calculate average in-flight work
For a stable system, L=lambda*W. At 80 arrivals per second and average time 0.25 seconds, average in-flight work is 20. At 0.5 seconds it is 40. This average accounting identity is not a prediction of latency percentiles or proof of stability.

## Seven questions before moving on
1. What problem does this solve? Give an everyday example.
2. Can I define each prerequisite and technical term?
3. Can I trace the inputs, intermediate states, and outputs?
4. Why does it work, and under which assumptions?
5. Can I explain implementation, edge cases, failures, and debugging?
6. When is an alternative better?
7. Can I solve a fresh exercise and explain the answer without hints?

The checklist is an acceptance standard, not proof that every topic has already passed editorial review. Executable lab results, classroom examples, and production acceptance are different evidence categories. This edition preserves those distinctions.
