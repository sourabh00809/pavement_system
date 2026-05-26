import { useState } from 'react'
import { uploadApi } from '../api/client'

export default function Upload() {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [dragging, setDragging] = useState(false)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const dropped = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.xls') || f.name.endsWith('.xlsx') || f.name.endsWith('.csv'))
    setFiles(prev => [...prev, ...dropped])
  }

  const handleUpload = async () => {
    if (files.length === 0) return
    setUploading(true)
    setResult(null)
    try {
      const results = await Promise.all(files.map(f => uploadApi(f)))
      setResult({ success: true, files: results })
    } catch (err: any) {
      setResult({ success: false, error: err.message })
    }
    setUploading(false)
  }

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
          <input type="file" multiple accept=".xls,.xlsx,.csv" className="hidden" onChange={e => setFiles(prev => [...prev, ...Array.from(e.target.files || [])])} />
        </label>
      </div>

      {files.length > 0 && (
        <div className="card">
          <h3 className="card-title">Selected Files ({files.length})</h3>
          <div className="space-y-2">
            {files.map((f, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-sm">{f.name}</span>
                  <span className="text-xs text-gray-400">{(f.size / 1024).toFixed(1)} KB</span>
                </div>
                <button onClick={() => setFiles(files.filter((_, j) => j !== i))} className="text-danger hover:text-red-700 text-sm">Remove</button>
              </div>
            ))}
          </div>
          <div className="mt-4 flex gap-3">
            <button onClick={handleUpload} disabled={uploading} className="btn-primary">
              {uploading ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
                  Uploading...
                </span>
              ) : 'Upload & Process'}
            </button>
            <button onClick={() => setFiles([])} className="btn-secondary bg-gray-100 text-gray-600 hover:bg-gray-200">Clear All</button>
          </div>
        </div>
      )}

      {result && (
        <div className={`card ${result.success ? 'border-green-200' : 'border-red-200'}`}>
          <h3 className={`card-title ${result.success ? 'text-success' : 'text-danger'}`}>
            {result.success ? 'Upload Successful' : 'Upload Failed'}
          </h3>
          {result.success ? (
            <ul className="text-sm text-gray-600 space-y-1">
              {result.files.map((f: any, i: number) => (
                <li key={i}>{f.filename} — {f.size} bytes</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-danger">{result.error}</p>
          )}
        </div>
      )}

      <div className="card bg-blue-50 border-blue-100">
        <h3 className="card-title text-sm text-primary">Using Demo Data</h3>
        <p className="text-xs text-gray-600">No files? Navigate to other pages — demo data is used automatically for all visualizations and predictions.</p>
      </div>
    </div>
  )
}
