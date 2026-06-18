import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadApi, pipelineApi } from '../api/client'

interface FileEntry {
  file: File
  type: 'ver' | 'hor'
}

function detectType(filename: string): 'ver' | 'hor' {
  const lower = filename.toLowerCase()
  if (lower.includes('hor') || lower.includes('horizontal')) return 'hor'
  return 'ver'
}

export default function Upload() {
  const navigate = useNavigate()
  const [entries, setEntries] = useState<FileEntry[]>([])
  const [phase, setPhase] = useState<'idle' | 'uploading' | 'processing' | 'done' | 'error'>('idle')
  const [result, setResult] = useState<any>(null)
  const [dragging, setDragging] = useState(false)
  const pollingRef = useRef(false)

  useEffect(() => {
    const stored = sessionStorage.getItem('pipeline_task')
    if (stored) {
      try {
        const { task_id } = JSON.parse(stored)
        setPhase('processing')
        startPolling(task_id)
      } catch { /* ignore corrupt storage */ }
    }
    return () => { pollingRef.current = false }
  }, [])

  const addFiles = (incoming: File[]) => {
    setEntries(prev => [...prev, ...incoming.map(f => ({ file: f, type: detectType(f.name) }))])
    setPhase('idle')
    setResult(null)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    addFiles(Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.xls') || f.name.endsWith('.xlsx') || f.name.endsWith('.csv')))
  }

  const startPolling = (tid: string) => {
    pollingRef.current = true
    const pollStart = Date.now()
    const POLL_TIMEOUT = 300000

    const poll = async () => {
      while (pollingRef.current) {
        if (Date.now() - pollStart > POLL_TIMEOUT) {
          setResult({ success: false, error: 'Pipeline timed out after 5 minutes' })
          setPhase('error')
          sessionStorage.removeItem('pipeline_task')
          return
        }
        try {
          const status = await pipelineApi.status(tid)
          if (status.status === 'success') {
            setResult({ success: true, pipeline: status })
            setPhase('done')
            sessionStorage.removeItem('pipeline_task')
            return
          }
          if (status.status === 'error') {
            setResult({ success: false, error: status.error || 'Processing failed' })
            setPhase('error')
            sessionStorage.removeItem('pipeline_task')
            return
          }
        } catch { /* network glitch, retry */ }
        await new Promise(r => setTimeout(r, 2000))
      }
    }
    poll()
  }

  const handleProcess = async () => {
    if (entries.length === 0) return
    setPhase('uploading')
    setResult(null)

    try {
      const uploadResults = await Promise.all(entries.map(e => uploadApi(e.file)))
      let verPath: string | undefined
      let horPath: string | undefined
      entries.forEach((e, i) => {
        if (e.type === 'ver') verPath = uploadResults[i].path
        if (e.type === 'hor') horPath = uploadResults[i].path
      })
      const { task_id } = await pipelineApi.run(false, undefined, verPath, horPath)
      sessionStorage.setItem('pipeline_task', JSON.stringify({ task_id }))
      setPhase('processing')
      startPolling(task_id)
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.response?.data?.message || err.message
      setResult({ success: false, error: msg })
      setPhase('error')
    }
  }

  const dismiss = () => {
    pollingRef.current = false
    sessionStorage.removeItem('pipeline_task')
    setPhase('idle')
    setResult(null)
  }

  const setType = (index: number, type: 'ver' | 'hor') => {
    setEntries(prev => prev.map((e, i) => i === index ? { ...e, type } : e))
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Data Upload</h2>
        <p className="text-gray-500 text-sm mt-1">Upload GEOTRAN .xls DAQ files</p>
      </div>

      <div
        className={`card border-2 border-dashed text-center ${dragging ? 'border-secondary bg-blue-50' : 'border-gray-200'} transition-colors`}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="text-gray-500 mb-2">Drag & drop GEOTRAN .xls files here</p>
        <p className="text-xs text-gray-400 mb-4">or</p>
        <label className="btn-primary cursor-pointer inline-block">
          Browse Files
          <input type="file" multiple accept=".xls,.xlsx,.csv" className="hidden" onChange={e => { addFiles(Array.from(e.target.files || [])) }} />
        </label>
      </div>

      {(phase === 'idle' || phase === 'uploading') && entries.length > 0 && (
        <div className="card">
          <h3 className="card-title">Selected Files ({entries.length})</h3>
          <div className="space-y-2">
            {entries.map((e, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-sm">{e.file.name}</span>
                  <span className="text-xs text-gray-400">{(e.file.size / 1024).toFixed(1)} KB</span>
                </div>
                <div className="flex items-center gap-2">
                  <select value={e.type} onChange={ev => setType(i, ev.target.value as 'ver' | 'hor')}
                    className="text-xs border border-gray-200 rounded px-2 py-1" disabled={phase === 'uploading'}>
                    <option value="ver">Vertical (VER)</option>
                    <option value="hor">Horizontal (HOR)</option>
                  </select>
                  <button onClick={() => setEntries(entries.filter((_, j) => j !== i))}
                    className="text-danger hover:text-red-700 text-sm" disabled={phase === 'uploading'}>Remove</button>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex gap-3">
            <button onClick={handleProcess} disabled={phase === 'uploading'} className="btn-primary">
              {phase === 'uploading' ? 'Uploading...' : 'Upload & Process'}
            </button>
            <button onClick={() => { setEntries([]); setPhase('idle'); setResult(null) }}
              className="btn-secondary bg-gray-100 text-gray-600 hover:bg-gray-200">Clear All</button>
          </div>
        </div>
      )}

      {phase === 'processing' && (
        <div className="card text-center py-8">
          <div className="animate-spin w-8 h-8 border-4 border-secondary border-t-transparent rounded-full mx-auto mb-3"></div>
          <p className="text-sm text-gray-500">Running pipeline analysis...</p>
          <p className="text-xs text-gray-400 mt-1">This normally takes 1–2 minutes. Results will appear below when ready.</p>
        </div>
      )}

      {phase === 'done' && result?.success && (
        <div className="card border-green-200">
          <h3 className="card-title text-success">Pipeline Complete</h3>
          <div className="text-sm text-gray-600 space-y-2">
            <p>Processed {entries.length} file(s)</p>
            {result.pipeline && (
              <div className="mt-3 p-3 bg-green-50 rounded text-xs space-y-1">
                <p>Nf (fatigue): {result.pipeline.life_result?.Nf}  ·  Nr (rutting): {result.pipeline.life_result?.Nr}</p>
                <p>Events detected: {result.pipeline.n_events}  ·  Healthy gauges: {result.pipeline.n_healthy_gauges}</p>
                <p>εt: {result.pipeline.rep_eps_t?.toFixed(1)} µε  ·  εv: {result.pipeline.rep_eps_v?.toFixed(1)} µε</p>
              </div>
            )}
            <div className="flex gap-2 mt-3">
              <button onClick={() => navigate('/signals')} className="btn-primary text-sm">View Signals</button>
              <button onClick={() => navigate('/')} className="btn-secondary text-sm">Go to Dashboard</button>
              <button onClick={dismiss} className="btn-secondary text-sm bg-gray-100 text-gray-600">Upload More</button>
            </div>
          </div>
        </div>
      )}

      {phase === 'error' && (
        <div className="card border-red-200">
          <h3 className="card-title text-danger">Processing Failed</h3>
          <p className="text-sm text-danger">{result?.error}</p>
          <p className="text-xs text-gray-500 mt-1">Check that your files are valid GEOTRAN .xls files.</p>
          <button onClick={dismiss} className="btn-secondary mt-3">Try Again</button>
        </div>
      )}

      {phase === 'idle' && entries.length === 0 && (
        <div className="card bg-blue-50 border-blue-100">
          <h3 className="card-title text-sm text-primary">Using Demo Data</h3>
          <p className="text-xs text-gray-600">
            No files to upload? Navigate to any page — demo data is used automatically.
          </p>
        </div>
      )}
    </div>
  )
}
