import { useEffect, useState } from 'react'
import InteractivePlot from '../components/InteractivePlot'
import MetricCard from '../components/MetricCard'
import { vizApi } from '../api/client'

export default function StrainViewer() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    vizApi.strains().then(setData).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  const hGauges = (data?.per_gauge || []).filter((g: any) => g.type === 'horizontal_strain')
  const vGauges = (data?.per_gauge || []).filter((g: any) => g.type === 'vertical_strain')

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Strain Viewer</h2>
        <p className="text-gray-500 text-sm mt-1">Per-gauge strain values · Collective εt/εv · Sensor fusion</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="εt (p95)" value={data?.eps_t ? `${data.eps_t} µε` : '—'} subtitle="Horizontal tensile" color="accent" icon="M7 11l5-5m0 0l5 5m-5-5v12" />
        <MetricCard title="εv (p95)" value={data?.eps_v ? `${data.eps_v} µε` : '—'} subtitle="Vertical compressive" color="secondary" icon="M13 5l5 5-5 5M5 5l5 5-5 5" />
        <MetricCard title="Gauges" value={data?.n_gauges || 0} subtitle={`${data?.n_horizontal || 0} hor · ${data?.n_vertical || 0} ver`} color="primary" icon="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        <MetricCard title="Health Weighted" value="Active" subtitle="Sensor fusion enabled" color="success" icon="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {data?.plot_json && <InteractivePlot plotJson={data.plot_json} />}
        {data?.plot_json2 && <InteractivePlot plotJson={data.plot_json2} />}
      </div>

      <div className="card">
        <h3 className="card-title">Per-Gauge Strain & Health</h3>
        {data?.per_gauge?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Gauge</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Type</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Peak Strain (µε)</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Health Score</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.per_gauge.map((g: any, i: number) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 px-3 font-medium">{g.gauge}</td>
                    <td className="py-2 px-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${g.type === 'horizontal_strain' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'}`}>
                        {g.type === 'horizontal_strain' ? 'Horizontal' : 'Vertical'}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono">{g.peak_strain_microstrain}</td>
                    <td className="py-2 px-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-200 rounded-full">
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
          <p className="text-gray-400 text-center py-8">No gauge data available</p>
        )}
      </div>
    </div>
  )
}