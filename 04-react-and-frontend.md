# Notebook 4 — React and Frontend Engineering

Begin with the browser, then learn JavaScript, React state, data fetching, design, accessibility, and tests. The explanations are self-contained. JavaScript labs use Node; the delivered React project contains dependencies and tests. React is a UI library, not a complete authentication, database, or backend system.

## 1. The browser is a document machine

HTML describes meaning and structure. CSS describes presentation and layout. JavaScript describes behavior. The DOM is the browser's in-memory document tree. An HTTP request asks a server for a resource; a response contains status, headers, and usually a body.

A button should be a button rather than a clickable paragraph. A form label should identify its input. Semantic elements supply behavior to keyboard users and assistive technology. Visual appearance alone does not determine usability.

CSS selectors choose elements. The cascade, specificity, and source order determine applicable rules. The box model includes content, padding, border, and margin. Flexbox suits one-dimensional alignment; Grid suits two-dimensional layouts. Use responsive constraints instead of assuming every reader has your screen width.

**Practice:** Does styling a div to look like a button provide keyboard activation automatically? **Answer:** No. Prefer the real button element and preserve focus indication.

## 2. JavaScript essentials for React

`const` prevents rebinding a variable; it does not freeze an object. `let` allows rebinding. Arrays hold ordered values. Objects hold named properties. Destructuring extracts values. Spread makes a shallow copy or expands elements. Arrow functions are concise functions with lexical `this` behavior.

```javascript
// lab: immutable_update
import assert from 'node:assert/strict';
const oldItems = [{id:1, done:false}, {id:2, done:false}];
const newItems = oldItems.map(item =>
  item.id === 2 ? {...item, done:true} : item);
assert.equal(oldItems[1].done, false);
assert.equal(newItems[1].done, true);
assert.equal(newItems[0], oldItems[0]);
console.log('Changed item copied; original state preserved');
```

`map` creates a new array. The conditional replaces only the matching object. Spread copies that object's properties and `done:true` overrides one. Unchanged items retain their references. This supports predictable state updates without unnecessary deep copying.

`===` compares without coercing types. `null` is an explicit empty value; `undefined` often represents absence. Nullish coalescing `??` falls back for null or undefined, while `||` also falls back for other falsy values such as zero. Use the operator matching your intended meaning.

## 3. Closures, promises, and the event loop

A closure retains access to variables from an enclosing scope. A promise represents eventual completion or failure. `async` functions return promises. `await` pauses that function's continuation, not the whole JavaScript runtime. A long synchronous computation can still block UI responsiveness.

```javascript
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
```

`Promise.all` rejects if an input rejects but does not automatically cancel underlying work. `allSettled` collects each outcome. Neither creates unlimited safe concurrency; cap requests when needed. Fetch resolves for many HTTP error statuses, so inspect `response.ok` rather than treating every resolved fetch as business success.

## 4. React: describe what the screen should be

A component is commonly a function that produces a UI description from props and state. JSX is syntax for those descriptions, transformed by tooling. Props are inputs supplied by a parent. State is remembered information owned by a component or shared state layer. Re-rendering computes a new description; committing applies necessary changes. [Official React introduction](https://react.dev/learn).

Imagine a scoreboard: its display is a function of the score. You update the score, then React updates the view. Do not manually edit the score text and also expect state to remain the authority.

Rendering should be pure: the same inputs should not secretly send a payment or mutate shared data. Components can render more than you expect, including development checks. Put user-triggered work in event handlers and external synchronization in appropriate effects.

## 5. State is a snapshot, not a mutable notebook

An event handler closes over values from a particular render. Calling a setter schedules an update; it does not rewrite the handler's local variable. When the next value depends on the previous one, a functional update expresses that dependency: `setCount(previous => previous + 1)`.

Never mutate a state array with `push` and expect all update logic to remain correct. Create a new array and copy changed objects. Stable keys identify list items across updates; array position can be the wrong identity when items move or are removed. [Array update guidance](https://react.dev/learn/updating-arrays-in-state).

Derived values, such as completed-count from a task list, usually need not be separately stored. Duplicated state can disagree. Keep one authoritative representation and calculate inexpensive derived values during rendering.

**Practice:** Why can three calls to `setCount(count + 1)` in one handler behave differently from three functional updates? **Answer:** The first calls use the same captured snapshot; functional updates compose through queued previous values.

## 6. Reducers make state transitions visible

A reducer receives current state and an action and returns next state. Think of an action as a small labeled instruction: add item, toggle item, reset. It should not secretly perform network calls. Pure reducers are easy to test. React's `useReducer` connects that function to component updates. [API reference](https://react.dev/reference/react/useReducer).

### Lab: a complete local study list

The delivered project uses the following component. The source is included in the notebook; the JavaScript build and DOM interaction checks are recorded separately from standalone Node labs.

```jsx
// lab: StudyApp
import React, {useReducer, useState} from 'react';

export function reducer(state, action) {
  switch (action.type) {
    case 'add': {
      const title = action.title.trim();
      if (!title) return state;
      return [...state, {id:action.id, title, done:false}];
    }
    case 'toggle':
      return state.map(item => item.id === action.id
        ? {...item, done:!item.done} : item);
    default: return state;
  }
}

export default function StudyApp() {
  const [items, dispatch] = useReducer(reducer, []);
  const [title, setTitle] = useState('');
  const completed = items.filter(item => item.done).length;
  function submit(event) {
    event.preventDefault();
    if (!title.trim()) return;
    dispatch({type:'add', id:crypto.randomUUID(), title});
    setTitle('');
  }
  return <main>
    <h1>My study practice</h1>
    <form onSubmit={submit}>
      <label htmlFor="topic">Topic to practice</label>
      <input id="topic" value={title}
        onChange={event => setTitle(event.target.value)} />
      <button type="submit" disabled={!title.trim()}>Add topic</button>
    </form>
    <p role="status">{completed} of {items.length} completed</p>
    <ul>{items.map(item => <li key={item.id}>
      <label><input type="checkbox" checked={item.done}
        onChange={() => dispatch({type:'toggle', id:item.id})} />
        {item.title}</label>
    </li>)}</ul>
  </main>;
}
```

The imports name React and the two hooks. `reducer` is a normal function. The add case trims text and appends a new item; toggle copies only the affected item. The component stores items and the controlled input's text. Completed count is derived rather than duplicated.

Submitting prevents the browser's default form navigation, creates a stable identity at action time, and dispatches an action. The input's value follows state and its event handler updates state. A label names the field; the button has a clear role; checkboxes provide native keyboard behavior. The status paragraph reports progress. This local app intentionally does not persist across refresh or claim backend authorization.

## 7. Effects synchronize with outside systems

Effects are for synchronizing with things outside rendering, such as subscriptions or a network connection. Dependencies describe reactive values used by the effect; suppressing dependency checks to force a desired schedule can capture stale values. Cleanup disconnects or invalidates the previous synchronization. [Effect guidance](https://react.dev/learn/synchronizing-with-effects).

### Integration recipe: handle a changing query

```jsx recipe
useEffect(() => {
  const controller = new AbortController();
  let active = true;
  setStatus('loading');
  fetch(`/api/search?q=${encodeURIComponent(query)}`, {
    signal: controller.signal
  }).then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }).then(data => {
    if (active) { setResults(data.items); setStatus('ready'); }
  }).catch(error => {
    if (active && error.name !== 'AbortError') setStatus('error');
  });
  return () => { active = false; controller.abort(); };
}, [query]);
```

This fragment assumes surrounding state and a defined search endpoint; it is not a standalone component. Abort requests cancellation. The active flag also prevents obsolete results from updating this component. Query encoding preserves URL structure. A production response needs runtime schema validation and a user-facing error policy. Framework data-loading facilities may handle caching and races more systematically.

Development Strict Mode can exercise extra setup/cleanup behavior to reveal bugs. Do not “fix” duplicate development observations by hiding missing cleanup. [useEffect reference](https://react.dev/reference/react/useEffect).

## 8. Hooks, context, refs, and component design

Hooks must follow their documented call rules so React can associate state with the right component execution. Custom hooks package reusable stateful logic; they do not share one global state merely because two components call the same hook.

Context passes a value through a subtree without manually forwarding every prop. It is useful for themes or bounded shared concerns, but every rapidly changing value does not belong in one giant provider. State ownership should follow who reads and updates it.

A ref remembers a mutable value without triggering a render when changed. Use it for appropriate imperative handles or values that should not drive the visible UI. `useMemo` caches a computed value and `useCallback` a function identity under dependency rules; they are performance tools, not correctness guarantees. Measure before adding them everywhere.

Prefer small components with clear props and composition. A presentational component can receive data and callbacks while a boundary component coordinates fetching. Avoid a rigid rule that every component must be split in two; use boundaries that clarify responsibilities.

## 9. TypeScript and boundary contracts

TypeScript checks types during development; the resulting JavaScript still receives real runtime data. A type assertion does not validate a server response. Parse and validate at the boundary.

```typescript recipe
type LoadState<T> =
  | {status:'loading'}
  | {status:'ready'; data:T}
  | {status:'error'; message:string};

function label(state: LoadState<string[]>): string {
  if (state.status === 'ready') return `${state.data.length} items`;
  if (state.status === 'error') return state.message;
  return 'Loading';
}
```

The status field discriminates the allowed shape. Loading cannot accidentally carry a required success payload. This reduces impossible state combinations. Generics let the same state structure describe different payload types. Compile-time narrowing helps code clarity; server identity, permissions, and semantic validity still need checks.

## 10. Routing, rendering modes, and data ownership

A router maps locations to UI. Put shareable navigation state in the URL when appropriate, such as search filters and selected resource IDs. Local transient input need not become a URL parameter. Protect routes for user experience, but enforce authority on the server regardless of hidden links.

Client-side rendering builds much UI in the browser. Server-side rendering sends rendered markup; hydration connects client behavior to compatible server output. Static generation prepares markup ahead of time. Server Components and streaming depend on the chosen supporting framework and boundary rules; they are not simply a flag that makes every component run everywhere.

Avoid sending secrets in client bundles. Any code or credential delivered to the browser should be considered accessible to its user. SSR does not automatically fix authorization or malicious HTML. Escape data appropriately and avoid inserting untrusted HTML without a justified sanitization design.

## 11. Forms, accessibility, and useful failure states

Every data-dependent view needs loading, empty, error, and success states. A blank panel gives no useful explanation. Keep previous data only when its staleness is clear. Disable duplicate submissions while also making the server robust to retries; a disabled button is not an idempotency mechanism.

Forms need labels, clear errors, appropriate input types, and focus behavior. Keyboard navigation, visible focus, contrast, and screen-reader names matter. Announce important asynchronous status changes without repeatedly interrupting the user. Tables need meaningful headers; icons need text alternatives when they convey meaning.

For AI chat, distinguish generated text from verified tool results. Show citations, tool progress, and recoverable errors without exposing secrets or unnecessary implementation details. Streaming partial output is not final success.

## 12. Performance and testing

Measure bundle size, render cost, network waterfalls, and user-perceived latency. Code splitting can defer unused modules. Virtualizing long lists reduces rendered elements but requires careful focus and accessibility behavior. Debouncing waits for a pause before work; throttling limits frequency. Cancel or ignore obsolete requests rather than letting old responses overwrite new input.

Unit-test pure reducers and utilities. Component tests interact through labels, roles, and visible behavior. Integration tests exercise API contracts. Browser tests cover real navigation and crucial journeys. Snapshot tests alone cannot demonstrate keyboard operability or correct network races.

The delivered project checks adding and completing a topic in a DOM test environment and produces a bundled static page. A DOM simulation does not replace cross-browser testing, screen-reader review, or a complete accessibility audit.

## 13. Frontend architecture and capstone

Organize by feature when it keeps related UI, validation, API calls, and tests together. Use a small shared design system for repeatable controls. Keep domain contracts separate from provider-specific transport details. Avoid a global mutable object that every component can change.

Capstone: a study dashboard with topics, completion status, search, and an AI explanation panel. The React layer owns display and input state. Java owns users and persisted study records. Python owns model inference or retrieval. The frontend receives a documented result structure and handles errors explicitly. Notebook 5 explains the full request path.

## 14. Interview practice

**Props versus state?** Props are inputs supplied by a parent; state is remembered information owned by a component or state layer.

**Why stable keys?** They help match item identity across list changes; incorrect keys can attach local state to the wrong item.

**Why no direct mutation?** It undermines predictable change tracking and can alter prior snapshots shared by other code.

**Effect versus event?** An event handles a particular interaction; an effect synchronizes after rendering with an external system.

**Does TypeScript validate an API payload?** No, runtime checks are still needed.

**Does Promise.all cancel work on failure?** Not automatically; define cancellation separately.

**Why avoid derived duplicate state?** Multiple representations can become inconsistent.

**Coverage:** Detailed foundations cover browser structure, JavaScript, state, reducers, effects, component design, TypeScript concepts, accessibility, rendering choices, performance, and tests. Advanced framework-specific routing internals, compiler implementation, every third-party state library, and all CSS specifications are outside a finite introductory workbook.


Advanced continuation: [11-react-depth](11-react-depth.html). The advanced workshop and accompanying projects extend the introductory scope described above.
