import { useEffect, useState } from 'react'
import InteractivePlot from '../components/InteractivePlot'
import MetricCard from '../components/MetricCard'
import { vizApi, exportApi } from '../api/client'

interface GaugeRow {
  gauge: string
  group: string
  peak_strain_microstrain: number
  n_vehicles: number
  vehicle_ids: number[]
  health_score: number
  excluded: boolean
}

export default function StrainViewer() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [signalVer, setSignalVer] = useState<any>(null)
  const [signalHor, setSignalHor] = useState<any>(null)
  const [selVer, setSelVer] = useState('')
  const [selHor, setSelHor] = useState('')

  useEffect(() => {
    vizApi.strains().then(setData).catch(() => setData(null)).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (selVer) vizApi.signals(selVer, 'VER').then(setSignalVer).catch(() => setSignalVer(null))
  }, [selVer])
  useEffect(() => {
    if (selHor) vizApi.signals(selHor, 'HOR').then(setSignalHor).catch(() => setSignalHor(null))
  }, [selHor])

  const handleExport = () => {
    exportApi.results().then(res => {
      const url = window.URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url; a.download = 'results.xlsx'; a.click()
      window.URL.revokeObjectURL(url)
    })
  }

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  const allGauges: GaugeRow[] = data?.per_gauge || []
  const verGauges = allGauges.filter(g => g.group === 'VER')
  const horGauges = allGauges.filter(g => g.group === 'HOR')
  const hasData = allGauges.length > 0

  function GaugeTable({ gauges, title }: { gauges: GaugeRow[]; title: string }) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="card-title mb-0">{title} ({gauges.length} gauges)</h3>
        </div>
        {gauges.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Gauge</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Peak Strain (µε)</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Vehicles</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Vehicle IDs</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Health</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {gauges.map((g, i) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 px-3 font-medium">{g.gauge}</td>
                    <td className="py-2 px-3 font-mono">{g.peak_strain_microstrain.toFixed(1)}</td>
                    <td className="py-2 px-3 font-mono">{g.n_vehicles}</td>
                    <td className="py-2 px-3 text-xs text-gray-500 max-w-[200px] truncate">{g.vehicle_ids?.join(', ') || '—'}</td>
                    <td className="py-2 px-3">
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1.5 bg-gray-200 rounded-full">
                          <div className={`h-full rounded-full ${g.health_score > 0.7 ? 'bg-green-500' : g.health_score > 0.3 ? 'bg-amber-500' : 'bg-red-500'}`}
                            style={{ width: `${g.health_score * 100}%` }} />
                        </div>
                        <span className="text-xs">{g.health_score.toFixed(2)}</span>
                      </div>
                    </td>
                    <td className="py-2 px-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${g.excluded ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                        {g.excluded ? 'Excluded' : 'Active'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-400 text-center py-8 text-sm">No gauge data available</p>
        )}
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-primary">Signal Viewer</h2>
          <p className="text-gray-500 text-sm mt-1">Per-gauge strain values · Separate VER & HOR analysis</p>
        </div>
        {hasData && (
          <button onClick={handleExport} className="btn-primary text-sm flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-2m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Export as Excel
          </button>
        )}
      </div>

      {!hasData && (
        <div className="card text-gray-400 text-center py-12 border-dashed border-2 border-gray-200">
          <p className="text-sm">No data available</p>
          <p className="text-xs mt-1">Upload and process files from the Dashboard first</p>
        </div>
      )}

      {hasData && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricCard title="Total Gauges" value={allGauges.length} subtitle={`${verGauges.length} VER · ${horGauges.length} HOR`} color="primary" />
            <MetricCard title="VER Peak (max)" value={verGauges.length > 0 ? `${Math.max(...verGauges.map(g => g.peak_strain_microstrain)).toFixed(1)} µε` : '—'} subtitle="Vertical strain" color="secondary" />
            <MetricCard title="HOR Peak (max)" value={horGauges.length > 0 ? `${Math.max(...horGauges.map(g => g.peak_strain_microstrain)).toFixed(1)} µε` : '—'} subtitle="Horizontal strain" color="accent" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {data?.plot_json_ver && <InteractivePlot plotJson={data.plot_json_ver} title="VER — Peak Strain" />}
            {data?.plot_json_hor && <InteractivePlot plotJson={data.plot_json_hor} title="HOR — Peak Strain" />}
          </div>

          <div className="space-y-6">
            {verGauges.length > 0 && <GaugeTable gauges={verGauges} title="Vertical Strain Gauges (VER)" />}
            {horGauges.length > 0 && <GaugeTable gauges={horGauges} title="Horizontal Strain Gauges (HOR)" />}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {verGauges.length > 0 && (
              <div className="card">
                <div className="flex items-center gap-3 mb-3">
                  <h3 className="card-title mb-0">VER Signal</h3>
                  <select value={selVer} onChange={e => setSelVer(e.target.value)}
                    className="text-xs border border-gray-200 rounded px-2 py-1 ml-auto">
                    <option value="">Select gauge...</option>
                    {verGauges.map(g => <option key={g.gauge} value={g.gauge}>{g.gauge}</option>)}
                  </select>
                </div>
                {signalVer?.plot_json ? <InteractivePlot plotJson={signalVer.plot_json} title="" />
                  : <p className="text-gray-400 text-center py-8 text-sm">Select a gauge to view signal</p>}
              </div>
            )}
            {horGauges.length > 0 && (
              <div className="card">
                <div className="flex items-center gap-3 mb-3">
                  <h3 className="card-title mb-0">HOR Signal</h3>
                  <select value={selHor} onChange={e => setSelHor(e.target.value)}
                    className="text-xs border border-gray-200 rounded px-2 py-1 ml-auto">
                    <option value="">Select gauge...</option>
                    {horGauges.map(g => <option key={g.gauge} value={g.gauge}>{g.gauge}</option>)}
                  </select>
                </div>
                {signalHor?.plot_json ? <InteractivePlot plotJson={signalHor.plot_json} title="" />
                  : <p className="text-gray-400 text-center py-8 text-sm">Select a gauge to view signal</p>}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
