import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import UploadStep from './components/UploadStep'
import ProgressStep from './components/ProgressStep'
import ResultsStep from './components/ResultsStep'
import { analyzeSkillVideo, healthCheck } from './lib/api'
import { Sparkles } from 'lucide-react'

const STEPS = ['Upload', 'Analyze', 'Results']

export default function App() {
  const [step, setStep] = useState(1)
  const [category, setCategory] = useState('')
  const [videoFile, setVideoFile] = useState(null)
  const [results, setResults] = useState(null)
  const [mode, setMode] = useState(null)
  const [error, setError] = useState('')
  const [qualityIssues, setQualityIssues] = useState(null)

  const handleSubmit = async () => {
    if (!category || !videoFile) return
    setError('')
    setStep(2)

    const ok = await healthCheck()
    if (!ok) {
      setError('AI server is not running. Start with: python server.py')
      setStep(1)
      return
    }

    try {
      const data = await analyzeSkillVideo(videoFile, category)

      if (data.status === 'quality_rejected') {
        setQualityIssues(data.quality)
        setError('Video quality too low for reliable AI analysis. Please re-record with better lighting and stable camera.')
        setStep(1)
        return
      }

      setResults(data)
      setMode(data.mode || 'twelvelabs')
      setStep(3)
    } catch (e) {
      setError('Analysis failed: ' + e.message)
      setStep(1)
    }
  }

  const reset = () => {
    setStep(1)
    setResults(null)
    setMode(null)
    setError('')
    setQualityIssues(null)
    setVideoFile(null)
    setCategory('')
  }

  return (
    <div className="min-h-screen bg-pattern">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold font-heading text-gray-900">AI Skill Verification</h1>
              <p className="text-[11px] text-gray-400">Powered by Twelve Labs · Pegasus 1.2 + Marengo 3.0</p>
            </div>
          </div>
          {/* Step dots */}
          <div className="flex items-center gap-2">
            {STEPS.map((s, i) => {
              const n = i + 1
              const done = step > n
              const active = step === n
              return (
                <div key={s} className="flex items-center gap-2">
                  <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold transition-all ${
                    done ? 'bg-success/10 text-success' : active ? 'bg-primary text-white' : 'bg-gray-100 text-gray-400'
                  }`}>
                    <span className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold bg-white/20">
                      {done ? '✓' : n}
                    </span>
                    {s}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className={`w-5 h-px ${done ? 'bg-success' : 'bg-gray-200'}`} />
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-6 py-10">
        {error && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
            className="mb-6 px-4 py-3 rounded-xl bg-danger/10 border border-danger/20 text-danger text-sm font-semibold flex items-center gap-2">
            <span>⚠</span> {error}
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          {step === 1 && (
            <UploadStep
              key="upload"
              category={category} setCategory={setCategory}
              videoFile={videoFile} setVideoFile={setVideoFile}
              onSubmit={handleSubmit}
            />
          )}
          {step === 2 && (
            <ProgressStep key="progress" category={category} />
          )}
          {step === 3 && results && (
            <ResultsStep key="results" results={results} mode={mode} category={category} onNewAnalysis={reset} />
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="text-center py-6 text-xs text-gray-400">
        AI Skill Verification · Portfolio Project · Powered by Twelve Labs
      </footer>
    </div>
  )
}
