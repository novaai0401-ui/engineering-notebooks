# 21 — Practice that measures understanding

## 1. Reading is rehearsal, answering is evidence

Watching someone ride a bicycle is different from balancing one yourself. Reading a correct answer creates familiarity; producing it under a new constraint tests understanding. This workbook gives timed tasks, answer keys and scoring rules. Your personal readiness remains unassessed until you submit your own answers. No tutor can honestly promise that every exam will be easy.

Use the earlier foundation books when you cannot explain a prerequisite. Use the advanced projects when you can explain a concept but cannot implement or debug it. Keep an error notebook: mistaken assumption, smallest counterexample, corrected rule and a new test.

## 2. Choose a route

Full-stack AI: Python and JavaScript foundations → HTTP and SQL → Java/Spring → React → retrieval and agents → identity and distributed project → system-design rounds. AI/ML: Python → probability and linear algebra → classical ML → deep learning → retrieval/generation → evaluation and deployment. Java backend: language/JVM/concurrency → SQL/JPA/transactions → security/messaging → distributed recovery. React: JavaScript/event loop → TypeScript → state/rendering → accessibility/testing → API integration.

These are prerequisite orders, not rigid calendars. Spend more time where your diagnostic scores are weak. A beginner should build small programs before attempting a multi-service deployment. An experienced engineer should demonstrate unfamiliar failure cases rather than reread only comfortable material.

## 3. Diagnostic: 30 minutes, 20 points

Answer before reading the key. Question one, four points: an order commits, the HTTP response is lost and the customer retries. How do you prevent duplicate orders? Question two, four points: why can two concurrent transactions violate “at least one doctor on call” while updating different rows? Question three, four points: a model returns a valid JSON tool call with another person's user ID; what must the server do? Question four, four points: a React component subscribes to a stream and unmounts; what cleanup and stale-response defenses are needed? Question five, four points: derive the gradient of (wx-y)²/2 with respect to w.

Key one: stable idempotency key, uniqueness scoped to caller, payload binding, atomic creation and stored outcome; reconcile an ambiguous result. Key two: write skew; shared invariant; appropriate lock or serializable isolation; retry full transaction. Key three: ignore model-supplied identity, derive it from authentication, validate schema and authorization, reject forbidden tools or arguments. Key four: abort/close subscription, effect cleanup, avoid updates from obsolete request identity, test unmount and route/session changes. Key five: (wx-y)x, with a correct chain-rule explanation and numeric check.

Award one point per named key component, with a maximum of four per question. A memorized phrase without an explanation receives at most half credit. Scores 0–8 suggest prerequisite work; 9–14 suggest targeted practice; 15–20 suggest progressing to timed implementation. These are study bands, not a prediction of a hiring decision.

## 4. Coding round: sliding window, 25 minutes

Task: given a string, return the length of its longest substring without repeated characters. Explain a brute-force baseline and improve it. Include empty input and repeated characters. Do not assume ASCII unless the problem says so; Python strings iterate code points, which are not always complete user-perceived grapheme clusters.

Baseline: enumerate substrings and check duplicates, O(n³) with repeated scanning or O(n²) using a growing set per start. Improved: keep the current window's left boundary and last-seen index for each character. When a repeat lies inside the window, move left past it. Never move left backwards.

```python
# lab: assessed_sliding_window
def longest_unique(text):
    last={};left=0;best=0
    for right,c in enumerate(text):
        left=max(left,last.get(c,-1)+1);last[c]=right
        best=max(best,right-left+1)
    return best
for text,expected in [('',0),('abba',2),('abcabcbb',3),('aaaa',1),('你好你',2)]:
    assert longest_unique(text)==expected
print('Five edge cases passed; O(n) expected time under hash-table assumptions.')
```

Rubric, ten points: two for explaining the invariant, three for correct code, two for edge tests, one for complexity assumptions, two for clearly comparing the baseline. Follow-up: return the actual substring; then process a stream where you cannot retain the entire input.

## 5. Debugging round: transaction proxy, 15 minutes

A Spring service gains `@Transactional`. Tests that access its package-visible `db` field suddenly see null, although its methods work. Diagnose before adding null checks.

Answer: Spring may inject a proxy. Direct field access is not a proxied method invocation, and proxy instance fields are not necessarily the target object's initialized fields. Inject the required repository directly into each collaborator or expose an appropriate method; do not reach through another service's fields. Also remember that self-invocation can bypass proxy-based advice. The expanded Study Coach work encountered this real defect and replaced direct collaborator-field access.

Score five points for explaining proxy versus target, two for a principled dependency fix, two for testing transaction rollback and one for mentioning self-invocation. “Initialize the field again” does not address the design issue.

## 6. System-design round: agent with approval, 40 minutes

Design an agent that reads an invoice and proposes a payment, but must wait for a human before paying. Define the immutable proposal content and its hash. Approval binds to that exact proposal, not whatever the model writes later. Recheck permissions and current business constraints at execution time. Persist workflow version, state, approval actor and time. Use an idempotent payment operation and reconcile ambiguous timeouts.

Address parallel document analysis without allowing concurrent payment execution. Separate read-only tools from irreversible tools. Explain checkpoint migration if a workflow changes while approvals are pending. Define cancellation before and after the external payment boundary. Include audit data without storing unnecessary sensitive content.

Rubric out of 20: four for state and approval binding; four for authentication/authorization; four for idempotency and crash recovery; four for evaluation, monitoring and budgets; four for tradeoffs and clear communication. An attractive architecture drawing without a failure model is incomplete.

## 7. ML round: a suspiciously excellent classifier

Your model reaches 99% validation accuracy but performs poorly after launch. List hypotheses and tests. Look for target leakage, duplicate entities across splits, temporal leakage, label noise, population shift, incorrect preprocessing at serving time and an imbalanced target where accuracy hides failures. Compare a simple baseline and inspect precision/recall at the actual decision threshold.

A good answer first verifies the evaluation design. It does not immediately demand a larger neural network. Split by the relevant unit—patient, customer or time—before fitting preprocessing. Evaluate probability calibration if decisions depend on estimated risk. Measure subgroup performance only with appropriate sample sizes and privacy constraints.

## 8. React round: stale search results

The user types A, then AB. Request AB returns first; request A returns later and overwrites the screen. Debouncing may reduce requests but does not prove correctness. Abort obsolete work when possible and guard result application with the current request identity. A cancelled network operation can still race with a completion already queued.

Follow-up: how do you distinguish loading initial data from refreshing existing data? Preserve useful existing results while clearly marking stale or refreshing state. Do not show placeholder data as current fact. Test keyboard focus, error announcements and retry behavior, not just a snapshot of successful markup.

## 9. An honest readiness record

For every attempt record the prompt, time limit, your answer before help, score by criterion, mistakes and retest date. Reattempt a related but different problem after two days and again after a week. Track unaided explanation, implementation, debugging and design separately. One total score can hide a serious weakness.

To receive personal grading, send your diagnostic answers and preferred role. Until then, the supplied keys and rubrics are ready, but a personalized score or claim that you are interview-ready would be fabricated.
