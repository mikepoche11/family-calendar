/**
 * Whole-app colour themes. Each one overrides the CSS variables set on :root in styles.css, using pastel
 * versions of the holiday's colours. The chosen theme is saved on the server, so the wall screen and every
 * phone change together. `icons` are holiday icons (holidayArt.js) shown in the header and on the theme button.
 */
export const THEMES = [
  {
    id: '',
    name: 'Everyday',
    icons: [],
    vars: {},
    swatch: ['#fdf8ef', '#a78bfa', '#fde68a'],
  },
  {
    id: 'christmas',
    name: 'Christmas',
    icons: ['xmas-santa', 'xmas-tree', 'xmas-snowman'],
    vars: {
      bg: '#e8f5eb', line: '#cfe5d4', accent: '#f87171', 'accent-soft': '#fee2e2', 'accent-ink': '#991b1b',
      primary: '#bbf7d0', 'primary-edge': '#86efac', today: '#fdecec',
    },
  },
  {
    id: 'mardi-gras',
    name: 'Mardi Gras',
    icons: ['mardi-jester', 'mardi-mask', 'mardi-king-cake'],
    vars: {
      bg: '#f0e8fb', line: '#ddd0f0', accent: '#a78bfa', 'accent-soft': '#ede9fe', 'accent-ink': '#5b21b6',
      primary: '#fde68a', 'primary-edge': '#f3c94f', today: '#ecfdf3',
    },
  },
  {
    id: 'valentines',
    name: "Valentine's",
    icons: ['valentine-heart', 'valentine-bear', 'valentine-letter'],
    vars: {
      bg: '#fce7ef', line: '#f3d0dc', accent: '#f472b6', 'accent-soft': '#fce7f3', 'accent-ink': '#9d174d',
      primary: '#fecdd3', 'primary-edge': '#fda4af', today: '#fde4ec',
    },
  },
  {
    id: 'easter',
    name: 'Easter',
    icons: ['easter-bunny', 'easter-chick', 'easter-egg'],
    vars: {
      bg: '#e9f6ee', line: '#d2e9da', accent: '#a5b4fc', 'accent-soft': '#e0e7ff', 'accent-ink': '#3730a3',
      primary: '#fbcfe8', 'primary-edge': '#f9a8d4', today: '#fef9e7',
    },
  },
  {
    id: 'summer',
    name: 'Summer',
    icons: ['summer-sun', 'summer-watermelon', 'summer-popsicle'],
    vars: {
      bg: '#e4f3fc', line: '#cbe3f2', accent: '#fb923c', 'accent-soft': '#ffedd5', 'accent-ink': '#9a3412',
      primary: '#fde68a', 'primary-edge': '#f3c94f', today: '#fff7e0',
    },
  },
  {
    id: 'july-4th',
    name: 'July 4th',
    icons: ['july4-star', 'july4-flag', 'july4-firework'],
    vars: {
      bg: '#e9effb', line: '#d2dcf1', accent: '#60a5fa', 'accent-soft': '#dbeafe', 'accent-ink': '#1e3a8a',
      primary: '#fecaca', 'primary-edge': '#fca5a5', today: '#fdeeee',
    },
  },
  {
    id: 'halloween',
    name: 'Halloween',
    icons: ['halloween-pumpkin', 'halloween-ghost', 'halloween-cat'],
    vars: {
      bg: '#fbe9d9', line: '#efd5bd', accent: '#a78bfa', 'accent-soft': '#ede9fe', 'accent-ink': '#4c1d95',
      primary: '#fed7aa', 'primary-edge': '#fdba74', today: '#f3eefe',
    },
  },
  {
    id: 'back-to-school',
    name: 'Back to school',
    icons: ['school-apple', 'school-bus', 'school-pencil'],
    vars: {
      bg: '#eef3fb', line: '#d6dfef', accent: '#f87171', 'accent-soft': '#fee2e2', 'accent-ink': '#991b1b',
      primary: '#fde68a', 'primary-edge': '#f3c94f', today: '#fff8dc',
    },
  },
  {
    id: 'thanksgiving',
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

/** Set the theme's colours on <html>; the Everyday theme just removes the overrides. */
export function applyTheme(id) {
  const t = themeById(id)
  const root = document.documentElement
  for (const v of VARS) {
    if (t.vars[v]) root.style.setProperty(`--${v}`, t.vars[v])
    else root.style.removeProperty(`--${v}`)
  }
  root.dataset.theme = t.id || 'everyday'
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', t.vars.bg ?? '#fdf8ef')
}
