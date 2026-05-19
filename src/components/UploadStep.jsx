import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { UploadCloud, FileVideo, Info, ChevronRight, Loader2, Wrench, Zap, Paintbrush, Droplets, Thermometer, Hammer, Scissors, Truck, Monitor, Home, Ruler, HelpCircle } from 'lucide-react'

const CATEGORIES = [
  { name: 'Plumbing', icon: Droplets, color: 'text-blue-600', bg: 'bg-blue-50' },
  { name: 'Electrical', icon: Zap, color: 'text-yellow-600', bg: 'bg-yellow-50' },
  { name: 'Cleaning', icon: Droplets, color: 'text-teal-600', bg: 'bg-teal-50' },
  { name: 'AC / HVAC', icon: Thermometer, color: 'text-orange-600', bg: 'bg-orange-50' },
  { name: 'Carpentry', icon: Hammer, color: 'text-amber-700', bg: 'bg-amber-50' },
  { name: 'Painting', icon: Paintbrush, color: 'text-pink-600', bg: 'bg-pink-50' },
  { name: 'Gardening', icon: Scissors, color: 'text-green-600', bg: 'bg-green-50' },
  { name: 'Moving', icon: Truck, color: 'text-indigo-600', bg: 'bg-indigo-50' },
  { name: 'Appliances', icon: Monitor, color: 'text-purple-600', bg: 'bg-purple-50' },
  { name: 'Roofing', icon: Home, color: 'text-red-600', bg: 'bg-red-50' },
  { name: 'Flooring', icon: Ruler, color: 'text-slate-600', bg: 'bg-slate-50' },
  { name: 'Other', icon: HelpCircle, color: 'text-gray-600', bg: 'bg-gray-50' },
]

const INSTRUCTIONS = {
  Plumbing:  ['Demonstrate pipe leak inspection', 'Show proper joint sealing technique', 'Perform pressure testing on pipes', 'Complete a fixture installation'],
  Electrical: ['Show proper PPE and lockout/tagout', 'Demonstrate voltage testing', 'Perform wiring connections correctly', 'Test circuit breaker and explain readings'],
  'AC / HVAC': ['Demonstrate tool selection and safety', 'Show refrigerant handling procedure', 'Perform pressure test and explain readings', 'Complete final system calibration'],
  Cleaning:  ['Show surface assessment technique', 'Demonstrate correct product usage', 'Complete a full room clean to standard', 'Explain safety and chemical handling'],
  Carpentry: ['Demonstrate measuring and marking', 'Show correct saw and chisel technique', 'Perform a joint or assembly task', 'Finish and sand a surface to standard'],
  Painting:  ['Show surface preparation and priming', 'Demonstrate brush and roller technique', 'Apply an even coat without drips', 'Clean up tools and protect surfaces'],
  Gardening: ['Demonstrate lawn mowing and edging', 'Show correct pruning and trimming', 'Perform soil preparation or planting', 'Apply fertilizer or pest control safely'],
  Moving:    ['Show correct heavy lifting technique', 'Demonstrate furniture disassembly', 'Secure items in a vehicle or truck', 'Perform final setup and placement'],
  Appliances: ['Diagnose a common appliance fault', 'Demonstrate safe disassembly', 'Replace a component correctly', 'Test the appliance after repair'],
  Roofing:   ['Demonstrate safe roof access', 'Inspect and identify damaged areas', 'Show correct patching technique', 'Complete final waterproofing check'],
  Flooring:  ['Demonstrate surface prep and leveling', 'Show correct tile laying technique', 'Cut and fit edges accurately', 'Seal or grout the finished surface'],
  Other:     ['Describe the service demonstrated', 'Show your tools and their purpose', 'Perform the core task step by step', 'Explain quality and safety standards'],
}

export default function UploadStep({ category, setCategory, videoFile, setVideoFile, onSubmit }) {
  const fileRef = useRef()
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  const handleFile = (e) => {
    const f = e.target.files?.[0]
    if (f?.type?.startsWith('video/')) setVideoFile(f)
  }

  const handleSubmit = async () => {
    if (!category || !videoFile) return
    setUploading(true)
    await onSubmit()
    setUploading(false)
  }

  const selected = CATEGORIES.find(c => c.name === category)

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} className="space-y-5 max-w-2xl mx-auto">

      {/* Category Grid */}
      <div className="rounded-2xl bg-white/90 backdrop-blur-sm border border-gray-100 shadow-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center">
            <Wrench className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-900">Select Your Trade</h2>
            <p className="text-[11px] text-gray-400">What skill are you demonstrating?</p>
          </div>
        </div>
        <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
          {CATEGORIES.map(({ name, icon: Icon, color, bg }) => {
            const active = category === name
            return (
              <motion.button
                key={name}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setCategory(name)}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border-2 transition-all ${
                  active
                    ? `${bg} border-primary shadow-md shadow-primary/10`
                    : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'
                }`}
              >
                <Icon className={`w-5 h-5 ${active ? color : 'text-gray-400'}`} />
                <span className={`text-[9px] font-semibold leading-tight text-center ${active ? 'text-gray-900' : 'text-gray-400'}`}>
                  {name}
                </span>
              </motion.button>
            )
          })}
        </div>
      </div>

      {/* Upload Zone */}
      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f?.type?.startsWith('video/')) setVideoFile(f) }}
        className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all bg-white/90 backdrop-blur-sm shadow-sm ${
          dragOver ? 'border-primary bg-blue-50 scale-[1.02]' :
          videoFile ? 'border-success/50 bg-green-50' : 'border-gray-200 hover:border-primary/40 hover:bg-blue-50/50'
        }`}
      >
        <input ref={fileRef} type="file" accept="video/mp4,video/quicktime,video/webm" className="hidden" onChange={handleFile} />
        {videoFile ? (
          <div className="flex flex-col items-center gap-2">
            <FileVideo className="w-10 h-10 text-success" />
            <p className="text-sm font-semibold text-gray-900">{videoFile.name}</p>
            <p className="text-xs text-gray-400">{(videoFile.size / 1024 / 1024).toFixed(1)} MB · {videoFile.type?.split('/')[1]?.toUpperCase() || 'VIDEO'}</p>
            <button type="button" onClick={e => { e.stopPropagation(); setVideoFile(null) }}
              className="text-xs text-danger hover:underline mt-1">Remove & choose another</button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-primary/5 flex items-center justify-center">
              <UploadCloud className="w-7 h-7 text-primary/50" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-700">Drop your video here or click to browse</p>
              <p className="text-xs text-gray-400 mt-1">MP4, MOV, WebM · Max 500 MB · Min 10 seconds</p>
            </div>
          </div>
        )}
      </div>

      {/* Preview */}
      <AnimatePresence>
        {videoFile && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
            <video src={URL.createObjectURL(videoFile)} controls className="w-full rounded-2xl max-h-80 object-contain bg-black shadow-lg" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Instructions */}
      <AnimatePresence>
        {category && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl bg-white/90 backdrop-blur-sm border border-gray-100 shadow-sm p-5">
            <div className="flex items-center gap-2 mb-3">
              {selected && <selected.icon className={`w-5 h-5 ${selected.color}`} />}
              <span className="text-sm font-bold text-gray-900">What to demonstrate — {category}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {(INSTRUCTIONS[category] || INSTRUCTIONS.Other).map((inst, i) => (
                <div key={i} className="flex items-start gap-2 p-2.5 rounded-xl bg-gray-50">
                  <span className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold flex-shrink-0">{i + 1}</span>
                  <span className="text-[11px] text-gray-600 leading-relaxed">{inst}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Submit */}
      <motion.button
        whileHover={category && videoFile && !uploading ? { scale: 1.01 } : {}}
        whileTap={{ scale: 0.98 }}
        onClick={handleSubmit}
        disabled={!category || !videoFile || uploading}
        className={`w-full py-4 rounded-2xl font-bold text-sm transition-all flex items-center justify-center gap-2 shadow-lg ${
          category && videoFile && !uploading
            ? 'bg-gradient-to-r from-primary to-primary-dark text-white hover:shadow-primary/30 shadow-primary/20'
            : 'bg-gray-100 text-gray-400 cursor-not-allowed shadow-none'
        }`}
      >
        {uploading ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing your skill video...</>
        ) : (
          <>Submit for AI Analysis <ChevronRight className="w-4 h-4" /></>
        )}
      </motion.button>
    </motion.div>
  )
}
