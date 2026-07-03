import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadApi, uploadPathsApi } from '../api/client'

export default function Upload() {
  const navigate = useNavigate()
  const [files, setFiles] = useState<{ file: File; type: 'VER' | 'HOR' }[]>([])
  const [uploading, setUploading] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)

  const addFiles = (incoming: File[]) => {
    setFiles(prev => [...prev, ...incoming.map(f => ({ file: f, type: 'VER' as 'VER' | 'HOR' }))])
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
      const typedFiles = results.map((r, i) => ({ path: r.path, type: files[i].type }))
      await uploadPathsApi.save(typedFiles)
      sessionStorage.setItem('pendingUploadFiles', JSON.stringify(typedFiles))
      setDone(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.message || err.message)
    }
    setUploading(false)
  }

  const setType = (i: number, type: 'VER' | 'HOR') => {
    setFiles(prev => prev.map((f, j) => j === i ? { ...f, type } : f))
  }

  const verFiles = files.filter(f => f.type === 'VER')
  const horFiles = files.filter(f => f.type === 'HOR')

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Upload Data</h2>
        <p className="text-gray-500 text-sm mt-1">Upload GEOTRAN .xls DAQ files — specify each file as Vertical or Horizontal</p>
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

          {verFiles.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-primary mb-2">Vertical (VER) — {verFiles.length} file(s)</h4>
              {verFiles.map((f, i) => {
                const idx = files.indexOf(f)
                return (
                  <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-50">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-secondary" />
                      <span className="text-sm">{f.file.name}</span>
                      <span className="text-xs text-gray-400">{(f.file.size / 1024).toFixed(1)} KB</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <select value={f.type} onChange={ev => setType(idx, ev.target.value as 'VER' | 'HOR')}
                        className="text-xs border border-gray-200 rounded px-2 py-1">
                        <option value="VER">Vertical (VER)</option>
                        <option value="HOR">Horizontal (HOR)</option>
                      </select>
                      <button onClick={() => setFiles(files.filter((_, j) => j !== idx))}
                        className="text-danger hover:text-red-700 text-sm">Remove</button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {horFiles.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-amber-600 mb-2">Horizontal (HOR) — {horFiles.length} file(s)</h4>
              {horFiles.map((f, i) => {
                const idx = files.indexOf(f)
                return (
                  <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-50">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-amber-500" />
                      <span className="text-sm">{f.file.name}</span>
                      <span className="text-xs text-gray-400">{(f.file.size / 1024).toFixed(1)} KB</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <select value={f.type} onChange={ev => setType(idx, ev.target.value as 'VER' | 'HOR')}
                        className="text-xs border border-gray-200 rounded px-2 py-1">
                        <option value="VER">Vertical (VER)</option>
                        <option value="HOR">Horizontal (HOR)</option>
                      </select>
                      <button onClick={() => setFiles(files.filter((_, j) => j !== idx))}
                        className="text-danger hover:text-red-700 text-sm">Remove</button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          <div className="mt-4 flex gap-3">
            <button onClick={handleUpload} disabled={uploading} className="btn-primary">
              {uploading ? 'Uploading...' : `Upload Files (${verFiles.length} VER, ${horFiles.length} HOR)`}
            </button>
            <button onClick={() => { setFiles([]); setDone(false); setError('') }}
              className="btn-secondary bg-gray-100 text-gray-600 hover:bg-gray-200">Clear</button>
          </div>
        </div>
      )}

      {done && (
        <div className="card border-green-200">
          <h3 className="card-title text-success">Files Uploaded</h3>
          <p className="text-sm text-gray-600 mb-3">{files.length} file(s) saved.</p>
          <div className="space-y-1 mb-3">
            <p className="text-xs text-gray-500">VER files: {verFiles.length} ({verFiles.map(f => f.file.name).join(', ')})</p>
            <p className="text-xs text-gray-500">HOR files: {horFiles.length} ({horFiles.map(f => f.file.name).join(', ')})</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => navigate('/', { state: { autoProcess: true } })} className="btn-primary text-sm">Process & View Results</button>
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
