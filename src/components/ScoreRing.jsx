import { useState, useEffect } from 'react'
import { motion, useMotionValue, animate } from 'framer-motion'
import { XCircle } from 'lucide-react'

export default function ScoreRing({ score, scoreRange, rejected }) {
  const motionVal = useMotionValue(0)
  const [display, setDisplay] = useState(0)
  const r = 54
  const circumference = 2 * Math.PI * r

  useEffect(() => {
    const ctrl = animate(motionVal, rejected ? 0 : score, {
      duration: 2,
      ease: 'easeOut',
      onUpdate: v => setDisplay(Math.round(v)),
    })
    return ctrl.stop
  }, [score, rejected])

  const offset = ((100 - display) / 100) * circumference

  const getColor = (s) => {
    if (rejected) return '#EA4335'
    if (s >= 80) return '#34A853'
    if (s >= 60) return '#F9AB00'
    return '#EA4335'
  }

  const color = getColor(display)
  const gradientId = `scoreGradient-${display}`

  return (
    <div className="relative w-48 h-48 mx-auto">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={color} />
            <stop offset="100%" stopColor={color} stopOpacity="0.7" />
          </linearGradient>
        </defs>
        <circle cx="60" cy="60" r={r} fill="none" strokeWidth="9" className="stroke-gray-100" />
        <motion.circle cx="60" cy="60" r={r} fill="none" strokeWidth="9"
          stroke={`url(#${gradientId})`} strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transition={{ duration: 2, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {rejected ? (
          <>
            <XCircle className="w-10 h-10 text-danger mb-1" />
            <span className="text-lg font-extrabold text-danger">0</span>
            <span className="text-[9px] font-medium text-danger/70 mt-0.5">REJECTED</span>
          </>
        ) : (
          <>
            <span className="text-5xl font-extrabold text-gray-900">{display}</span>
            <span className="text-xs font-medium text-gray-400">out of 100</span>
            {scoreRange && scoreRange !== '0-0' && (
              <span className="text-[10px] text-gray-400 mt-0.5">
                Range: {scoreRange}
              </span>
            )}
          </>
        )}
      </div>
    </div>
  )
}
