import { useEffect, useRef, useState } from 'react'
import { api } from './api.js'

/** Shared grocery list: anyone adds from the wall or a phone; tap to check off. */
export default function GroceryList({ version }) {
  const [items, setItems] = useState([])
  const [text, setText] = useState('')
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const load = () => api.grocery().then(setItems).catch((e) => setError(e.message))
  useEffect(() => {
    load()
  }, [version])

  async function act(fn) {
    setError(null)
    try {
      await fn()
    } catch (e) {
      setError(e.message)
    }
    load()
  }

  async function add(e) {
    e.preventDefault()
    const value = text.trim()
    if (!value) return
    setText('')
    await act(() => api.addGrocery(value))
    inputRef.current?.focus()
  }

  // Optimistic toggle so the tap feels instant
  function toggle(item) {
    setItems((list) => list.map((i) => (i.id === item.id ? { ...i, done: !i.done } : i)))
    act(() => api.updateGrocery(item.id, { done: !item.done }))
  }

  const open = items.filter((i) => !i.done)
  const done = items.filter((i) => i.done)

  return (
    <main className="grocery">
      <form className="grocery-add" onSubmit={add}>
        <input
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Add an item…"
          maxLength={120}
          enterKeyHint="done"
        />
        <button type="submit" className="primary">Add</button>
      </form>
      {error && <p className="error">{error}</p>}

      <div className="grocery-list">
        {open.length === 0 && <p className="empty">The list is empty. Add something above.</p>}
        {open.map((item) => (
          <Row key={item.id} item={item} onToggle={toggle} onDelete={() => act(() => api.deleteGrocery(item.id))} />
        ))}

        {done.length > 0 && (
          <>
            <div className="grocery-done-head">
              <span>Got it ({done.length})</span>
              <button onClick={() => act(api.clearCheckedGrocery)}>Clear checked</button>
            </div>
            {done.map((item) => (
              <Row key={item.id} item={item} onToggle={toggle} onDelete={() => act(() => api.deleteGrocery(item.id))} />
            ))}
          </>
        )}
      </div>
    </main>
  )
}

function Row({ item, onToggle, onDelete }) {
  return (
    <div className={`grocery-item ${item.done ? 'done' : ''}`}>
      <button className="check" onClick={() => onToggle(item)} aria-label={item.done ? 'Uncheck' : 'Check off'}>
        <span className="box">{item.done ? '✓' : ''}</span>
        <span className="text">{item.text}</span>
      </button>
      <button className="remove" onClick={onDelete} aria-label={`Remove ${item.text}`}>
        ×
      </button>
    </div>
  )
}
