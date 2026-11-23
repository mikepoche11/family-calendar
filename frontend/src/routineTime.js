/** When the morning and bedtime routines are on, from the times saved in Settings ("06:30" style, local time). */

export const KINDS = ['morning', 'bedtime']
export const ROUTINE = {
  morning: { label: 'Morning routine', short: 'Morning', icon: 'sun' },
  bedtime: { label: 'Bedtime routine', short: 'Bedtime', icon: 'moon' },
}

const hhmm = (d) => `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`

/** The routine that's on right now, or null. */
export function activeKind(settings, now = new Date()) {
  if (!settings) return null
  const t = hhmm(now)
  return KINDS.find((k) => settings[k] && settings[k].start <= t && t < settings[k].end) ?? null
}

/** The routine to show: the one that's on, else the next one today (after bedtime ends: tomorrow's morning). */
export function shownKind(settings, now = new Date()) {
  if (!settings) return 'morning'
  const on = activeKind(settings, now)
  if (on) return on
  const t = hhmm(now)
  const next = KINDS.map((k) => ({ k, start: settings[k].start }))
    .filter((x) => x.start > t)
    .sort((a, b) => a.start.localeCompare(b.start))[0]
  return next?.k ?? 'morning'
}

/** "06:30" -> "6:30 AM" */
export function fmtTime(v) {
  if (!v) return ''
  const [h, m] = v.split(':').map(Number)
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h < 12 ? 'AM' : 'PM'}`
}

export const localDate = (d = new Date()) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
