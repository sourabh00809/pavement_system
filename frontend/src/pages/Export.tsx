import { useState } from 'react'
import { exportApi } from '../api/client'

export default function ExportPage() {
  const [downloading, setDownloading] = useState<string | null>(null)

  const download = async (type: string, apiFn: () => Promise<any>, filename: string) => {
    setDownloading(type)
    try {
      const res = await apiFn()
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      alert('Download failed — is the backend running?')
    }
    setDownloading(null)
  }

  const items = [
    { type: 'events', label: 'Vehicle Events (CSV)', desc: 'All detected events with axle counts, strains, durations', api: () => exportApi.events(), file: 'vehicle_events.csv', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
    { type: 'summary', label: 'Life Prediction Summary (JSON)', desc: 'Nf, Nr, Nd, uncertainty intervals, design adequacy', api: async () => {
      const data = await exportApi.summary()
      return { data: JSON.stringify(data, null, 2) }
    }, file: 'life_prediction_summary.json', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },

  ]

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Export & Report</h2>
        <p className="text-gray-500 text-sm mt-1">Download pipeline results and configuration</p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {items.map(item => (
          <div key={item.type} className="card flex items-center justify-between">
            <div className="flex items-start gap-3">
              <svg className="w-8 h-8 text-secondary flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={item.icon} />
              </svg>
              <div>
                <h3 className="font-medium text-sm">{item.label}</h3>
                <p className="text-xs text-gray-400 mt-0.5">{item.desc}</p>
              </div>
            </div>
            <button
              onClick={() => {
                const blobPromise = item.type === 'summary'
                  ? item.api().then((r: any) => new Blob([r.data]))
                  : item.api().then((r: any) => new Blob([r.data]))
                download(item.type, () => item.api(), item.file)
              }}
              disabled={downloading === item.type}
              className="btn-secondary text-sm py-2 px-4 whitespace-nowrap"
            >
              {downloading === item.type ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin w-3 h-3 border-2 border-white border-t-transparent rounded-full"></span>
                  Downloading...
                </span>
              ) : 'Download'}
            </button>
          </div>
        ))}
      </div>

      <div className="card bg-blue-50 border-blue-100">
        <h3 className="card-title text-sm text-primary">Pipeline Status</h3>
        <button onClick={async () => {
          try {
            const { pipelineApi, vizApi } = await import('../api/client')
            const res = await pipelineApi.run([])
            await vizApi.refresh()
            alert(`Pipeline refreshed!\nNf: ${res.life_result?.Nf}\nNr: ${res.life_result?.Nr}\nEvents: ${res.n_events}`)
          } catch (e: any) {
            alert(`Pipeline error: ${e.message}`)
          }
        }} className="btn-primary text-sm" disabled={downloading === 'pipeline'}>
          Refresh Pipeline Data
        </button>
      </div>
    </div>
  )
}
