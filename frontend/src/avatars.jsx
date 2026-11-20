/**
 * Built-in avatars: simple animal faces drawn for this project (original art, no licence needed).
 * Each is drawn in a 100x100 box. Add one by adding an entry to AVATARS.
 */

const INK = '#1f2937'
const CHEEK = '#fda4af'

const eyes = (y = 54, dx = 11, r = 4.2) => (
  <g>
    <circle cx={50 - dx} cy={y} r={r} fill={INK} />
    <circle cx={50 + dx} cy={y} r={r} fill={INK} />
    <circle cx={50 - dx + 1.4} cy={y - 1.5} r={r * 0.35} fill="#fff" />
    <circle cx={50 + dx + 1.4} cy={y - 1.5} r={r * 0.35} fill="#fff" />
  </g>
)
const cheeks = (y = 64, dx = 19) => (
  <g opacity="0.75">
    <circle cx={50 - dx} cy={y} r="4.5" fill={CHEEK} />
    <circle cx={50 + dx} cy={y} r="4.5" fill={CHEEK} />
  </g>
)
const smile = (y = 68) => (
  <path d={`M44 ${y} Q50 ${y + 5} 56 ${y}`} stroke={INK} strokeWidth="2.2" fill="none" strokeLinecap="round" />
)
const head = (fill, r = 30, cy = 57) => <circle cx="50" cy={cy} r={r} fill={fill} />

export const AVATARS = [
  {
    id: 'cat',
    name: 'Cat',
    draw: () => (
      <>
        <path d="M24 44 L28 16 L46 32 Z" fill="#f4a259" />
        <path d="M76 44 L72 16 L54 32 Z" fill="#f4a259" />
        <path d="M29 36 L31 23 L40 31 Z" fill={CHEEK} />
        <path d="M71 36 L69 23 L60 31 Z" fill={CHEEK} />
        {head('#f4a259')}
        {eyes()}
        {cheeks()}
        <path d="M47 61 L53 61 L50 64 Z" fill={INK} />
        <path d="M50 64 Q46 69 43 66 M50 64 Q54 69 57 66" stroke={INK} strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M22 60 L36 62 M22 67 L36 65 M78 60 L64 62 M78 67 L64 65" stroke={INK} strokeWidth="1.4" strokeLinecap="round" />
      </>
    ),
  },
  {
    id: 'dog',
    name: 'Puppy',
    draw: () => (
      <>
        {head('#e9c08f')}
        <ellipse cx="23" cy="52" rx="10" ry="19" fill="#8b5e3c" transform="rotate(15 23 52)" />
        <ellipse cx="77" cy="52" rx="10" ry="19" fill="#8b5e3c" transform="rotate(-15 77 52)" />
        <ellipse cx="50" cy="68" rx="14" ry="10" fill="#f8e3c8" />
        {eyes(52)}
        <ellipse cx="50" cy="63" rx="5.5" ry="4" fill={INK} />
        {smile(69)}
        <path d="M50 72 Q50 79 54 78 Q57 77 55 72" fill="#f87171" />
      </>
    ),
  },
  {
    id: 'bear',
    name: 'Bear',
    draw: () => (
      <>
        <circle cx="26" cy="32" r="11" fill="#9a6b4b" />
        <circle cx="74" cy="32" r="11" fill="#9a6b4b" />
        <circle cx="26" cy="32" r="5.5" fill="#d9a77f" />
        <circle cx="74" cy="32" r="5.5" fill="#d9a77f" />
        {head('#9a6b4b')}
        <ellipse cx="50" cy="67" rx="13" ry="10" fill="#d9a77f" />
        {eyes(52)}
        <ellipse cx="50" cy="63" rx="5" ry="3.6" fill={INK} />
        {smile(68)}
      </>
    ),
  },
  {
    id: 'bunny',
    name: 'Bunny',
    draw: () => (
      <>
        <ellipse cx="38" cy="22" rx="8" ry="20" fill="#e5e7eb" />
        <ellipse cx="62" cy="22" rx="8" ry="20" fill="#e5e7eb" />
        <ellipse cx="38" cy="23" rx="4" ry="14" fill={CHEEK} />
        <ellipse cx="62" cy="23" rx="4" ry="14" fill={CHEEK} />
        {head('#f3f4f6', 29, 60)}
        {eyes(57)}
        {cheeks(67)}
        <path d="M47 64 L53 64 L50 67 Z" fill="#f472b6" />
        <path d="M50 67 Q46 72 43 69 M50 67 Q54 72 57 69" stroke={INK} strokeWidth="2" fill="none" strokeLinecap="round" />
      </>
    ),
  },
  {
    id: 'fox',
    name: 'Fox',
    draw: () => (
      <>
        <path d="M22 48 L24 14 L46 34 Z" fill="#ea7a2b" />
        <path d="M78 48 L76 14 L54 34 Z" fill="#ea7a2b" />
        <path d="M28 38 L28 24 L39 33 Z" fill="#1f2937" />
        <path d="M72 38 L72 24 L61 33 Z" fill="#1f2937" />
        {head('#ea7a2b')}
        <path d="M22 60 Q36 56 50 80 Q64 56 78 60 Q72 86 50 87 Q28 86 22 60 Z" fill="#fff7ed" />
        {eyes(53)}
        <ellipse cx="50" cy="70" rx="4.5" ry="3.4" fill={INK} />
      </>
    ),
  },
  {
    id: 'panda',
    name: 'Panda',
    draw: () => (
      <>
        <circle cx="26" cy="32" r="11" fill={INK} />
        <circle cx="74" cy="32" r="11" fill={INK} />
        {head('#ffffff')}
        <circle cx="50" cy="57" r="30" fill="none" stroke="#e5e7eb" strokeWidth="1.5" />
        <ellipse cx="38" cy="54" rx="8" ry="10" fill={INK} transform="rotate(25 38 54)" />
        <ellipse cx="62" cy="54" rx="8" ry="10" fill={INK} transform="rotate(-25 62 54)" />
        <circle cx="39" cy="53" r="3" fill="#fff" />
        <circle cx="61" cy="53" r="3" fill="#fff" />
        <ellipse cx="50" cy="65" rx="4.5" ry="3.2" fill={INK} />
        {smile(70)}
        {cheeks(68, 21)}
      </>
    ),
  },
  {
    id: 'owl',
    name: 'Owl',
    draw: () => (
      <>
        <path d="M26 34 L30 18 L40 30 Z" fill="#7c5a3a" />
        <path d="M74 34 L70 18 L60 30 Z" fill="#7c5a3a" />
        {head('#7c5a3a', 31, 56)}
        <ellipse cx="50" cy="72" rx="17" ry="13" fill="#c8a27a" />
        <circle cx="38" cy="50" r="11" fill="#fff" />
        <circle cx="62" cy="50" r="11" fill="#fff" />
        <circle cx="38" cy="50" r="5" fill={INK} />
        <circle cx="62" cy="50" r="5" fill={INK} />
        <circle cx="39.5" cy="48.5" r="1.7" fill="#fff" />
        <circle cx="63.5" cy="48.5" r="1.7" fill="#fff" />
        <path d="M45 60 L55 60 L50 68 Z" fill="#f59e0b" />
      </>
    ),
  },
  {
    id: 'frog',
    name: 'Frog',
    draw: () => (
      <>
        <circle cx="34" cy="34" r="12" fill="#6cc04a" />
        <circle cx="66" cy="34" r="12" fill="#6cc04a" />
        {head('#6cc04a', 30, 60)}
        <circle cx="34" cy="34" r="7" fill="#fff" />
        <circle cx="66" cy="34" r="7" fill="#fff" />
        <circle cx="34" cy="35" r="3.8" fill={INK} />
        <circle cx="66" cy="35" r="3.8" fill={INK} />
        <path d="M34 66 Q50 78 66 66" stroke={INK} strokeWidth="2.4" fill="none" strokeLinecap="round" />
        {cheeks(64, 22)}
        <circle cx="46" cy="56" r="1.4" fill={INK} />
        <circle cx="54" cy="56" r="1.4" fill={INK} />
      </>
    ),
  },
  {
    id: 'penguin',
    name: 'Penguin',
    draw: () => (
      <>
        {head('#334155', 31, 56)}
        <path d="M50 42 Q30 34 27 58 Q28 84 50 86 Q72 84 73 58 Q70 34 50 42 Z" fill="#fff" />
        {eyes(54, 10)}
        <path d="M44 62 L56 62 L50 69 Z" fill="#f59e0b" />
        {cheeks(66, 17)}
      </>
    ),
  },
  {
    id: 'lion',
    name: 'Lion',
    draw: () => (
      <>
        <circle cx="50" cy="56" r="40" fill="#b45309" />
        <circle cx="30" cy="32" r="7" fill="#f6c453" />
        <circle cx="70" cy="32" r="7" fill="#f6c453" />
        {head('#f6c453', 28, 57)}
        <ellipse cx="50" cy="68" rx="11" ry="8" fill="#fde68a" />
        {eyes(52, 10)}
        <path d="M46 62 L54 62 L50 66 Z" fill={INK} />
        {smile(69)}
      </>
    ),
  },
  {
    id: 'koala',
    name: 'Koala',
    draw: () => (
      <>
        <circle cx="22" cy="40" r="15" fill="#9ca3af" />
        <circle cx="78" cy="40" r="15" fill="#9ca3af" />
        <circle cx="22" cy="40" r="8" fill="#e5e7eb" />
        <circle cx="78" cy="40" r="8" fill="#e5e7eb" />
        {head('#9ca3af', 29, 58)}
        {eyes(52, 12, 3.8)}
        <ellipse cx="50" cy="63" rx="7" ry="9" fill="#374151" />
        {cheeks(68, 18)}
      </>
    ),
  },
  {
    id: 'chick',
    name: 'Chick',
    draw: () => (
      <>
        <path d="M46 28 Q44 18 50 20 Q52 12 56 20 Q60 18 56 28 Z" fill="#facc15" />
        {head('#fde047', 30, 58)}
        {eyes(54, 11)}
        <path d="M43 62 L57 62 L50 70 Z" fill="#f97316" />
        {cheeks(66, 19)}
      </>
    ),
  },
]

const BY_ID = Object.fromEntries(AVATARS.map((a) => [a.id, a]))

/** A person's avatar: the chosen animal on a ring of their colour, or their initial if none chosen. */
export default function Avatar({ person, size = 40 }) {
  const art = BY_ID[person?.avatar]
  const color = person?.color ?? '#cbd5e1'
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" className="avatar" aria-hidden="true">
      <circle cx="50" cy="50" r="48" fill={art ? '#ffffff' : color} stroke={color} strokeWidth="4" />
      {art ? (
        <g transform="translate(50 50) scale(0.86) translate(-50 -50)">{art.draw()}</g>
      ) : (
        <text x="50" y="50" dy="0.35em" textAnchor="middle" fontSize="48" fontWeight="700" fill="#334155">
          {(person?.name ?? '?').slice(0, 1).toUpperCase()}
        </text>
      )}
    </svg>
  )
}

export function AvatarArt({ id, size = 64 }) {
  const art = BY_ID[id]
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
      {art?.draw()}
    </svg>
  )
}
