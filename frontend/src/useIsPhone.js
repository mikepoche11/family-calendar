import { useEffect, useState } from 'react'

// Matches the phone breakpoint in phone.css. The wall screen is always wider than this.
const QUERY = '(max-width: 700px)'

export default function useIsPhone() {
  const [isPhone, setIsPhone] = useState(() => window.matchMedia(QUERY).matches)
  useEffect(() => {
    const mq = window.matchMedia(QUERY)
    const update = () => setIsPhone(mq.matches)
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])
  return isPhone
}
