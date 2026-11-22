/**
 * Google Calendar's 11 event colours, keyed by the event's colorId.
 * Hex values match what Google Calendar shows on the web and phone today, so an event looks the
 * same on the wall as it does in the Google app. Events with no colour picked (colorId "") fall
 * back to the family member's colour, or the neutral grey.
 */
export const GOOGLE_COLORS = {
  1: { name: 'Lavender', bg: '#7986cb' },
  2: { name: 'Sage', bg: '#33b679' },
  3: { name: 'Grape', bg: '#8e24aa' },
  4: { name: 'Flamingo', bg: '#e67c73' },
  5: { name: 'Banana', bg: '#f6bf26' },
  6: { name: 'Tangerine', bg: '#f4511e' },
  7: { name: 'Peacock', bg: '#039be5' },
  8: { name: 'Graphite', bg: '#616161' },
  9: { name: 'Blueberry', bg: '#3f51b5' },
  10: { name: 'Basil', bg: '#0b8043' },
  11: { name: 'Tomato', bg: '#d50000' },
}

/** Order Google's own colour picker uses. */
export const GOOGLE_COLOR_ORDER = ['11', '4', '6', '5', '2', '10', '7', '9', '1', '3', '8']

/** Dark text on light colours (Banana), white text on the rest. */
export function textOn(hex) {
  const n = parseInt(hex.slice(1), 16)
  const [r, g, b] = [n >> 16, (n >> 8) & 255, n & 255].map((v) => {
    const c = v / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return lum > 0.4 ? '#1e293b' : '#ffffff'
}
