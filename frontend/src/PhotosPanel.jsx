import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { api } from './api.js'

/** Settings tab for the photo screensaver: connect Google Photos, pick photos, manage them. */
export default function PhotosPanel({ onPreview }) {
  const [status, setStatus] = useState(null)
  const [photos, setPhotos] = useState([])
  const [qr, setQr] = useState(null)
  const [error, setError] = useState(null)
  const [confirmClear, setConfirmClear] = useState(false)

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
        After {status.count ? 'a few minutes' : 'a while'} with nobody touching the screen, it shows a slideshow of these
        photos. Tap anywhere to get back to the calendar.
      </p>

      {!status.configured && (
        <p className="notice">
          To pick photos from Google Photos, add your Google sign-in keys to the backend first (see
          docs/photos-setup.md). Photos copied into the <code>data/photos</code> folder work without it.
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

      <div className="field-label">
        {photos.length} photo{photos.length === 1 ? '' : 's'}
      </div>
      {photos.length > 0 && (
        <>
          <div className="thumbs">
            {photos.map((name) => (
              <div className="thumb" key={name}>
                <img src={`/api/photos/file/${encodeURIComponent(name)}`} alt="" loading="lazy" />
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
