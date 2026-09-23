// src/StudyApp.jsx
import React, { useReducer, useState } from "react";
function reducer(state, action) {
  switch (action.type) {
    case "add": {
      const title = action.title.trim();
      if (!title) return state;
      return [...state, { id: action.id, title, done: false }];
    }
    case "toggle":
      return state.map((item) => item.id === action.id ? { ...item, done: !item.done } : item);
    default:
      return state;
  }
}
function StudyApp() {
  const [items, dispatch] = useReducer(reducer, []);
  const [title, setTitle] = useState("");
  const completed = items.filter((item) => item.done).length;
  function submit(event) {
    event.preventDefault();
    if (!title.trim()) return;
    dispatch({ type: "add", id: crypto.randomUUID(), title });
    setTitle("");
  }
  return /* @__PURE__ */ React.createElement("main", null, /* @__PURE__ */ React.createElement("h1", null, "My study practice"), /* @__PURE__ */ React.createElement("form", { onSubmit: submit }, /* @__PURE__ */ React.createElement("label", { htmlFor: "topic" }, "Topic to practice"), /* @__PURE__ */ React.createElement(
    "input",
    {
      id: "topic",
      value: title,
      onChange: (event) => setTitle(event.target.value)
    }
  ), /* @__PURE__ */ React.createElement("button", { type: "submit", disabled: !title.trim() }, "Add topic")), /* @__PURE__ */ React.createElement("p", { role: "status" }, completed, " of ", items.length, " completed"), /* @__PURE__ */ React.createElement("ul", null, items.map((item) => /* @__PURE__ */ React.createElement("li", { key: item.id }, /* @__PURE__ */ React.createElement("label", null, /* @__PURE__ */ React.createElement(
    "input",
    {
      type: "checkbox",
      checked: item.done,
      onChange: () => dispatch({ type: "toggle", id: item.id })
    }
  ), item.title)))));
}
export {
  StudyApp as default,
  reducer
};
