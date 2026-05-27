import { useEffect, useState } from 'react'
import InteractivePlot from '../components/InteractivePlot'
import MetricCard from '../components/MetricCard'
import { vizApi } from '../api/client'

export default function Health() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    vizApi.health().then(setData).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  if (error || data?.error) {
    return (
      <div className="max-w-5xl mx-auto space-y-6">
        <div><h2 className="text-2xl font-bold text-primary">Sensor Health Monitor</h2></div>
        <div className="card border border-red-200 bg-red-50">
          <p className="text-sm text-danger">{error || data?.error}</p>
        </div>
      </div>
    )
  }

  const summary = data?.summary || {}

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Sensor Health Monitor</h2>
        <p className="text-gray-500 text-sm mt-1">Dead/saturated gauge detection · Health score 0–1</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="Healthy" value={summary.healthy || 0} subtitle={`of ${summary.total || 0} gauges`} color="success" icon="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        <MetricCard title="Warning" value={summary.warning || 0} subtitle="Score 0.3–0.7" color="warning" icon="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
        <MetricCard title="Excluded" value={summary.excluded || 0} subtitle="Score < 0.3" color="danger" icon="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </div>

      {data?.plot_json && <InteractivePlot plotJson={data.plot_json} />}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data?.gauges?.map((g: any) => (
          <div key={g.gauge} className={`card ${g.excluded ? 'border-red-200 bg-red-50' : g.health_score > 0.7 ? 'border-green-200' : 'border-yellow-200'}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-sm">{g.gauge}</span>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                g.excluded ? 'bg-red-100 text-red-700' : g.health_score > 0.7 ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
              }`}>
                {g.excluded ? 'Excluded' : g.health_score > 0.7 ? 'Healthy' : 'Warning'}
              </span>
            </div>
            <div className="flex items-baseline gap-1 mb-2">
              <span className="text-2xl font-bold text-primary">{(g.health_score * 100).toFixed(0)}</span>
              <span className="text-sm text-gray-400">/100</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-1.5">
              <div className={`h-1.5 rounded-full ${g.excluded ? 'bg-red-500' : g.health_score > 0.7 ? 'bg-green-500' : 'bg-amber-500'}`}
                style={{ width: `${g.health_score * 100}%` }}></div>
            </div>
            <div className="mt-2 text-xs text-gray-500 space-y-0.5">
              <p>σ = {g.std_dev.toFixed(2)} µε</p>
              <p>μ = {g.mean_offset.toFixed(2)} µε</p>
            </div>
            {g.flags?.length > 0 && (
              <div className="mt-2 space-y-1">
                {g.flags.map((f: string, i: number) => (
                  <p key={i} className="text-xs text-red-600">{f}</p>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}