/**
 * Whole-app colour themes. Each one overrides the CSS variables set on :root in styles.css, using pastel
 * versions of the holiday's colours. The chosen theme is saved on the server, so the wall screen and every
 * phone change together. `icons` are holiday icons (holidayArt.js) shown in the header and on the theme button.
 */
export const THEMES = [
  {
    id: '',
    deep: '#a07c4f', // darkest background shade offered in the colour picker
    name: 'Everyday',
    icons: [],
    vars: {},
    swatch: ['#fdf8ef', '#a78bfa', '#fde68a'],
  },
  {
    id: 'christmas',
    deep: '#2f6b45', // darkest background shade offered in the colour picker
    name: 'Christmas',
    icons: ['xmas-santa', 'xmas-tree', 'xmas-snowman'],
    vars: {
      bg: '#e8f5eb', line: '#cfe5d4', accent: '#f87171', 'accent-soft': '#fee2e2', 'accent-ink': '#991b1b',
      primary: '#bbf7d0', 'primary-edge': '#86efac', today: '#fdecec',
    },
  },
  {
    id: 'mardi-gras',
    deep: '#6d4aa8', // darkest background shade offered in the colour picker
    name: 'Mardi Gras',
    icons: ['mardi-jester', 'mardi-mask', 'mardi-king-cake'],
    vars: {
      bg: '#f0e8fb', line: '#ddd0f0', accent: '#a78bfa', 'accent-soft': '#ede9fe', 'accent-ink': '#5b21b6',
      primary: '#fde68a', 'primary-edge': '#f3c94f', today: '#ecfdf3',
    },
  },
  {
    id: 'valentines',
    deep: '#b8406f', // darkest background shade offered in the colour picker
    name: "Valentine's",
    icons: ['valentine-heart', 'valentine-bear', 'valentine-letter'],
    vars: {
      bg: '#fce7ef', line: '#f3d0dc', accent: '#f472b6', 'accent-soft': '#fce7f3', 'accent-ink': '#9d174d',
      primary: '#fecdd3', 'primary-edge': '#fda4af', today: '#fde4ec',
    },
  },
  {
    id: 'easter',
    deep: '#5b8f6f', // darkest background shade offered in the colour picker
    name: 'Easter',
    icons: ['easter-bunny', 'easter-chick', 'easter-egg'],
    vars: {
      bg: '#e9f6ee', line: '#d2e9da', accent: '#a5b4fc', 'accent-soft': '#e0e7ff', 'accent-ink': '#3730a3',
      primary: '#fbcfe8', 'primary-edge': '#f9a8d4', today: '#fef9e7',
    },
  },
  {
    id: 'summer',
    deep: '#2b7fb0', // darkest background shade offered in the colour picker
    name: 'Summer',
    icons: ['summer-sun', 'summer-watermelon', 'summer-popsicle'],
    vars: {
      bg: '#e4f3fc', line: '#cbe3f2', accent: '#fb923c', 'accent-soft': '#ffedd5', 'accent-ink': '#9a3412',
      primary: '#fde68a', 'primary-edge': '#f3c94f', today: '#fff7e0',
    },
  },
  {
    id: 'july-4th',
    deep: '#2d4f8f', // darkest background shade offered in the colour picker
    name: 'July 4th',
    icons: ['july4-star', 'july4-flag', 'july4-firework'],
    vars: {
      bg: '#e9effb', line: '#d2dcf1', accent: '#60a5fa', 'accent-soft': '#dbeafe', 'accent-ink': '#1e3a8a',
      primary: '#fecaca', 'primary-edge': '#fca5a5', today: '#fdeeee',
    },
  },
  {
    id: 'halloween',
    deep: '#c2611f', // darkest background shade offered in the colour picker
    name: 'Halloween',
    icons: ['halloween-pumpkin', 'halloween-ghost', 'halloween-cat'],
    vars: {
      bg: '#fbe9d9', line: '#efd5bd', accent: '#a78bfa', 'accent-soft': '#ede9fe', 'accent-ink': '#4c1d95',
      primary: '#fed7aa', 'primary-edge': '#fdba74', today: '#f3eefe',
    },
  },
  {
    id: 'back-to-school',
    deep: '#3f5f9a', // darkest background shade offered in the colour picker
    name: 'Back to school',
    icons: ['school-apple', 'school-bus', 'school-pencil'],
    vars: {
      bg: '#eef3fb', line: '#d6dfef', accent: '#f87171', 'accent-soft': '#fee2e2', 'accent-ink': '#991b1b',
      primary: '#fde68a', 'primary-edge': '#f3c94f', today: '#fff8dc',
    },
  },
  {
    id: 'thanksgiving',
    deep: '#8a5a2b', // darkest background shade offered in the colour picker
    name: 'Thanksgiving',
    icons: ['thanks-turkey', 'thanks-pie', 'thanks-leaf'],
    vars: {
      bg: '#f7ead9', line: '#ead6bf', accent: '#d9a066', 'accent-soft': '#f6e7d4', 'accent-ink': '#7c4a2d',
      primary: '#fdba74', 'primary-edge': '#f59e0b', today: '#fdf0de',
    },
  },
]

THEMES.forEach((t) => {
  if (!t.swatch) t.swatch = [t.vars.bg, t.vars.accent, t.vars.primary]
})

export const themeById = (id) => THEMES.find((t) => t.id === id) ?? THEMES[0]

const VARS = ['bg', 'line', 'accent', 'accent-soft', 'accent-ink', 'primary', 'primary-edge', 'today']
const EVERYDAY_BG = '#fdf8ef'

export const defaultBackground = (t) => t.vars.bg ?? EVERYDAY_BG

const hex = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16))
const toHex = (rgb) => '#' + rgb.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')
const mix = (a, b, t) => toHex(hex(a).map((v, i) => v + (hex(b)[i] - v) * t))

/** Relative brightness 0 (black) .. 1 (white). */
export function lightness(c) {
  const [r, g, b] = hex(c).map((v) => {
    v /= 255
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

/** Background swatches for a theme: its own background, then lighter to darker shades of its main colour. */
export function backgroundShades(t) {
  return [defaultBackground(t), ...[0.88, 0.75, 0.6, 0.4, 0.2, 0].map((k) => mix(t.deep, '#ffffff', k))]
}

/**
 * Set the theme's colours on <html>; the Everyday theme just removes the overrides. `background` is the
 * family's own background colour for this theme, if they picked one. On a dark background, text that sits
 * straight on the page (clock, headings) turns light so it stays readable.
 */
export function applyTheme(id, background = '') {
  const t = themeById(id)
  const root = document.documentElement
  for (const v of VARS) {
    if (t.vars[v]) root.style.setProperty(`--${v}`, t.vars[v])
    else root.style.removeProperty(`--${v}`)
  }
  const bg = /^#[0-9a-f]{6}$/i.test(background) ? background : defaultBackground(t)
  if (bg !== defaultBackground(t)) {
    root.style.setProperty('--bg', bg)
    root.style.setProperty('--line', lightness(bg) < 0.3 ? mix(bg, '#ffffff', 0.78) : mix(bg, '#475569', 0.12))
  }
  root.classList.toggle('bg-dark', lightness(bg) < 0.3)
  root.dataset.theme = t.id || 'everyday'
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', bg)
}
