import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadApi, pipelineApi } from '../api/client'

function autoTag(filename: string): 'VER' | 'HOR' | '' {
  const lower = filename.toLowerCase()
  if (lower.includes('ver') || lower.includes('vertical')) return 'VER'
  if (lower.includes('hor') || lower.includes('horizontal')) return 'HOR'
  return ''
}

export default function Upload() {
  const navigate = useNavigate()
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [dragging, setDragging] = useState(false)
  const pollingRef = useRef(false)

  const addFiles = (incoming: File[]) => {
    setFiles(prev => [...prev, ...incoming])
    setResult(null)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    addFiles(Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.xls') || f.name.endsWith('.xlsx') || f.name.endsWith('.csv')))
  }

  const handleProcess = async () => {
    if (files.length === 0) return

    setUploading(true)
    setResult(null)
    pollingRef.current = true

    try {
      const uploadResults = await Promise.all(files.map(f => uploadApi(f)))
      const filePaths = uploadResults.map(r => r.path)

      const { task_id } = await pipelineApi.run(false, filePaths)

      const pollStart = Date.now()
      const POLL_TIMEOUT = 300000
      let pipelineResult: any

      while (pollingRef.current) {
        if (Date.now() - pollStart > POLL_TIMEOUT) {
          throw new Error('Pipeline timed out after 5 minutes')
        }
        const status = await pipelineApi.status(task_id)
        if (status.status === 'success') {
          pipelineResult = status
          break
        }
        if (status.status === 'error') {
          throw new Error(status.error || 'Pipeline processing failed')
        }
        await new Promise(r => setTimeout(r, 2000))
      }

      if (!pipelineResult) throw new Error('Processing cancelled')

      setResult({ success: true, pipeline: pipelineResult, files: uploadResults })
    } catch (err: any) {
      const serverMsg = err.response?.data?.detail || err.response?.data?.message || err.message
      setResult({ success: false, error: serverMsg })
    }

    setUploading(false)
    pollingRef.current = false
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
          <input type="file" multiple accept=".xls,.xlsx,.csv" className="hidden" onChange={e => { setResult(null); addFiles(Array.from(e.target.files || [])) }} />
        </label>
      </div>

      {files.length > 0 && (
        <div className="card">
          <h3 className="card-title">Selected Files ({files.length})</h3>
          <div className="space-y-2">
            {files.map((f, i) => {
              const tag = autoTag(f.name)
              return (
                <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="text-sm">{f.name}</span>
                    <span className="text-xs text-gray-400">{(f.size / 1024).toFixed(1)} KB</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {tag && (
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${tag === 'VER' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                        {tag}
                      </span>
                    )}
                    <button onClick={() => setFiles(files.filter((_, j) => j !== i))} className="text-danger hover:text-red-700 text-sm">Remove</button>
                  </div>
                </div>
              )
            })}
          </div>
          <div className="mt-4 flex gap-3">
            <button onClick={handleProcess} disabled={uploading} className="btn-primary">
              {uploading ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
                  Processing...
                </span>
              ) : 'Upload & Process'}
            </button>
            <button onClick={() => { setFiles([]); setResult(null) }} className="btn-secondary bg-gray-100 text-gray-600 hover:bg-gray-200">Clear All</button>
          </div>
        </div>
      )}

      {uploading && !result && (
        <div className="card text-center py-8">
          <div className="animate-spin w-8 h-8 border-4 border-secondary border-t-transparent rounded-full mx-auto mb-3"></div>
          <p className="text-sm text-gray-500">Running pipeline analysis...</p>
          <p className="text-xs text-gray-400 mt-1">Processing may take a few minutes for large files</p>
        </div>
      )}

      {result && (
        <div className={`card ${result.success ? 'border-green-200' : 'border-red-200'}`}>
          <h3 className={`card-title ${result.success ? 'text-success' : 'text-danger'}`}>
            {result.success ? 'Pipeline Complete' : 'Processing Failed'}
          </h3>
          {result.success ? (
            <div className="text-sm text-gray-600 space-y-2">
              <p>Uploaded files:</p>
              <ul className="space-y-1">
                {result.files.map((f: any, i: number) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-400"></span>
                    {f.filename}
                  </li>
                ))}
              </ul>
              {result.pipeline && (
                <div className="mt-3 p-3 bg-green-50 rounded text-xs">
                  <p>Nf (fatigue): {result.pipeline.life_result?.Nf}</p>
                  <p>Nr (rutting): {result.pipeline.life_result?.Nr}</p>
                  <p>Events detected: {result.pipeline.n_events}</p>
                  <p>Healthy gauges: {result.pipeline.n_healthy_gauges}</p>
                  <p>εt: {result.pipeline.rep_eps_t?.toFixed(1)} µε · εv: {result.pipeline.rep_eps_v?.toFixed(1)} µε</p>
                </div>
              )}
              <div className="flex gap-2 mt-3">
                <button onClick={() => navigate('/signals')} className="btn-primary text-sm">View Signals</button>
                <button onClick={() => navigate('/')} className="btn-secondary text-sm">Go to Dashboard</button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-danger">
              <p className="font-medium mb-1">{result.error}</p>
              <p className="text-xs text-gray-500">Check that your files are valid GEOTRAN .xls files. You can also try using demo data by navigating to any page.</p>
            </div>
          )}
        </div>
      )}

      <div className="card bg-blue-50 border-blue-100">
        <h3 className="card-title text-sm text-primary">Using Demo Data</h3>
        <p className="text-xs text-gray-600">
          No files to upload? Navigate to any page — demo data is used automatically.
          To switch back to demo after uploading, use the "Refresh Pipeline Data" button on the Export page.
        </p>
      </div>
    </div>
  )
}
