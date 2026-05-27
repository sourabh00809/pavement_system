import { useEffect, useState } from 'react'
import MetricCard from '../components/MetricCard'
import InteractivePlot from '../components/InteractivePlot'
import { vizApi } from '../api/client'

export default function Dashboard() {
  const [life, setLife] = useState<any>(null)
  const [health, setHealth] = useState<any>(null)
  const [events, setEvents] = useState<any>(null)
  const [strains, setStrains] = useState<any>(null)
  const [sync, setSync] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      vizApi.life(),
      vizApi.health(),
      vizApi.events(),
      vizApi.strains(),
      vizApi.sync(),
    ]).then(([l, h, e, s, sy]) => {
      setLife(l); setHealth(h); setEvents(e); setStrains(s); setSync(sy)
    }).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  const axleDist = (events?.axle_distribution || {}) as Record<string, number>
  const totalEvents = Object.values(axleDist).reduce((a: number, b: number) => a + b, 0)
  const healthSummary = health?.summary || {}

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Dashboard</h2>
        <p className="text-gray-500 text-sm mt-1">NH-71 Instrumented Pavement · IIT Tirupati</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Fatigue Life (Nf)" value={life?.life?.Nf ? parseFloat(life.life.Nf).toExponential(2) : '—'} subtitle="IRC:37-2018" color="primary" icon="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        <MetricCard title="Rutting Life (Nr)" value={life?.life?.Nr ? parseFloat(life.life.Nr).toExponential(2) : '—'} subtitle="Shell model" color="accent" icon="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        <MetricCard title="Design Traffic (Nd)" value={life?.life?.Nd ? parseFloat(life.life.Nd).toExponential(2) : '—'} subtitle="Cumulative std axles" color="secondary" icon="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        <MetricCard title="Status" value={life?.life?.design_adequate ? 'Adequate' : 'Inadequate'} subtitle={life?.life?.governing_failure || '—'} color={life?.life?.design_adequate ? 'success' : 'danger'} icon="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="εt (p95)" value={strains?.eps_t ? `${strains.eps_t} µε` : '—'} subtitle="Horizontal tensile" color="accent" icon="M7 11l5-5m0 0l5 5m-5-5v12" />
        <MetricCard title="εv (p95)" value={strains?.eps_v ? `${strains.eps_v} µε` : '—'} subtitle="Vertical compressive" color="secondary" icon="M13 5l5 5-5 5M5 5l5 5-5 5" />
        <MetricCard title="Vehicle Events" value={totalEvents} subtitle={`${events?.n_total || 0} detections`} color="primary" icon="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        <MetricCard title="Synced Bundles" value={sync?.n_bundles || 0} subtitle={`${sync?.bundles?.length || 0} matched`} color="warning" icon="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="Healthy Gauges" value={healthSummary.healthy || '—'} subtitle={`of ${healthSummary.total || '—'} total`} color="success" icon="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        <MetricCard title="Warning Gauges" value={healthSummary.warning || 0} subtitle="Score 0.3–0.7" color="warning" icon="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
        <MetricCard title="Excluded Gauges" value={healthSummary.excluded || 0} subtitle="Score < 0.3" color="danger" icon="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <InteractivePlot plotJson={life?.plot_json} title="Pavement Life" />
        <InteractivePlot plotJson={health?.plot_json} title="Gauge Health Scores" />
      </div>

      <div className="card">
        <h3 className="card-title">Quick Actions</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <a href="/upload" className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 text-primary hover:bg-blue-100 transition-colors">
            <svg className="w-5 h-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
            <span className="text-sm font-medium">Upload Data</span>
          </a>
          <a href="/signals" className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 text-primary hover:bg-blue-100 transition-colors">
            <svg className="w-5 h-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
            <span className="text-sm font-medium">View Signals</span>
          </a>
          <a href="/design" className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 text-primary hover:bg-blue-100 transition-colors">
            <svg className="w-5 h-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
            <span className="text-sm font-medium">Pavement Design</span>
          </a>
          <a href="/docs" className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 text-primary hover:bg-blue-100 transition-colors">
            <svg className="w-5 h-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
            <span className="text-sm font-medium">Documentation</span>
          </a>
        </div>
      </div>
    </div>
  )
}