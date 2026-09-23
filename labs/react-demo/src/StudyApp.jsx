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
