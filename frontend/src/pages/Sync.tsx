import { useEffect, useState } from 'react'
import InteractivePlot from '../components/InteractivePlot'
import MetricCard from '../components/MetricCard'
import { vizApi } from '../api/client'

export default function Sync() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    vizApi.sync().then(setData).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Multi-Gauge Synchronization</h2>
        <p className="text-muted-foreground text-sm mt-1">Cross-correlation · DTW alignment · DBSCAN temporal clustering</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="Synced Bundles" value={data?.n_bundles || 0} color="primary" icon="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        <MetricCard title="Gauges Tracked" value={data?.gauges?.length || 0} color="secondary" icon="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        <MetricCard title="Avg Confidence" value={data?.bundles?.length ? (data.bundles.reduce((a: number, b: any) => a + b.confidence, 0) / data.bundles.length).toFixed(3) : '—'} color="accent" icon="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </div>

      {data?.plot_json && <InteractivePlot plotJson={data.plot_json} />}

      <div className="card">
        <h3 className="card-title">Synchronized Event Bundles</h3>
        {data?.bundles?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 px-3 text-muted-foreground font-medium">Bundle ID</th>
                  <th className="text-left py-2 px-3 text-muted-foreground font-medium">Time (s)</th>
                  <th className="text-left py-2 px-3 text-muted-foreground font-medium">Axles</th>
                  <th className="text-left py-2 px-3 text-muted-foreground font-medium">Gauges</th>
                  <th className="text-left py-2 px-3 text-muted-foreground font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {data.bundles.slice(0, 20).map((b: any, i: number) => (
                  <tr key={i} className="border-b border-border hover:bg-muted">
                    <td className="py-2 px-3 font-medium">{b.bundle_id}</td>
                    <td className="py-2 px-3">{b.representative_time?.toFixed(2)}</td>
                    <td className="py-2 px-3">{b.axle_count}</td>
                    <td className="py-2 px-3">{b.n_gauges_matched}</td>
                    <td className="py-2 px-3">
                      <span className={`badge ${b.confidence > 0.7 ? 'badge-ok' : b.confidence > 0.4 ? 'badge-warn' : 'badge-err'}`}>
                        {b.confidence.toFixed(3)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-muted-foreground text-center py-8">No synchronized bundles found</p>
        )}
      </div>
    </div>
  )
}
