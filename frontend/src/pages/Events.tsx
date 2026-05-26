import { useEffect, useState } from 'react'
import PlotImage from '../components/PlotImage'
import MetricCard from '../components/MetricCard'
import { vizApi } from '../api/client'

export default function Events() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    vizApi.events().then(setData).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Vehicle Event Detection</h2>
        <p className="text-gray-500 text-sm mt-1">Adaptive peak detection · Axle grouping · Vehicle classification</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="Total Events" value={data?.n_total || 0} color="primary" icon="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        <MetricCard title="Vehicle Types" value={Object.keys(data?.axle_distribution || {}).length} color="secondary" icon="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" subtitle={`${Object.values(data?.axle_distribution || {}).reduce((a: number, b: number) => a + b, 0)} total`} />
        <MetricCard title="Most Common" value={Object.entries(data?.axle_distribution || {}).sort((a: any, b: any) => b[1] - a[1])[0]?.[0] + '-axle' || '—'} color="accent" icon="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </div>

      {data?.plot && <PlotImage src={data.plot} alt="Event distribution" />}

      <div className="card">
        <h3 className="card-title">Detected Events</h3>
        {data?.events?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Vehicle ID</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Gauge</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Axles</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Max Strain</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Duration</th>
                </tr>
              </thead>
              <tbody>
                {data.events.slice(0, 50).map((e: any, i: number) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 px-3 font-medium">{e.vehicle_id}</td>
                    <td className="py-2 px-3">{e.gauge_id}</td>
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
