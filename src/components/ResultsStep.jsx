import { motion } from 'framer-motion'
import {
  ShieldCheck, Star, AlertTriangle, CheckCircle2, RotateCcw, BarChart3, Gauge,
  TrendingUp, TrendingDown, Minus, Target, ArrowUp, XCircle, Banknote, Info
} from 'lucide-react'
import ScoreRing from './ScoreRing'

const SKILL_COLORS = {
  Master:       { color: 'text-purple-500', bg: 'bg-purple-500/10 border-purple-500/30' },
  Experienced:  { color: 'text-primary',    bg: 'bg-primary/10 border-primary/30' },
  Competent:    { color: 'text-success',    bg: 'bg-success/10 border-success/30' },
  Developing:   { color: 'text-warning',    bg: 'bg-warning/10 border-warning/30' },
  'Not Yet Ready': { color: 'text-danger',  bg: 'bg-danger/10 border-danger/30' },
}

const RELIABILITY_COLORS = {
  HIGH:   { color: 'text-success', bg: 'bg-success/10 border-success/30', label: 'High Reliability' },
  MEDIUM: { color: 'text-warning', bg: 'bg-warning/10 border-warning/30', label: 'Medium Reliability' },
  LOW:    { color: 'text-danger',  bg: 'bg-danger/10 border-danger/30',  label: 'Low Reliability' },
}

const card = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
}

export default function ResultsStep({ results, mode, category, onNewAnalysis }) {
  const meta = SKILL_COLORS[results.skillLevel] || SKILL_COLORS.Developing
  const isRejected = results.score === 0 && !results.is_correct_category
  const calibration = results.calibration?.aggregate
  const calReliability = RELIABILITY_COLORS[calibration?.worst_reliability] || RELIABILITY_COLORS.LOW

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-5 max-w-2xl mx-auto">

      {/* ── Category Mismatch Banner (rejected) ── */}
      {isRejected && (
        <motion.div {...card} transition={{ delay: 0 }}
          className="rounded-2xl bg-danger/10 border-2 border-danger/30 p-5">
          <div className="flex items-start gap-3">
            <XCircle className="w-6 h-6 text-danger flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-bold text-danger">Invalid Submission — Score: 0</h3>
              <p className="text-xs text-danger/80 mt-1">
                This video does not contain <strong>{category}</strong> work.
                The AI detected <strong>{results.detected_category}</strong> content instead.
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Please upload a video of you <strong>physically performing {category} tasks</strong> —
                showing tools, techniques, and the complete workflow.
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* ── Score Card ── */}
      <motion.div {...card} transition={{ delay: 0.04 }}
        className="rounded-2xl bg-white/90 backdrop-blur-sm border border-gray-100 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className={`w-10 h-10 rounded-xl ${isRejected ? 'bg-danger/10' : 'bg-primary/10'} flex items-center justify-center`}>
            <Star className={`w-5 h-5 ${isRejected ? 'text-danger' : 'text-primary'}`} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900">AI Analysis Results</h2>
            <p className="text-[11px] text-gray-400">
              {results.detected_category || category} · Twelve Labs (Pegasus + Marengo)
            </p>
          </div>
        </div>

        <ScoreRing score={results.score} rejected={isRejected}
          scoreRange={calibration?.aggregate_score_range} />

        {/* Calibration badges */}
        {calibration && (
          <div className="flex flex-col items-center gap-1.5 mt-3">
            <div className="flex items-center gap-2 text-[10px] text-gray-400">
              <Gauge className="w-3 h-3" />
              <span>Score range: {calibration.aggregate_score_range}</span>
              <span className="text-gray-300">|</span>
              <span>Confidence: {(calibration.mean_confidence * 100).toFixed(0)}%</span>
            </div>
            <span className={`inline-flex items-center gap-1 px-3 py-0.5 rounded-full text-[10px] font-bold border ${calReliability.bg} ${calReliability.color}`}>
              <BarChart3 className="w-3 h-3" /> {calReliability.label}
            </span>
          </div>
        )}

        {/* Skill badge */}
        <div className="flex justify-center mt-4">
          <span className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-bold border ${meta.bg} ${meta.color}`}>
            <ShieldCheck className="w-3.5 h-3.5" /> {results.skillLevel}
          </span>
        </div>

        {/* Category warning (non-rejected but mismatch) */}
        {!results.is_correct_category && !isRejected && (
          <div className="mt-4 px-4 py-2.5 rounded-xl bg-danger/10 border border-danger/20 text-center">
            <p className="text-xs font-bold text-danger">
              Category Mismatch — Video appears to show <strong>{results.detected_category}</strong>, not {category}
            </p>
          </div>
        )}
      </motion.div>

      {/* ── Segment Table ── */}
      {results.segments?.length > 0 && (
        <motion.div {...card} transition={{ delay: 0.08 }}
          className="rounded-2xl bg-white/90 backdrop-blur-sm border border-gray-100 shadow-sm p-5 overflow-x-auto">
          <h3 className="font-bold text-sm text-gray-900 mb-3">Segment Breakdown</h3>
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-gray-400 font-bold uppercase tracking-wider">
                <th className="text-left pb-2 pr-2">#</th>
                <th className="text-left pb-2 pr-2">Time</th>
                <th className="text-left pb-2 pr-2">Actions</th>
                <th className="text-center pb-2 pr-2">Viol.</th>
                <th className="text-center pb-2 pr-1">Score</th>
                <th className="text-center pb-2">Result</th>
              </tr>
            </thead>
            <tbody>
              {results.segments.map((seg, i) => (
                <motion.tr key={seg.id || i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }} className="border-b border-gray-50">
                  <td className="py-2.5 px-1 text-gray-400 font-medium text-[10px]">{seg.id || i + 1}</td>
                  <td className="py-2.5 px-1 text-gray-400 text-[10px]">{seg.timeRange}</td>
                  <td className="py-2.5 px-1 text-gray-700 text-[10px] max-w-[180px] truncate">{seg.actions}</td>
                  <td className="py-2.5 px-1 text-center">
                    {seg.violations > 0 ? <span className="text-[10px] font-bold text-danger">{seg.violations}</span> :
                     <span className="text-[10px] font-bold text-success">0</span>}
                  </td>
                  <td className="py-2.5 px-1 text-center">
                    <span className={`text-xs font-bold ${seg.score >= 80 ? 'text-success' : seg.score >= 60 ? 'text-warning' : 'text-danger'}`}>
                      {seg.score}
                    </span>
                  </td>
                  <td className="py-2.5 px-1 text-center">
                    {seg.pass
                      ? <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[9px] font-bold bg-success/10 text-success">PASS</span>
                      : <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[9px] font-bold bg-danger/10 text-danger">FAIL</span>}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      )}

      {/* ── Violations ── */}
      {results.violations?.length > 0 && (
        <motion.div {...card} transition={{ delay: 0.12 }}
          className="rounded-2xl bg-white/90 backdrop-blur-sm border border-gray-100 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-danger" />
            <h3 className="font-bold text-sm text-gray-900">Violations</h3>
            {results.verified_violations?.length > 0 && (
              <span className="text-[10px] text-gray-400">
                ({results.verified_violations.length} verified, {results.unverified_violations?.length || 0} unverified hidden)
              </span>
            )}
          </div>
          <div className="space-y-2">
            {results.violations.map((v, i) => (
              <div key={i} className={`flex items-start gap-2.5 px-3 py-2.5 rounded-xl ${
                v.type === 'MAJOR' ? 'bg-danger/5 border border-danger/10' : 'bg-warning/5 border border-warning/10'
              }`}>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 mt-0.5 ${
                  v.type === 'MAJOR' ? 'bg-danger/10 text-danger' : 'bg-warning/10 text-warning'
                }`}>{v.type}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] text-gray-600">{v.reason}</p>
                  {v.verified && (
                    <span className="inline-flex items-center gap-0.5 text-[9px] text-success font-semibold mt-0.5">
                      <CheckCircle2 className="w-2.5 h-2.5" /> Verified ({v.occurrences}/3 runs)
                    </span>
                  )}
                  {v.verified === false && (
                    <span className="inline-flex items-center gap-0.5 text-[9px] text-warning font-semibold mt-0.5">
                      <AlertTriangle className="w-2.5 h-2.5" /> Unverified ({v.occurrences}/3 runs)
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Strengths ── */}
      {results.strengths?.length > 0 && (
        <motion.div {...card} transition={{ delay: 0.16 }}
          className="rounded-2xl bg-white/90 backdrop-blur-sm border border-gray-100 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-4 h-4 text-success" />
            <h3 className="font-bold text-sm text-gray-900">Strengths</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {results.strengths.map((s, i) => (
              <div key={i} className="flex items-start gap-2 px-3 py-2.5 rounded-xl bg-success/5 border border-success/10">
                <span className="text-success text-xs mt-0.5">+</span>
                <p className="text-[11px] text-gray-600">{s}</p>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Temporal Consistency ── */}
      {results.temporal?.data && results.temporal.data.segment_scores?.length > 1 && (
        <motion.div {...card} transition={{ delay: 0.18 }}
          className="rounded-2xl bg-white/90 backdrop-blur-sm border border-gray-100 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-3">
            {results.temporal.data.trend === 'improving' ? <TrendingUp className="w-4 h-4 text-success" /> :
             results.temporal.data.trend === 'degrading' ? <TrendingDown className="w-4 h-4 text-danger" /> :
             <Minus className="w-4 h-4 text-gray-400" />}
            <h3 className="font-bold text-sm text-gray-900">Temporal Consistency</h3>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
              results.temporal.data.trend === 'steady' ? 'bg-success/10 text-success' :
              results.temporal.data.trend === 'improving' ? 'bg-primary/10 text-primary' :
              results.temporal.data.trend === 'degrading' ? 'bg-danger/10 text-danger' :
              'bg-warning/10 text-warning'
            }`}>{results.temporal.data.trend.toUpperCase()}</span>
          </div>
          <p className="text-[11px] text-gray-500 mb-3">{results.temporal.data.interpretation}</p>
          <div className="flex items-end gap-1 h-16">
            {results.temporal.data.segment_scores.map((s, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-[9px] text-gray-500 font-medium">{s}</span>
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: `${Math.max(s, 2)}%` }}
                  transition={{ delay: 0.3 + i * 0.05, duration: 0.5 }}
                  className="w-full rounded-t-sm max-h-[40px] min-h-[2px]"
                  style={{ backgroundColor: s >= 80 ? '#34A853' : s >= 60 ? '#F9AB00' : '#EA4335' }}
                />
                <span className="text-[8px] text-gray-300">{results.temporal.data.segment_labels?.[i] || i+1}</span>
              </div>
            ))}
          </div>
          {results.temporal.fatigue?.warning && (
            <div className="mt-3 px-3 py-2 rounded-lg bg-danger/5 border border-danger/10">
              <p className="text-[11px] text-danger font-semibold">{results.temporal.fatigue.message}</p>
            </div>
          )}
        </motion.div>
      )}

      {/* ── Improvement Roadmap ── */}
      {results.roadmap?.steps?.length > 0 && !isRejected && (
        <motion.div {...card} transition={{ delay: 0.2 }}
          className="rounded-2xl bg-white/90 backdrop-blur-sm border border-gray-100 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-4 h-4 text-primary" />
            <h3 className="font-bold text-sm text-gray-900">Improvement Roadmap</h3>
            <span className="text-[10px] text-gray-400">
              {results.roadmap.current_level} → {results.roadmap.target_level}
            </span>
          </div>
          <p className="text-[11px] text-gray-500 mb-3">
            Fix these to go from <strong>{results.roadmap.current_score}</strong> to{' '}
            <strong className="text-success">{results.roadmap.potential_score}</strong>
            {' '}· ~{results.roadmap.estimated_timeline}
          </p>
          <div className="space-y-2">
            {results.roadmap.steps.map((step, i) => (
              <div key={i} className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  step.difficulty === 'Easy' ? 'bg-success/10' :
                  step.difficulty === 'Medium' ? 'bg-warning/10' : 'bg-danger/10'
                }`}>
                  <ArrowUp className={`w-4 h-4 ${
                    step.difficulty === 'Easy' ? 'text-success' :
                    step.difficulty === 'Medium' ? 'text-warning' : 'text-danger'
                  }`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] text-gray-700 font-medium leading-snug">{step.action}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-success font-bold">+{step.impact_points} pts</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-semibold ${
                      step.difficulty === 'Easy' ? 'bg-success/10 text-success' :
                      step.difficulty === 'Medium' ? 'bg-warning/10 text-warning' :
                      'bg-danger/10 text-danger'
                    }`}>{step.difficulty}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Calibration Detail ── */}
      {results.calibration?.per_chunk?.length > 0 && (
        <motion.div {...card} transition={{ delay: 0.22 }}
          className="rounded-2xl bg-white/90 backdrop-blur-sm border border-gray-100 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-primary" />
            <h3 className="font-bold text-sm text-gray-900">Calibration Detail</h3>
            <span className="text-[10px] text-gray-400">{results.calibration.per_chunk.length} chunk(s)</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {results.calibration.per_chunk.map((c, i) => (
              <div key={i} className="rounded-xl bg-gray-50 p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-semibold text-gray-500">Chunk #{c.chunk}</span>
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                    c.reliability === 'HIGH' ? 'bg-success/10 text-success' :
                    c.reliability === 'MEDIUM' ? 'bg-warning/10 text-warning' :
                    'bg-danger/10 text-danger'
                  }`}>{c.reliability}</span>
                </div>
                <div className="flex items-end gap-1 h-8 mb-1">
                  {c.individual_scores.map((s, j) => (
                    <motion.div
                      key={j}
                      initial={{ height: 0 }}
                      animate={{ height: `${Math.max(s, 4)}%` }}
                      transition={{ delay: j * 0.1 }}
                      className="flex-1 rounded-t-sm"
                      style={{ backgroundColor: s >= 80 ? '#34A853' : s >= 60 ? '#F9AB00' : '#EA4335' }}
                    />
                  ))}
                </div>
                <div className="flex items-center justify-between text-[9px] text-gray-400">
                  <span>{c.score_range}</span>
                  <span>{(c.confidence * 100).toFixed(0)}% conf</span>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Summary ── */}
      {results.summary && (
        <motion.div {...card} transition={{ delay: 0.24 }}
          className={`rounded-2xl p-5 text-center ${
            isRejected ? 'bg-danger/5 border border-danger/10' : 'bg-primary/5 border border-primary/10'
          }`}>
          <p className={`text-sm italic ${isRejected ? 'text-danger' : 'text-gray-700'}`}>
            "{results.summary}"
          </p>
        </motion.div>
      )}

      {/* ── New Analysis ── */}
      <div className="flex justify-center pt-2 pb-4">
        <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
          onClick={onNewAnalysis}
          className="flex items-center gap-2 px-8 py-3.5 rounded-2xl bg-gradient-to-r from-primary to-primary-dark text-white text-sm font-bold hover:shadow-xl hover:shadow-primary/20 transition-all">
          <RotateCcw className="w-4 h-4" /> New Analysis
        </motion.button>
      </div>
    </motion.div>
  )
}
