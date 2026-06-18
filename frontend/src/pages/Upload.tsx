import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadApi, pipelineApi } from '../api/client'

interface FileEntry {
  file: File
  type: 'ver' | 'hor' | ''
}

export default function Upload() {
  const navigate = useNavigate()
  const [entries, setEntries] = useState<FileEntry[]>([])
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [dragging, setDragging] = useState(false)

  const addFiles = (incoming: File[]) => {
    const newEntries = incoming.map(f => ({ file: f, type: '' as 'ver' | 'hor' | '' }))
    setEntries(prev => [...prev, ...newEntries])
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const dropped = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.xls') || f.name.endsWith('.xlsx') || f.name.endsWith('.csv'))
    addFiles(dropped)
  }

  const classifyFile = (filename: string): 'ver' | 'hor' | '' => {
    const lower = filename.toLowerCase()
    if (lower.includes('ver') || lower.includes('vertical')) return 'ver'
    if (lower.includes('hor') || lower.includes('horizontal')) return 'hor'
    return ''
  }

  const handleProcess = async () => {
    const toUpload = entries.filter(e => e.type !== '')
    if (toUpload.length === 0) return

    setUploading(true)
    setResult(null)

    try {
      // First upload all files
      const uploadResults = await Promise.all(toUpload.map(e => uploadApi(e.file)))

      // Determine ver_path and hor_path from upload results
      let verPath: string | undefined
      let horPath: string | undefined

      toUpload.forEach((e, i) => {
        if (e.type === 'ver') verPath = uploadResults[i].path
        if (e.type === 'hor') horPath = uploadResults[i].path
      })

      // Run pipeline with the uploaded files
      const pipelineResult = await pipelineApi.run(false, verPath, horPath)

      setResult({
        success: true,
        pipeline: pipelineResult,
        files: uploadResults,
        verPath,
        horPath,
      })
    } catch (err: any) {
      const serverMsg = err.response?.data?.detail || err.response?.data?.message || err.message
      setResult({ success: false, error: serverMsg })
    }

    setUploading(false)
  }

  const setType = (index: number, type: 'ver' | 'hor') => {
    setEntries(prev => prev.map((e, i) => i === index ? { ...e, type } : e))
  }

  const canProcess = entries.some(e => e.type !== '') && !uploading

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Data Upload</h2>
        <p className="text-gray-500 text-sm mt-1">Upload GEOTRAN .xls DAQ files (VER / HOR)</p>
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
          <input type="file" multiple accept=".xls,.xlsx,.csv" className="hidden" onChange={e => addFiles(Array.from(e.target.files || []))} />
        </label>
      </div>

      {entries.length > 0 && (
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
                  <select value={e.type} onChange={e => setType(i, e.target.value as 'ver' | 'hor')}
                    className="text-xs border border-gray-200 rounded px-2 py-1">
                    <option value="">— Select type —</option>
                    <option value="ver">VER (Vertical)</option>
                    <option value="hor">HOR (Horizontal)</option>
                  </select>
                  <button onClick={() => setEntries(entries.filter((_, j) => j !== i))} className="text-danger hover:text-red-700 text-sm">Remove</button>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex gap-3">
            <button onClick={handleProcess} disabled={!canProcess} className="btn-primary">
              {uploading ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
                  Processing...
                </span>
              ) : 'Upload & Process'}
            </button>
            <button onClick={() => setEntries([])} className="btn-secondary bg-gray-100 text-gray-600 hover:bg-gray-200">Clear All</button>
          </div>
          {entries.some(e => e.type === '') && (
            <p className="text-xs text-amber-600 mt-2">Please assign a type (VER/HOR) to each file before processing</p>
          )}
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
                </div>
              )}
              <div className="flex gap-2 mt-3">
                <button onClick={() => navigate('/signals')} className="btn-primary text-sm">View Signals</button>
                <button onClick={() => navigate('/')} className="btn-secondary text-sm">Go to Dashboard</button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-danger">{result.error}</p>
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
