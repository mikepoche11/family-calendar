/**
 * Pastel icon set drawn for this project (original art, no licence needed), in the same soft style as the
 * animal avatars and the marble jars. Every icon is drawn in a 48x48 box with a soft dark outline.
 *
 * Chores, rewards and meals still store an emoji in the database (so old data keeps working). EMOJI maps
 * those emoji to a drawn icon; an emoji with no drawing is shown as plain text.
 */

const INK = '#475569'
const C = {
  pink: '#fbcfe8', rose: '#fecdd3', coral: '#fca5a5', peach: '#fed7aa', orange: '#fdba74', butter: '#fde68a',
  cream: '#fef3c7', mint: '#bbf7d0', green: '#86efac', sage: '#d9f99d', sky: '#bae6fd', ice: '#e0f2fe',
  blue: '#93c5fd', lilac: '#ddd6fe', lav: '#e9d5ff', tan: '#f3d9b1', brown: '#d6b38a', grey: '#e2e8f0',
  steel: '#cbd5e1', white: '#ffffff',
}

const pt = (cx, cy, r, a) => `${(cx + r * Math.cos(a)).toFixed(2)} ${(cy + r * Math.sin(a)).toFixed(2)}`

function starPath(cx, cy, ro, ri, n = 5) {
  const p = []
  for (let i = 0; i < n * 2; i++) p.push(pt(cx, cy, i % 2 ? ri : ro, -Math.PI / 2 + (i * Math.PI) / n))
  return `M${p.join(' L')} Z`
}

function gearPath(cx, cy, ro, ri, n) {
  const w = (2 * Math.PI) / n
  const p = []
  for (let i = 0; i < n; i++) {
    const a = i * w
    p.push(pt(cx, cy, ri, a - 0.32 * w), pt(cx, cy, ro, a - 0.18 * w), pt(cx, cy, ro, a + 0.18 * w), pt(cx, cy, ri, a + 0.32 * w))
  }
  return `M${p.join(' L')} Z`
}

const heart = (cx, cy, s) =>
  `M${cx} ${cy + s * 0.85} C${cx - s * 1.5} ${cy - s * 0.1} ${cx - s * 0.8} ${cy - s * 1.25} ${cx} ${cy - s * 0.45} ` +
  `C${cx + s * 0.8} ${cy - s * 1.25} ${cx + s * 1.5} ${cy - s * 0.1} ${cx} ${cy + s * 0.85} Z`

const drop = (x, y, s = 1) =>
  `M${x} ${y} c0 0 ${-3.2 * s} ${4.2 * s} ${-3.2 * s} ${6.6 * s} a${3.2 * s} ${3.2 * s} 0 0 0 ${6.4 * s} 0 c0 ${-2.4 * s} ${-3.2 * s} ${-6.6 * s} ${-3.2 * s} ${-6.6 * s} Z`

/** Cloud whose flat bottom runs from (x, y) to (x + 28 * s, y). */
const cloudPath = (x, y, s = 1) =>
  `M${x + 5 * s} ${y} a${6 * s} ${6 * s} 0 0 1 ${-0.6 * s} ${-11.9 * s} ` +
  `a${8.5 * s} ${8.5 * s} 0 0 1 ${16.4 * s} ${-3.2 * s} a${6.6 * s} ${6.6 * s} 0 0 1 ${2.2 * s} ${15.1 * s} Z`

const Cloud = ({ x = 8, y = 36, s = 1.15, fill = C.white }) => <path d={cloudPath(x, y, s)} fill={fill} />

const Sun = ({ cx = 24, cy = 24, r = 8, rays = true }) => (
  <g>
    {rays &&
      Array.from({ length: 8 }, (_, i) => {
        const a = (i * Math.PI) / 4
        return <path key={i} d={`M${pt(cx, cy, r + 4, a)} L${pt(cx, cy, r + 7.5, a)}`} />
      })}
    <circle cx={cx} cy={cy} r={r} fill={C.butter} />
  </g>
)

const thin = { strokeWidth: 1.6 }

export const ICONS = {
  /* ---------- app ---------- */
  calendar: () => (
    <>
      <rect x="7" y="10" width="34" height="31" rx="6" fill={C.pink} />
      <path d="M7 19 H41 V35 a6 6 0 0 1 -6 6 H13 a6 6 0 0 1 -6 -6 Z" fill={C.white} />
      <path d="M16 6 v7 M32 6 v7" />
      <g stroke="none">
        <circle cx="16" cy="26.5" r="2.3" fill={C.blue} />
        <circle cx="24" cy="26.5" r="2.3" fill={C.blue} />
        <circle cx="32" cy="26.5" r="2.3" fill={C.blue} />
        <circle cx="16" cy="34" r="2.3" fill={C.blue} />
        <path d={heart(24.5, 34, 3.4)} fill="#f9a8d4" />
      </g>
    </>
  ),
  cart: () => (
    <>
      <path d="M11.5 15 H41 l-4 14 H14.5 Z" fill={C.sky} />
      <path d="M21 15.5 v13 M29 15.5 v13" {...thin} />
      <path d="M4 9 h5.5 l5 24 h22" fill="none" />
      <circle cx="17" cy="38" r="3.2" fill={C.white} />
      <circle cx="33" cy="38" r="3.2" fill={C.white} />
    </>
  ),
  plate: () => (
    <>
      <circle cx="24" cy="24" r="13" fill={C.white} />
      <circle cx="24" cy="24" r="8" fill={C.cream} />
      <path d="M4.5 10 v6 a2.5 2.5 0 0 0 5 0 v-6 M7 10 v28" fill="none" />
      <path d="M43 10 c-3.5 3 -3.5 11 0 13.5 V38" fill="none" />
    </>
  ),
  chores: () => (
    <>
      <rect x="8" y="8" width="32" height="32" rx="9" fill={C.mint} />
      <path d="M16 24.5 l5.5 5.5 L33 18" fill="none" strokeWidth="3.6" />
    </>
  ),
  jar: () => (
    <>
      <path d="M15 13 h18 v3 c5 2 7 6 7 11 v8 a6 6 0 0 1 -6 6 H14 a6 6 0 0 1 -6 -6 v-8 c0 -5 2 -9 7 -11 Z" fill={C.ice} />
      <g {...thin}>
        <circle cx="16" cy="35" r="4" fill={C.blue} />
        <circle cx="24.5" cy="35" r="4" fill={C.white} />
        <circle cx="32.5" cy="35" r="4" fill={C.blue} />
        <circle cx="20.5" cy="27.5" r="4" fill={C.blue} />
        <circle cx="29" cy="28" r="4" fill={C.blue} />
      </g>
      <path d="M12.5 22 c-1.2 3 -1.2 6 -0.6 9" stroke={C.white} strokeWidth="2.6" fill="none" />
      <rect x="13" y="6" width="22" height="7.5" rx="3" fill={C.lilac} />
    </>
  ),
  gear: () => (
    <>
      <path d={gearPath(24, 24, 18, 13.5, 8)} fill={C.lilac} />
      <circle cx="24" cy="24" r="5.5" fill={C.white} />
    </>
  ),
  pencil: () => (
    <g transform="rotate(45 24 24)">
      <rect x="19" y="4" width="10" height="10" rx="3" fill={C.pink} />
      <rect x="19" y="12" width="10" height="21" fill={C.butter} />
      <path d="M19 33 L24 43 L29 33 Z" fill={C.cream} />
      <path d="M22.4 39.8 L24 43 L25.6 39.8 Z" fill={INK} />
    </g>
  ),
  anyone: () => (
    <>
      <path d={heart(18, 22, 10)} fill={C.lilac} />
      <path d={heart(30.5, 28, 10)} fill={C.pink} />
    </>
  ),
  party: () => (
    <>
      <path d="M7 41 L15 18 L30 33 Z" fill={C.peach} />
      <path d="M11 30 l7 7 M13 24 l11 11" {...thin} />
      <g stroke="none">
        <circle cx="30" cy="12" r="2.6" fill="#f9a8d4" />
        <circle cx="39" cy="22" r="2.4" fill={C.blue} />
        <circle cx="21" cy="9" r="2.2" fill={C.green} />
        <circle cx="40" cy="34" r="2.2" fill="#fcd34d" />
      </g>
      <path d="M34 6 q3 2.5 0 5 q-3 2.5 0 5" stroke="#c4b5fd" strokeWidth="3" fill="none" />
      <path d="M31 27 q4 -4 9 -2" stroke="#f9a8d4" strokeWidth="3" fill="none" />
    </>
  ),
  star: () => <path d={starPath(24, 25.5, 18, 8.5)} fill={C.butter} />,
  bag: () => (
    <>
      <path d="M10 17 h28 l-1.5 22 a3.5 3.5 0 0 1 -3.5 3.3 H15 a3.5 3.5 0 0 1 -3.5 -3.3 Z" fill={C.pink} />
      <path d="M18 22 v-7 a6 6 0 0 1 12 0 v7" fill="none" />
      <path d={heart(24, 30, 4)} fill={C.white} {...thin} />
    </>
  ),
  scale: () => (
    <>
      <path d="M24 11 V39 M15 41 h18 M9 14 h30" />
      <path d="M9 14 L4.5 27 M9 14 L13.5 27 M39 14 L34.5 27 M39 14 L43.5 27" {...thin} />
      <path d="M3 27 h12 a6 6 0 0 1 -12 0 Z" fill={C.lilac} />
      <path d="M33 27 h12 a6 6 0 0 1 -12 0 Z" fill={C.mint} />
      <circle cx="24" cy="9" r="3" fill={C.butter} />
    </>
  ),
  undo: () => (
    <path d="M17 13 L10 20 L17 27 M10 20 H30 a8.5 8.5 0 0 1 0 17 H21" fill="none" strokeWidth="3.2" />
  ),
  gift: () => (
    <>
      <rect x="9" y="22" width="30" height="19" rx="3" fill={C.pink} />
      <rect x="7" y="15" width="34" height="8" rx="3" fill={C.rose} />
      <rect x="21" y="15" width="6" height="26" fill={C.mint} />
      <path d="M24 15 c-4 -8 -12 -7 -9.5 -1.5 c1 1.8 5 1.5 9.5 1.5 Z" fill={C.mint} />
      <path d="M24 15 c4 -8 12 -7 9.5 -1.5 c-1 1.8 -5 1.5 -9.5 1.5 Z" fill={C.mint} />
    </>
  ),
  dice: () => (
    <>
      <rect x="9" y="9" width="30" height="30" rx="8" fill={C.lilac} />
      <g fill={INK} stroke="none">
        <circle cx="17" cy="17" r="2.6" />
        <circle cx="31" cy="17" r="2.6" />
        <circle cx="24" cy="24" r="2.6" />
        <circle cx="17" cy="31" r="2.6" />
        <circle cx="31" cy="31" r="2.6" />
      </g>
    </>
  ),
  book: () => (
    <>
      <path d="M4 15 V40 c7 -2 14 -1 20 2 c6 -3 13 -4 20 -2 V15" fill={C.sky} />
      <path d="M24 14 C19 10 12 10 6.5 12 V37 c6 -2 12.5 -1.5 17.5 2 Z" fill={C.white} />
      <path d="M24 14 C29 10 36 10 41.5 12 V37 c-6 -2 -12.5 -1.5 -17.5 2 Z" fill={C.white} />
      <path d="M11 18 c3 -1 6 -1 9 0.5 M11 24 c3 -1 6 -1 9 0.5 M28 18.5 c3 -1.5 6 -1.5 9 -0.5" {...thin} />
    </>
  ),
  bulb: () => (
    <>
      <path d="M24 5 a12.5 12.5 0 0 0 -7.4 22.6 c1.5 1.2 2.4 2.7 2.4 4.4 h10 c0 -1.7 .9 -3.2 2.4 -4.4 A12.5 12.5 0 0 0 24 5 Z" fill={C.butter} />
      <rect x="19" y="32" width="10" height="6" rx="2" fill={C.grey} />
      <path d="M21 42 h6" />
      <path d="M17.5 15 a7.5 7.5 0 0 1 4.5 -4.5" stroke={C.white} strokeWidth="2.6" fill="none" />
    </>
  ),

  /* ---------- weather ---------- */
  sun: () => <Sun r={9} />,
  'cloud-sun': () => (
    <>
      <Sun cx={30} cy={17} r={7} />
      <Cloud x={5} y={40} s={1.05} />
    </>
  ),
  cloud: () => <Cloud x={8} y={36} s={1.15} fill={C.ice} />,
  fog: () => (
    <>
      <Cloud x={9} y={29} s={1.05} fill={C.ice} />
      <path d="M8 35 h24 M14 41 h26" strokeWidth="2.8" />
    </>
  ),
  drizzle: () => (
    <>
      <Sun cx={32} cy={14} r={6} />
      <Cloud x={5} y={32} s={1.05} fill={C.ice} />
      <path d={drop(15, 35, 0.8)} fill={C.blue} />
      <path d={drop(26, 37, 0.8)} fill={C.blue} />
    </>
  ),
  rain: () => (
    <>
      <Cloud x={8} y={29} s={1.15} fill={C.ice} />
      <path d={drop(15, 33)} fill={C.blue} />
      <path d={drop(24, 35)} fill={C.blue} />
      <path d={drop(33, 33)} fill={C.blue} />
    </>
  ),
  snow: () => (
    <>
      <Cloud x={8} y={29} s={1.15} fill={C.white} />
      {[[15, 37], [24, 40], [33, 37]].map(([x, y]) => (
        <path key={x} d={`M${x - 3} ${y} h6 M${x} ${y - 3} v6 M${x - 2.2} ${y - 2.2} l4.4 4.4 M${x + 2.2} ${y - 2.2} l-4.4 4.4`} stroke="#7dd3fc" strokeWidth="1.8" />
      ))}
    </>
  ),
  storm: () => (
    <>
      <Cloud x={8} y={29} s={1.15} fill={C.steel} />
      <path d="M25 27 L18 37 h6 l-3 8 L31 33 h-6 l3 -6 Z" fill={C.butter} />
    </>
  ),

  /* ---------- chores ---------- */
  bed: () => (
    <>
      <rect x="5" y="13" width="7" height="27" rx="2.5" fill={C.tan} />
      <path d="M17 21 h22 a4 4 0 0 1 4 4 v6 H17 Z" fill={C.sky} />
      <rect x="12" y="19.5" width="10" height="7" rx="3.5" fill={C.white} />
      <rect x="5" y="30" width="38" height="6.5" rx="2.5" fill={C.tan} />
      <path d="M40 37 v4" />
    </>
  ),
  basket: () => (
    <>
      <path d="M12 18 q1.5 -8 9 -7 q5 1 4 7 Z" fill={C.pink} />
      <path d="M24 18 q3 -7 10 -5 q4 2 1.5 5 Z" fill={C.sky} />
      <path d="M8 21 h32 l-3 17 a3 3 0 0 1 -3 2.6 H14 a3 3 0 0 1 -3 -2.6 Z" fill={C.tan} />
      <path d="M16 25 l1.5 11 M24 25 v11 M32 25 l-1.5 11 M10 30 h28" {...thin} />
      <rect x="6" y="17" width="36" height="5.5" rx="2.75" fill={C.brown} />
    </>
  ),
  teddy: () => (
    <>
      <ellipse cx="24" cy="39" rx="11" ry="7" fill={C.tan} />
      <circle cx="14" cy="12.5" r="5.5" fill={C.tan} />
      <circle cx="34" cy="12.5" r="5.5" fill={C.tan} />
      <circle cx="14" cy="12.5" r="2.5" fill={C.rose} stroke="none" />
      <circle cx="34" cy="12.5" r="2.5" fill={C.rose} stroke="none" />
      <circle cx="24" cy="22" r="12" fill={C.tan} />
      <ellipse cx="24" cy="26.5" rx="5.5" ry="4.2" fill={C.cream} />
      <g fill={INK} stroke="none">
        <ellipse cx="24" cy="24.8" rx="2" ry="1.4" />
        <circle cx="19.2" cy="19.5" r="1.7" />
        <circle cx="28.8" cy="19.5" r="1.7" />
      </g>
    </>
  ),
  shirt: () => (
    <>
      <path d="M17 7 l-11 6 l4 9.5 l5 -2 V41 h18 V20.5 l5 2 l4 -9.5 l-11 -6 c-1 3 -4 5 -7 5 c-3 0 -6 -2 -7 -5 Z" fill={C.sky} />
      <path d={heart(24, 26, 4)} fill={C.pink} {...thin} />
    </>
  ),
  spoon: () => (
    <g transform="rotate(35 24 24)">
      <rect x="21.5" y="21" width="5" height="23" rx="2.5" fill={C.lilac} />
      <ellipse cx="24" cy="13" rx="7.5" ry="9.5" fill={C.grey} />
      <path d="M20.5 9.5 a4 5 0 0 1 2.5 -3" stroke={C.white} strokeWidth="2.4" fill="none" />
    </g>
  ),
  bubbles: () => (
    <>
      <circle cx="18" cy="28" r="11" fill={C.ice} />
      <circle cx="33" cy="16" r="7.5" fill={C.lav} />
      <circle cx="35" cy="35" r="5" fill={C.pink} />
      <g stroke={C.white} strokeWidth="2.6" fill="none">
        <path d="M11.5 25 a7 7 0 0 1 4.5 -4.5" />
        <path d="M29 14 a4.5 4.5 0 0 1 3 -3" />
      </g>
    </>
  ),
  trash: () => (
    <>
      <path d="M11 16 h26 l-2 23 a3 3 0 0 1 -3 2.7 H16 a3 3 0 0 1 -3 -2.7 Z" fill={C.mint} />
      <path d="M19 22 v14 M24 22 v14 M29 22 v14" {...thin} />
      <path d="M19.5 11 v-3.5 h9 V11" fill="none" />
      <rect x="7" y="11" width="34" height="5.5" rx="2.75" fill={C.sage} />
    </>
  ),

  /* ---------- treats ---------- */
  sundae: () => (
    <>
      <circle cx="24" cy="7" r="3" fill={C.coral} />
      <circle cx="24" cy="15.5" r="7" fill={C.cream} />
      <circle cx="16.5" cy="21" r="7" fill={C.pink} />
      <circle cx="31.5" cy="21" r="7" fill={C.mint} />
      <path d="M7 25 h34 c0 7 -7.5 12 -17 12 c-9.5 0 -17 -5 -17 -12 Z" fill={C.lav} />
      <path d="M21 37 v4 M27 37 v4 M16 42.5 h16" />
    </>
  ),
  cone: () => (
    <>
      <path d="M14.5 23 L24 45 L33.5 23 Z" fill={C.tan} />
      <path d="M18 27 l9 9 M24 24 l6 6 M30 27 l-9 9 M24 24 l-6 6" {...thin} />
      <path d="M18.5 13 c0 -5 5 -7 8 -10 c.5 3.5 3.5 5.5 2.5 10 Z" fill={C.pink} />
      <ellipse cx="24" cy="15.5" rx="8.5" ry="4.2" fill={C.pink} />
      <ellipse cx="24" cy="21.5" rx="11.5" ry="4.5" fill={C.pink} />
    </>
  ),
  soda: () => (
    <>
      <path d="M26 12 L30 3 h5" fill="none" />
      <path d="M13 16 h22 l-3 26 H16 Z" fill={C.pink} />
      <path d="M14.4 27 c3 -2 6 2 9.6 0 c3.6 -2 6.4 2 9.6 0" fill="none" stroke={C.white} strokeWidth="2.6" />
      <rect x="11" y="12" width="26" height="5" rx="2.5" fill={C.white} />
    </>
  ),
  cookie: () => (
    <>
      <circle cx="24" cy="24" r="16.5" fill={C.tan} />
      <g fill="#a47148" stroke="none">
        <ellipse cx="17" cy="18" rx="2.6" ry="2" />
        <ellipse cx="29" cy="15" rx="2.2" ry="1.8" />
        <ellipse cx="31" cy="27" rx="2.6" ry="2" />
        <ellipse cx="19" cy="30" rx="2.2" ry="1.8" />
        <ellipse cx="25" cy="23" rx="1.8" ry="1.5" />
      </g>
    </>
  ),
  donut: () => (
    <>
      <circle cx="24" cy="24" r="17" fill={C.tan} />
      <path d="M24 10 c4 0 6 2 8 2 c3 1 5 4 5.5 6.5 c.5 2 2 4 1 6.5 c-.5 2 -1 4 -3 6 c-2 2 -3 3.5 -6 4 c-2.5 .5 -4 1.5 -6.5 1 c-3 -.5 -5 -1 -7 -3 c-2 -2 -4 -3.5 -4.5 -6.5 c-.5 -2.5 -.5 -4.5 .5 -7 c1 -2.5 2 -4.5 4.5 -6 C17.5 11 20 10 24 10 Z" fill={C.pink} />
      <circle cx="24" cy="24" r="5.5" fill={C.white} />
      <g strokeWidth="2.4">
        <path d="M17 17 l2 1.5" stroke="#7dd3fc" />
        <path d="M30 15 l1.5 2" stroke="#fcd34d" />
        <path d="M32 27 l-2 1.2" stroke="#86efac" />
        <path d="M18 30 l2 -1" stroke="#c4b5fd" />
      </g>
    </>
  ),
  popcorn: () => (
    <>
      <g fill={C.cream}>
        <circle cx="15" cy="18" r="4.5" />
        <circle cx="33" cy="18" r="4.5" />
        <circle cx="20" cy="13" r="4.5" />
        <circle cx="28" cy="13" r="4.5" />
        <circle cx="24" cy="18" r="4.5" />
      </g>
      <path d="M11 20 h26 l-3 22 H14 Z" fill={C.white} />
      <path d="M17.5 20 L19 42 H23 L22 20 Z M26 20 L25 42 H29 L30.5 20 Z" fill={C.coral} {...thin} />
    </>
  ),
  movie: () => (
    <>
      <rect x="7" y="18" width="34" height="22" rx="3" fill={C.lilac} />
      <rect x="7" y="10" width="34" height="8" rx="2" fill={C.white} />
      <path d="M15 10 l-3 8 M23 10 l-3 8 M31 10 l-3 8 M39 10 l-3 8" />
      <path d="M21 24.5 v10 l8.5 -5 Z" fill={C.white} {...thin} />
    </>
  ),
  game: () => (
    <>
      <path d="M14 15 h20 a9 9 0 0 1 8.7 11.3 l-2 7.5 a4.5 4.5 0 0 1 -8 1.5 l-3 -4.3 h-11.4 l-3 4.3 a4.5 4.5 0 0 1 -8 -1.5 l-2 -7.5 A9 9 0 0 1 14 15 Z" fill={C.lilac} />
      <path d="M14 20.5 v7 M10.5 24 h7" />
      <circle cx="32" cy="21.5" r="2.1" fill="#f9a8d4" {...thin} />
      <circle cx="36" cy="25.5" r="2.1" fill={C.green} {...thin} />
    </>
  ),

  /* ---------- meals ---------- */
  taco: () => (
    <>
      <path d="M8 36 a18 18 0 0 1 36 0 Z" fill={C.green} />
      <circle cx="31" cy="20.5" r="2.6" fill={C.coral} {...thin} />
      <circle cx="38" cy="26.5" r="2.6" fill={C.coral} {...thin} />
      <path d="M4 39 a18 18 0 0 1 36 0 Z" fill={C.butter} />
      <path d="M10 39 a12 12 0 0 1 24 0" fill="none" {...thin} />
    </>
  ),
  spaghetti: () => (
    <>
      <path d="M10 24 c1 -8 7 -12 14 -12 c7 0 13 4 14 12 Z" fill={C.butter} />
      <path d="M14 21 c3 -3 6 3 9 0 c3 -3 6 3 9 0 M17 16.5 c2 -2 4 2 6 0" fill="none" {...thin} />
      <circle cx="19" cy="17" r="3.6" fill={C.brown} />
      <circle cx="29" cy="19" r="3.6" fill={C.brown} />
      <path d="M6 24 h36 c0 9 -8 15 -18 15 c-10 0 -18 -6 -18 -15 Z" fill={C.sky} />
    </>
  ),
  beans: () => (
    <>
      {[[17, 18, -25], [31, 20, 20], [23, 32, -5]].map(([x, y, r]) => (
        <g key={x} transform={`rotate(${r} ${x} ${y})`}>
          <path d={`M${x - 8} ${y} c0 -5 4 -6 8 -4.5 c4 -1.5 8 -.5 8 4.5 c0 5 -4 6 -8 6 c-4 0 -8 -1 -8 -6 Z`} fill={C.coral} />
          <path d={`M${x - 4.5} ${y - 1.5} c1 -1.5 2.5 -2 4 -1.5`} stroke={C.white} strokeWidth="2.2" fill="none" />
        </g>
      ))}
    </>
  ),
  paella: () => (
    <>
      <path d="M6 24 v4 c0 6 8 10 18 10 c10 0 18 -4 18 -10 v-4" fill={C.peach} />
      <path d="M6 26 h-3 M42 26 h3" strokeWidth="3.2" />
      <ellipse cx="24" cy="24" rx="18" ry="6.5" fill={C.butter} />
      <g {...thin}>
        <circle cx="16" cy="23" r="2.3" fill={C.coral} />
        <circle cx="31" cy="22" r="2.3" fill={C.coral} />
        <circle cx="24" cy="26.5" r="2.3" fill={C.green} />
        <circle cx="22" cy="20.5" r="1.8" fill={C.green} />
      </g>
    </>
  ),
  pot: () => (
    <>
      <path d="M18 13 q-2.5 -3 0 -5.5 q2.5 -2.5 0 -5 M24 13 q-2.5 -3 0 -5.5 q2.5 -2.5 0 -5 M30 13 q-2.5 -3 0 -5.5 q2.5 -2.5 0 -5" fill="none" strokeWidth="2" opacity="0.6" />
      <path d="M9 20 h30 v14 a6 6 0 0 1 -6 6 H15 a6 6 0 0 1 -6 -6 Z" fill={C.rose} />
      <path d="M9 25 h-4 M39 25 h4" strokeWidth="3.2" />
      <rect x="6" y="16.5" width="36" height="5.5" rx="2.75" fill={C.pink} />
    </>
  ),
  pancakes: () => (
    <>
      <ellipse cx="24" cy="38" rx="20" ry="5.5" fill={C.white} />
      <rect x="9" y="29.5" width="30" height="7" rx="3.5" fill={C.tan} />
      <rect x="10" y="23" width="28" height="7" rx="3.5" fill={C.tan} />
      <rect x="9" y="16.5" width="30" height="7" rx="3.5" fill={C.tan} />
      <path d="M12 17 h24 v2.5 c0 2 -2.5 2 -2.5 0 c0 3 -3 3 -3 0 c0 2 -2.5 2 -2.5 0 H17 c0 3.5 -3 3.5 -3 0 c0 1.5 -2 1.5 -2 0 Z" fill={C.orange} {...thin} />
      <rect x="20" y="12" width="8" height="5" rx="1.5" fill={C.butter} />
    </>
  ),
  sandwich: () => (
    <>
      <path d="M8 36 q3 4 6 0 q3 4 6 0 q3 4 6 0 q3 4 6 0 q3 4 6 0 Z" fill={C.green} />
      <path d="M8 36 L24 9 L40 36 Z" fill={C.tan} />
      <path d="M14 32.5 L24 15.5 L34 32.5 Z" fill={C.cream} {...thin} />
    </>
  ),
  pizza: () => (
    <>
      <path d="M24 43 L8 13 c10 -5 22 -5 32 0 Z" fill={C.butter} />
      <path d="M8 13 c10 -5 22 -5 32 0 l-2.2 4.2 c-9 -4.2 -18.6 -4.2 -27.6 0 Z" fill={C.tan} />
      <g {...thin}>
        <circle cx="19.5" cy="22" r="3.2" fill={C.coral} />
        <circle cx="28.5" cy="23" r="3.2" fill={C.coral} />
        <circle cx="24" cy="32" r="2.8" fill={C.coral} />
      </g>
    </>
  ),
  drumstick: () => (
    <>
      <path d="M22 26 L12 36" strokeWidth="7.5" />
      <path d="M22 26 L12 36" stroke={C.white} strokeWidth="3.4" />
      <circle cx="9.5" cy="34.5" r="3.2" fill={C.white} />
      <circle cx="13.5" cy="38.5" r="3.2" fill={C.white} />
      <ellipse cx="29" cy="19" rx="12.5" ry="10" transform="rotate(-40 29 19)" fill={C.orange} />
      <path d="M25 13 a6 5 0 0 1 5 -2" stroke={C.cream} strokeWidth="2.6" fill="none" />
    </>
  ),
  takeout: () => (
    <>
      <path d="M16 11 c0 -6.5 16 -6.5 16 0" fill="none" />
      <path d="M10 18 l4 -8 h20 l4 8 Z" fill={C.rose} />
      <path d="M10 18 h28 l-4 24 H14 Z" fill={C.white} />
      <circle cx="24" cy="29" r="4.5" fill={C.coral} {...thin} />
    </>
  ),
  burger: () => (
    <>
      <path d="M8 22 c0 -8 7 -12.5 16 -12.5 c9 0 16 4.5 16 12.5 Z" fill={C.peach} />
      <g fill={C.cream} stroke="none">
        <ellipse cx="18" cy="15" rx="1.5" ry="1" />
        <ellipse cx="25" cy="13" rx="1.5" ry="1" />
        <ellipse cx="31" cy="16.5" rx="1.5" ry="1" />
      </g>
      <path d="M7 23 q3 4 6 0 q3 4 6 0 q3 4 6 0 q3 4 6 0 q3 4 6 0 q2 3 4 0 Z" fill={C.green} />
      <rect x="8" y="26.5" width="32" height="6.5" rx="3.2" fill={C.brown} />
      <rect x="8" y="33" width="32" height="7" rx="3.5" fill={C.peach} />
    </>
  ),
  salad: () => (
    <>
      <circle cx="16" cy="20" r="6" fill={C.green} />
      <circle cx="25" cy="16" r="7" fill={C.sage} />
      <circle cx="33" cy="21" r="5.5" fill={C.green} />
      <circle cx="22" cy="22" r="3" fill={C.coral} {...thin} />
      <path d="M6 24 h36 c0 9 -8 15 -18 15 c-10 0 -18 -6 -18 -15 Z" fill={C.white} />
      <path d="M12 30 c4 2 8 2 12 0 c4 -2 8 -2 12 0" stroke={C.mint} strokeWidth="2.6" fill="none" />
    </>
  ),

  /* ---------- other jobs ---------- */
  toothbrush: () => (
    <g transform="rotate(35 24 24)">
      <rect x="21.5" y="17" width="5" height="28" rx="2.5" fill={C.sky} />
      <rect x="20.5" y="4" width="7" height="14" rx="3" fill={C.white} />
      <path d="M27.5 6 h4 M27.5 10 h4 M27.5 14 h4" stroke={C.green} strokeWidth="2.8" />
    </g>
  ),
  paw: () => (
    <>
      <path d="M24 24 c6 0 11 5 11 10 c0 4 -3 6 -6 6 c-2 0 -3 -1 -5 -1 c-2 0 -3 1 -5 1 c-3 0 -6 -2 -6 -6 c0 -5 5 -10 11 -10 Z" fill={C.pink} />
      <ellipse cx="11.5" cy="22" rx="4" ry="4.8" fill={C.pink} />
      <ellipse cx="19" cy="13.5" rx="4" ry="4.8" fill={C.pink} />
      <ellipse cx="29" cy="13.5" rx="4" ry="4.8" fill={C.pink} />
      <ellipse cx="36.5" cy="22" rx="4" ry="4.8" fill={C.pink} />
    </>
  ),
  broom: () => (
    <g transform="rotate(25 24 24)">
      <rect x="22" y="1" width="4" height="25" rx="2" fill={C.tan} />
      <path d="M16 29 h16 l5 15 H11 Z" fill={C.butter} />
      <path d="M19 31 l-2 12 M24 31 v12 M29 31 l2 12" {...thin} />
      <rect x="16" y="24.5" width="16" height="5.5" rx="2.2" fill={C.pink} />
    </g>
  ),
  plant: () => (
    <>
      <path d="M24 28 c-10 -2 -12.5 -10 -10.5 -16.5 c6.5 2 10.5 8 10.5 16.5 Z" fill={C.green} />
      <path d="M24 28 c10 -2 12.5 -10 10.5 -16.5 c-6.5 2 -10.5 8 -10.5 16.5 Z" fill={C.green} />
      <path d="M24 28 c-4 -6 -3.5 -15 0 -21 c3.5 6 4 15 0 21 Z" fill={C.sage} />
      <path d="M14 30 h20 l-2 12 H16 Z" fill={C.peach} />
      <rect x="12" y="27" width="24" height="5" rx="2.2" fill={C.orange} />
    </>
  ),
}

/** Emoji (as stored for chores, rewards, meals) -> drawn icon. Variation selectors are ignored. */
export const EMOJI = {
  '📅': 'calendar', '🗓': 'calendar', '🛒': 'cart', '🍽': 'plate', '✅': 'chores', '✔': 'chores', '🫙': 'jar',
  '⚙': 'gear', '✎': 'pencil', '✏': 'pencil', '🤝': 'anyone', '🎉': 'party', '⭐': 'star', '🌟': 'star',
  '🛍': 'bag', '⚖': 'scale', '↶': 'undo', '🎁': 'gift', '🎲': 'dice', '📖': 'book', '💡': 'bulb',
  '☀': 'sun', '⛅': 'cloud-sun', '🌤': 'cloud-sun', '☁': 'cloud', '🌫': 'fog', '🌦': 'drizzle', '🌧': 'rain',
  '❄': 'snow', '🌨': 'snow', '⛈': 'storm', '🌩': 'storm',
  '🛏': 'bed', '🧺': 'basket', '🧸': 'teddy', '👕': 'shirt', '🥄': 'spoon', '🫧': 'bubbles', '🗑': 'trash',
  '🍨': 'sundae', '🍦': 'cone', '🥤': 'soda', '🍪': 'cookie', '🍩': 'donut', '🍿': 'popcorn', '🎬': 'movie',
  '🎮': 'game', '🌮': 'taco', '🍝': 'spaghetti', '🫘': 'beans', '🥘': 'paella', '🍲': 'pot', '🥞': 'pancakes',
  '🥪': 'sandwich', '🍕': 'pizza', '🍗': 'drumstick', '🍖': 'drumstick', '🥡': 'takeout', '🍔': 'burger',
  '🥗': 'salad', '🪥': 'toothbrush', '🐾': 'paw', '🐶': 'paw', '🐱': 'paw', '🧹': 'broom', '🪴': 'plant', '🌱': 'plant',
}

const EMOJI_FOR = Object.fromEntries(Object.entries(EMOJI).reverse().map(([e, n]) => [n, e]))

/** Icons offered in the pickers for chores, rewards and meals, with the emoji each one saves as. */
export const PICKER = [
  'star', 'bed', 'basket', 'teddy', 'shirt', 'spoon', 'bubbles', 'trash', 'broom', 'toothbrush', 'paw', 'plant',
  'book', 'plate', 'cart', 'gift', 'sundae', 'cone', 'soda', 'cookie', 'donut', 'popcorn', 'movie', 'game',
  'taco', 'spaghetti', 'beans', 'paella', 'pot', 'pancakes', 'sandwich', 'pizza', 'drumstick', 'takeout',
  'burger', 'salad',
].map((name) => ({ name, emoji: EMOJI_FOR[name] }))

export function iconFor(value) {
  if (!value) return null
  if (ICONS[value]) return value
  return EMOJI[value.replace(/️/g, '').trim()] ?? null
}

/** A drawn icon. Sized in em by default, so it follows the font size of whatever it sits in. */
export function Icon({ name, size = '1.2em', className = '', title }) {
  const draw = ICONS[name]
  if (!draw) return null
  return (
    <svg
      className={`ic ${className}`}
      width={size}
      height={size}
      viewBox="0 0 48 48"
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <g stroke={INK} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
        {draw()}
      </g>
    </svg>
  )
}

/** Icon for a stored chore/reward/meal value: drawn icon when we have one, else the emoji as text. */
export function ItemIcon({ value, fallback = 'star', size, className = '' }) {
  const name = iconFor(value) ?? (value ? null : fallback)
  if (name) return <Icon name={name} size={size} className={className} />
  return <span className={`emoji ${className}`}>{value}</span>
}
