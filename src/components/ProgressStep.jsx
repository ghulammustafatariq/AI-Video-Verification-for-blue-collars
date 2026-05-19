import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Loader2, CheckCircle2, Clock, Video } from 'lucide-react'

const STAGES = [
  { key: 'upload', label: 'Uploading to AI', icon: Video },
  { key: 'index', label: 'Indexing video', icon: Loader2 },
  { key: 'analyze', label: '3-Run Analysis', icon: Loader2 },
  { key: 'compile', label: 'Compiling Results', icon: Loader2 },
]

const TIPS = [
  'Tip: Better lighting = higher accuracy',
  'Tip: Keep the camera steady for best results',
  'Tip: Show the full task from start to finish',
  'Tip: Safety equipment is checked automatically',
  'Tip: Close-up shots improve tool detection',
]

export default function ProgressStep({ category }) {
  const [stage, setStage] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [tipIdx, setTipIdx] = useState(0)

  useEffect(() => {
    const stages = [1800, 4000, 12000, 16000]
    stages.forEach((ms, i) => {
      setTimeout(() => setStage(i + 1), ms)
    })
    const timer = setInterval(() => setElapsed(s => s + 1), 1000)
    const tipTimer = setInterval(() => setTipIdx(t => (t + 1) % TIPS.length), 4000)
    return () => { clearInterval(timer); clearInterval(tipTimer) }
  }, [])

  const mins = Math.floor(elapsed / 60)
  const secs = elapsed % 60
  const pct = Math.min(95, stage * 25 + (elapsed % 6) * 3)

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }}
      className="max-w-lg mx-auto space-y-6">

      {/* Header */}
      <div className="text-center">
        <motion.div
          animate={{ scale: [1, 1.05, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center shadow-lg shadow-primary/20"
        >
          <Loader2 className="w-8 h-8 text-white animate-spin" />
        </motion.div>
        <h2 className="text-lg font-bold text-gray-900 mt-4">AI is analyzing your video</h2>
        <p className="text-sm text-gray-400 mt-1">
          Category: <span className="font-semibold text-gray-700">{category}</span>
          {' · '}
          <Clock className="w-3 h-3 inline" /> {mins}:{String(secs).padStart(2, '0')}
        </p>
      </div>

      {/* Progress Bar */}
      <div className="rounded-2xl bg-white/90 backdrop-blur-sm border border-gray-100 shadow-sm p-5">
        <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-primary to-primary-dark"
            initial={{ width: '0%' }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
        <p className="text-[10px] text-gray-400 text-right mt-1">{pct}%</p>

        {/* Stage Timeline */}
        <div className="mt-5 space-y-3">
          {STAGES.map((s, i) => {
            const done = stage > i
            const active = stage === i
            const pending = stage < i
            return (
              <div key={s.key} className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${
                  done ? 'bg-success text-white' :
                  active ? 'bg-primary text-white' :
                  'bg-gray-100 text-gray-300'
                }`}>
                  {done ? <CheckCircle2 className="w-4 h-4" /> :
                   active ? <Loader2 className="w-4 h-4 animate-spin" /> :
                   <span className="text-[10px] font-bold">{i + 1}</span>}
                </div>
                <div className="flex-1">
                  <p className={`text-xs font-semibold ${
                    done ? 'text-success' : active ? 'text-primary' : 'text-gray-400'
                  }`}>{s.label}</p>
                  {active && (
                    <p className="text-[10px] text-gray-400">Processing...</p>
                  )}
                </div>
                {done && <CheckCircle2 className="w-4 h-4 text-success" />}
              </div>
            )
          })}
        </div>
      </div>

      {/* Tips */}
      <motion.div
        key={tipIdx}
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -5 }}
        className="rounded-2xl bg-primary/5 border border-primary/10 p-4 text-center"
      >
        <p className="text-xs text-primary font-medium">{TIPS[tipIdx]}</p>
      </motion.div>
    </motion.div>
  )
}
