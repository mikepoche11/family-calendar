import { useEffect, useRef, useState } from 'react'
import QRCode from 'qrcode'
import { api } from './api.js'
import { isVideo } from './Screensaver.jsx'

/** Settings tab for the photo screensaver: connect Google Photos, pick photos, manage them. */
export default function PhotosPanel({ onPreview }) {
  const [status, setStatus] = useState(null)
  const [photos, setPhotos] = useState([])
  const [qr, setQr] = useState(null)
  const [error, setError] = useState(null)
  const [confirmClear, setConfirmClear] = useState(false)
  const [upload, setUpload] = useState(null) // { done, total, added, failed }
  const [ss, setSs] = useState(null)
  const fileRef = useRef(null)

  useEffect(() => {
    api.config().then((c) => setSs(c.screensaver)).catch(() => {})
  }, [])

  async function saveSs(change) {
    const next = { ...ss, ...change }
    setSs(next)
    try {
      setSs(await api.setScreensaver(next))
    } catch (err) {
      setError(err.message)
    }
  }

  // One photo at a time, so a big batch from a phone shows progress and one bad file doesn't stop the rest
  async function uploadFiles(files) {
    const list = [...files]
    if (!list.length) return
    setError(null)
    const state = { done: 0, total: list.length, added: 0, failed: [] }
    setUpload({ ...state })
    for (const f of list) {
      try {
        const r = await api.uploadPhoto(f)
        if (r.added) state.added++
      } catch (err) {
        state.failed.push(`${f.name}: ${err.message}`)
      }
      state.done++
      setUpload({ ...state })
    }
    await load()
  }

  const load = async () => {
    try {
      const [s, list] = await Promise.all([api.photoStatus(), api.photos()])
      setStatus(s)
      setPhotos(list)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  // While a pick is in progress, poll for progress
  const picking = status?.pick?.state === 'waiting' || status?.pick?.state === 'downloading'
  useEffect(() => {
    if (!picking) return
    const t = setInterval(load, 2000)
    return () => clearInterval(t)
  }, [picking])

  useEffect(() => {
    const uri = status?.pick?.state === 'waiting' ? status.pick.picker_uri : null
    if (!uri) return setQr(null)
    QRCode.toDataURL(uri, { width: 320, margin: 1 }).then(setQr)
  }, [status?.pick?.state, status?.pick?.picker_uri])

  async function act(fn) {
    setError(null)
    try {
      await fn()
    } catch (err) {
      setError(err.message)
    }
    await load()
  }

  if (!status) return <p className="hint">Loading…</p>
  const pick = status.pick ?? {}

  return (
    <div className="editor photos-panel">
      <p className="hint">
        When nobody has touched the wall for a while, it shows a slideshow of these photos. Tap anywhere to get back to
        the calendar.
      </p>

      <div className="row-actions">
        <button className="primary" onClick={() => fileRef.current?.click()} disabled={upload && upload.done < upload.total}>
          Add photos
        </button>
        <span className="hint">Photos and MP4 videos from this phone, tablet or computer. On a phone, your gallery opens.</span>
        <input
          ref={fileRef}
          type="file"
          accept="image/*,video/mp4,video/webm"
          multiple
          hidden
          onChange={(e) => {
            uploadFiles(e.target.files)
            e.target.value = ''
          }}
        />
      </div>
      {upload && upload.done < upload.total && (
        <p className="big">
          Adding… {upload.done} of {upload.total}{upload.total - upload.done > 0 && ' (videos take a moment)'}
        </p>
      )}
      {upload && upload.done === upload.total && (
        <p className="big">
          Added {upload.added} item{upload.added === 1 ? '' : 's'}
          {upload.total - upload.added - upload.failed.length > 0 && ` (${upload.total - upload.added - upload.failed.length} already here)`}.
        </p>
      )}
      {upload?.failed.length > 0 && <p className="error">Couldn't add {upload.failed.join('; ')}</p>}

      {!status.configured && (
        <p className="hint">
          Want to pick from Google Photos too? Add your Google sign-in keys first (see docs/photos-setup.md).
        </p>
      )}

      {status.configured && !status.connected && (
        <div className="row-actions">
          <a className="button primary" href="/api/photos/auth/start">
            Connect Google Photos
          </a>
          <span className="hint">One-time sign-in with the Google account that has your photos.</span>
        </div>
      )}

      {status.connected && (
        <div className="row-actions">
          {!picking && (
            <button className="primary" onClick={() => act(api.startPick)}>
              Choose photos
            </button>
          )}
          {picking && (
            <button onClick={() => act(api.cancelPick)}>Cancel</button>
          )}
          <button onClick={() => act(api.disconnectPhotos)}>Disconnect</button>
        </div>
      )}

      {pick.state === 'waiting' && (
        <div className="picker-box">
          {qr && <img src={qr} alt="QR code to open Google Photos" width="220" height="220" />}
          <div>
            <p className="big">Scan with your phone to choose photos</p>
            <p className="hint">
              Your phone opens Google Photos. Pick photos (you can browse your albums), tap Done, and they appear here.
            </p>
            <button onClick={() => window.open(pick.picker_uri + '/autoclose', '_blank')}>Or choose on this screen</button>
          </div>
        </div>
      )}
      {pick.state === 'downloading' && <p className="big">Copying photos… {pick.added} so far</p>}
      {pick.state === 'done' && <p className="big">Added {pick.added} photo{pick.added === 1 ? '' : 's'}.</p>}
      {pick.state === 'error' && <p className="error">{pick.error}</p>}
      {error && <p className="error">{error}</p>}

      {ss && (
        <div className="ss-settings">
          <label>
            Start after
            <select value={ss.minutes} onChange={(e) => saveSs({ minutes: Number(e.target.value) })}>
              {[...new Set([1, 2, 5, 10, 15, 20, 30, 60, ss.minutes])].sort((a, b) => a - b).map((m) => (
                <option key={m} value={m}>
                  {m} min untouched
                </option>
              ))}
            </select>
          </label>
          <label>
            Each photo
            <select value={ss.slide_seconds} onChange={(e) => saveSs({ slide_seconds: Number(e.target.value) })}>
              {[...new Set([5, 10, 15, 20, 30, 60, ss.slide_seconds])].sort((a, b) => a - b).map((n) => (
                <option key={n} value={n}>
                  {n} seconds
                </option>
              ))}
            </select>
          </label>
          <label className="check">
            <input type="checkbox" checked={ss.card} onChange={(e) => saveSs({ card: e.target.checked })} />
            Show time, weather and what's next
          </label>
          <label className="check">
            <input type="checkbox" checked={ss.night} onChange={(e) => saveSs({ night: e.target.checked })} />
            Dim clock instead of photos at night
          </label>
          {ss.night && (
            <label>
              Night
              <input type="time" value={ss.night_start} onChange={(e) => e.target.value && saveSs({ night_start: e.target.value })} />
              to
              <input type="time" value={ss.night_end} onChange={(e) => e.target.value && saveSs({ night_end: e.target.value })} />
            </label>
          )}
        </div>
      )}

      <div className="field-label">
        {photos.length} photo{photos.length === 1 ? '' : 's'}
      </div>
      {photos.length > 0 && (
        <>
          <div className="thumbs">
            {photos.map((name) => (
              <div className="thumb" key={name}>
                {isVideo(name) ? (
                  <>
                    <video src={`/api/photos/file/${encodeURIComponent(name)}#t=0.5`} muted playsInline preload="metadata" />
                    <span className="thumb-play" aria-label="Video">▶</span>
                  </>
                ) : (
                  <img src={`/api/photos/file/${encodeURIComponent(name)}`} alt="" loading="lazy" />
                )}
                <button aria-label="Remove photo" onClick={() => act(() => api.deletePhoto(name))}>
                  ×
                </button>
              </div>
            ))}
          </div>
          <div className="actions">
            <button onClick={onPreview}>Preview slideshow</button>
            <span className="spacer" />
            {confirmClear ? (
              <>
                <span className="confirm-text">Remove all {photos.length} photos from the screen?</span>
                <button onClick={() => setConfirmClear(false)}>Keep</button>
                <button className="danger" onClick={() => act(api.deleteAllPhotos).then(() => setConfirmClear(false))}>
                  Remove all
                </button>
              </>
            ) : (
              <button className="danger" onClick={() => setConfirmClear(true)}>
                Remove all
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}
