const SERVER = 'http://localhost:5000'

export async function analyzeSkillVideo(videoFile, category) {
  const form = new FormData()
  form.append('video', videoFile)
  form.append('category', category)

  const resp = await fetch(`${SERVER}/analyze`, { method: 'POST', body: form })

  if (resp.status === 422) {
    const quality = await resp.json()
    return { status: 'quality_rejected', ...quality }
  }

  if (!resp.ok) {
    let errorMessage = `Server ${resp.status}`
    try {
      const text = await resp.text()
      try {
        const err = JSON.parse(text)
        errorMessage = err.error || err.message || JSON.stringify(err)
      } catch {
        errorMessage = text.slice(0, 200) || errorMessage
      }
    } catch {
      errorMessage = `Server ${resp.status}`
    }
    throw new Error(errorMessage)
  }
  return resp.json()
}

export async function healthCheck() {
  try {
    const r = await fetch(`${SERVER}/health`, { signal: AbortSignal.timeout(3000) })
    return r.ok
  } catch { return false }
}
