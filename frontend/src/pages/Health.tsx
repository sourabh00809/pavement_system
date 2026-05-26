import { useEffect, useState } from 'react'
import InteractivePlot from '../components/InteractivePlot'
import { vizApi } from '../api/client'

export default function Health() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    vizApi.health().then(setData).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Sensor Health Monitor</h2>
        <p className="text-gray-500 text-sm mt-1">Dead/saturated gauge detection · Autoencoder anomaly detector</p>
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
              <div className={`h-1.5 rounded-full ${g.excluded ? 'bg-danger' : g.health_score > 0.7 ? 'bg-success' : 'bg-warning'}`}
                style={{ width: `${g.health_score * 100}%` }}></div>
            </div>
            <div className="mt-2 text-xs text-gray-500 space-y-0.5">
              <p>σ = {g.std_dev.toFixed(2)} µε</p>
              <p>μ = {g.mean_offset.toFixed(2)} µε</p>
            </div>
            {g.flags?.length > 0 && (
              <div className="mt-2 space-y-1">
                {g.flags.map((f: string, i: number) => (
                  <p key={i} className="text-xs text-danger">{f}</p>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
