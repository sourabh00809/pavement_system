import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadApi, uploadPathsApi } from '../api/client'

function detectType(filename: string): 'ver' | 'hor' {
  const lower = filename.toLowerCase()
  if (lower.includes('hor') || lower.includes('horizontal')) return 'hor'
  return 'ver'
}

export default function Upload() {
  const navigate = useNavigate()
  const [files, setFiles] = useState<{ file: File; type: 'ver' | 'hor' }[]>([])
  const [uploading, setUploading] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)

  const addFiles = (incoming: File[]) => {
    setFiles(prev => [...prev, ...incoming.map(f => ({ file: f, type: detectType(f.name) }))])
    setDone(false)
    setError('')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    addFiles(Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.xls') || f.name.endsWith('.xlsx') || f.name.endsWith('.csv')))
  }

  const handleUpload = async () => {
    if (files.length === 0) return
    setUploading(true)
    setError('')
    try {
      const results = await Promise.all(files.map(f => uploadApi(f.file)))
      let verPath: string | undefined
      let horPath: string | undefined
      files.forEach((f, i) => {
        if (f.type === 'ver') verPath = results[i].path
        if (f.type === 'hor') horPath = results[i].path
      })
      await uploadPathsApi.save(verPath, horPath)
      setDone(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.message || err.message)
    }
    setUploading(false)
  }

  const setType = (i: number, type: 'ver' | 'hor') => {
    setFiles(prev => prev.map((f, j) => j === i ? { ...f, type } : f))
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Upload Data</h2>
        <p className="text-gray-500 text-sm mt-1">Upload GEOTRAN .xls DAQ files — no processing, just saving file paths</p>
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

      {(files.length > 0 && !done) && (
        <div className="card">
          <h3 className="card-title">Selected Files ({files.length})</h3>
          <div className="space-y-2">
            {files.map((f, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-sm">{f.file.name}</span>
                  <span className="text-xs text-gray-400">{(f.file.size / 1024).toFixed(1)} KB</span>
                </div>
                <div className="flex items-center gap-2">
                  <select value={f.type} onChange={ev => setType(i, ev.target.value as 'ver' | 'hor')}
                    className="text-xs border border-gray-200 rounded px-2 py-1">
                    <option value="ver">Vertical (VER)</option>
                    <option value="hor">Horizontal (HOR)</option>
                  </select>
                  <button onClick={() => setFiles(files.filter((_, j) => j !== i))}
                    className="text-danger hover:text-red-700 text-sm">Remove</button>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex gap-3">
            <button onClick={handleUpload} disabled={uploading} className="btn-primary">
              {uploading ? 'Uploading...' : 'Upload Files'}
            </button>
            <button onClick={() => { setFiles([]); setDone(false); setError('') }}
              className="btn-secondary bg-gray-100 text-gray-600 hover:bg-gray-200">Clear</button>
          </div>
        </div>
      )}

      {done && (
        <div className="card border-green-200">
          <h3 className="card-title text-success">Files Uploaded</h3>
          <p className="text-sm text-gray-600 mb-3">{files.length} file(s) saved. No processing done yet.</p>
          <div className="flex gap-2">
            <button onClick={() => navigate('/')} className="btn-primary text-sm">Go to Dashboard & Process</button>
            <button onClick={() => { setFiles([]); setDone(false) }} className="btn-secondary text-sm">Upload More</button>
          </div>
        </div>
      )}

      {error && (
        <div className="card border-red-200">
          <h3 className="card-title text-danger">Upload Failed</h3>
          <p className="text-sm text-danger">{error}</p>
          <button onClick={() => setError('')} className="btn-secondary mt-3">Dismiss</button>
        </div>
      )}
    </div>
  )
}
