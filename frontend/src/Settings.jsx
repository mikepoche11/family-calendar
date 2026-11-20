import { useState } from 'react'
import { api } from './api.js'
import Avatar, { AVATARS, AvatarArt } from './avatars.jsx'
import PhotosPanel from './PhotosPanel.jsx'

/** Pastel family colours (coral, peach, butter yellow, lime, mint, aqua, sky, blue, lilac, orchid, pink, grey). */
export const COLORS = [
  '#fca5a5', '#fdba74', '#fde68a', '#d9f99d', '#86efac', '#99f6e4',
  '#7dd3fc', '#93c5fd', '#c4b5fd', '#f0abfc', '#f9a8d4', '#cbd5e1',
]

/** Family settings: pick a person, then change their name, colour and avatar. Saves as you tap. */
export default function Settings({ people, onChanged, onClose, initialTab = 'family', onPreview }) {
  const [tab, setTab] = useState(initialTab)
  const [selectedId, setSelectedId] = useState(people[0]?.id ?? null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [error, setError] = useState(null)
  const person = people.find((p) => p.id === selectedId)

  async function run(fn) {
    setError(null)
    try {
      const result = await fn()
      await onChanged()
      return result
    } catch (err) {
      setError(err.message)
    }
  }

  const patch = (fields) => run(() => api.updatePerson(person.id, fields))

  async function addPerson() {
    const used = new Set(people.map((p) => p.color))
    const color = COLORS.find((c) => !used.has(c)) ?? COLORS[0]
    let n = people.length + 1
    while (people.some((p) => p.name === `Person ${n}`)) n++
    const created = await run(() => api.createPerson({ name: `Person ${n}`, color }))
    if (created) setSelectedId(created.id)
  }

  async function removePerson() {
    await run(() => api.deletePerson(person.id))
    setConfirmDelete(false)
    setSelectedId(people.find((p) => p.id !== person.id)?.id ?? null)
  }

  return (
    <div className="backdrop" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal settings">
        <div className="settings-head">
          <div className="tabs">
            <button className={tab === 'family' ? 'on' : ''} onClick={() => setTab('family')}>Family</button>
            <button className={tab === 'photos' ? 'on' : ''} onClick={() => setTab('photos')}>Photos</button>
          </div>
          <button onClick={onClose} className="primary">Done</button>
        </div>

        {tab === 'photos' && <PhotosPanel onPreview={onPreview} />}

        {tab === 'family' && (
        <div className="person-tabs">
          {people.map((p) => (
            <button
              key={p.id}
              className={`person-tab ${p.id === selectedId ? 'on' : ''}`}
              style={{ '--chip': p.color }}
              onClick={() => {
                setSelectedId(p.id)
                setConfirmDelete(false)
              }}
            >
              <Avatar person={p} size={44} />
              <span>{p.name}</span>
            </button>
          ))}
          <button className="person-tab add" onClick={addPerson}>
            <span className="plus">+</span>
            <span>Add</span>
          </button>
        </div>
        )}

        {tab === 'family' && person && (
          <div className="editor" key={person.id}>
            <label>
              Name
              <input
                defaultValue={person.name}
                maxLength={40}
                onBlur={(e) => {
                  const name = e.target.value.trim()
                  if (name && name !== person.name) patch({ name })
                }}
                onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
              />
            </label>
            <p className="hint">
              Events titled "{person.name}: …" or "[{person.name}] …" show in {person.name}'s colour.
            </p>

            <div className="field-label">Colour</div>
            <div className="swatches">
              {COLORS.map((c) => (
                <button
                  key={c}
                  className={`swatch ${person.color === c ? 'on' : ''}`}
                  style={{ background: c }}
                  aria-label={`Colour ${c}`}
                  onClick={() => patch({ color: c })}
                />
              ))}
            </div>

            <div className="field-label">Avatar</div>
            <div className="avatar-grid">
              <button
                className={`avatar-choice ${!person.avatar ? 'on' : ''}`}
                style={{ '--chip': person.color }}
                onClick={() => patch({ avatar: '' })}
              >
                <Avatar person={{ ...person, avatar: '' }} size={64} />
                <span>Letter</span>
              </button>
              {AVATARS.map((a) => (
                <button
                  key={a.id}
                  className={`avatar-choice ${person.avatar === a.id ? 'on' : ''}`}
                  style={{ '--chip': person.color }}
                  onClick={() => patch({ avatar: a.id })}
                >
                  <AvatarArt id={a.id} size={64} />
                  <span>{a.name}</span>
                </button>
              ))}
            </div>

            <div className="actions">
              {confirmDelete ? (
                <>
                  <span className="confirm-text">Remove {person.name}? Their events stay on the calendar.</span>
                  <button onClick={() => setConfirmDelete(false)}>Keep</button>
                  <button className="danger" onClick={removePerson}>Remove</button>
                </>
              ) : (
                <button className="danger" onClick={() => setConfirmDelete(true)}>
                  Remove {person.name}
                </button>
              )}
            </div>
          </div>
        )}
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  )
}
