import { useEffect, useState } from 'react'
import InteractivePlot from '../components/InteractivePlot'
import MetricCard from '../components/MetricCard'
import { vizApi, exportApi } from '../api/client'

export default function Events() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'all' | 'VER' | 'HOR'>('all')

  useEffect(() => {
    vizApi.events().then(setData).finally(() => setLoading(false))
  }, [])

  const axleDist = (data?.axle_distribution || {}) as Record<string, number>
  const totalEvents = data?.n_total || 0
  const eventsVer = data?.events_ver || []
  const eventsHor = data?.events_hor || []

  const handleExport = () => {
    exportApi.results().then(blob => {
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = 'results.xlsx'; a.click()
      window.URL.revokeObjectURL(url)
    })
  }

  const visibleEvents = activeTab === 'all' ? (data?.events || []) :
    activeTab === 'VER' ? eventsVer : eventsHor

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-primary">Vehicle Event Detection</h2>
          <p className="text-gray-500 text-sm mt-1">Separate processing for VER and HOR strain types</p>
        </div>
        {totalEvents > 0 && (
          <button onClick={handleExport} className="btn-primary text-sm flex items-center gap-2">
            Export Excel
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="Total Events" value={totalEvents} color="primary" />
        <MetricCard title="VER Events" value={eventsVer.length} color="secondary" />
        <MetricCard title="HOR Events" value={eventsHor.length} color="accent" />
        <MetricCard title="Vehicle Types" value={Object.keys(axleDist).length} subtitle={`${Object.values(axleDist).reduce((a: number, b: number) => a + b, 0)} total`} color="warning" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {data?.plot_json && <InteractivePlot plotJson={data.plot_json} />}
        {data?.plot_json2 && <InteractivePlot plotJson={data.plot_json2} />}
      </div>

      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <h3 className="card-title mb-0">Detected Events</h3>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
            {(['all', 'VER', 'HOR'] as const).map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)}
                className={`px-3 py-1 text-xs rounded-md transition-colors ${activeTab === tab ? 'bg-white shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700'}`}>
                {tab === 'all' ? 'All' : tab}
              </button>
            ))}
          </div>
        </div>
        {visibleEvents.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Vehicle ID</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Gauge</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Group</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Axles</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Max Strain</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Duration</th>
                </tr>
              </thead>
              <tbody>
                {visibleEvents.slice(0, 100).map((e: any, i: number) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 px-3 font-medium">{e.vehicle_id}</td>
                    <td className="py-2 px-3">{e.gauge_id}</td>
                    <td className="py-2 px-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${e.group === 'VER' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                        {e.group || '—'}
                      </span>
                    </td>
                    <td className="py-2 px-3">{e.axle_count}</td>
                    <td className="py-2 px-3">{e.max_strain.toFixed(1)} µε</td>
                    <td className="py-2 px-3">{e.duration_s.toFixed(3)} s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-400 text-center py-8">No events detected</p>
        )}
      </div>
    </div>
  )
}
