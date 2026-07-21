import { useEffect, useState, useCallback } from 'react'
import InteractivePlot from '../components/InteractivePlot'
import { vizApi } from '../api/client'

const GAUGES = ['CH0','CH1','CH2','CH3','CH4','CH5','CH6','CH7','CH8','CH9','CH10','CH11','CH12','CH13','CH14','CH15']

export default function Signals() {
  const [mode, setMode] = useState<'single' | 'all'>('all')
  const [gauge, setGauge] = useState('CH0')
  const [singleData, setSingleData] = useState<any>(null)
  const [allData, setAllData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback((silent = false) => {
    if (!silent) setLoading(true)
    if (mode === 'all') {
      vizApi.signalsAll().then(setAllData).finally(() => { if (!silent) setLoading(false) })
    } else {
      vizApi.signals(gauge).then(setSingleData).finally(() => { if (!silent) setLoading(false) })
    }
  }, [mode, gauge])

  useEffect(() => {
    fetchData()
    const handler = () => { if (!document.hidden) fetchData(true) }
    document.addEventListener('visibilitychange', handler)
    return () => document.removeEventListener('visibilitychange', handler)
  }, [fetchData])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Signal Processing</h2>
        <p className="text-muted-foreground text-sm mt-1">Bandpass filter (0.5–30 Hz) · Baseline correction</p>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 bg-muted rounded-lg p-1">
          <button onClick={() => setMode('all')} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${mode === 'all' ? 'bg-background shadow text-primary font-medium' : 'text-muted-foreground hover:text-muted-foreground'}`}>
            All Gauges
          </button>
          <button onClick={() => setMode('single')} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${mode === 'single' ? 'bg-background shadow text-primary font-medium' : 'text-muted-foreground hover:text-muted-foreground'}`}>
            Single Gauge
          </button>
        </div>
        {mode === 'single' && (
          <select value={gauge} onChange={e => setGauge(e.target.value)} className="input-field w-auto">
            {GAUGES.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
        )}
        {mode === 'all' && allData && (
          <span className="text-xs text-muted-foreground">{allData.n_horizontal} horizontal · {allData.n_vertical} vertical · {allData.n_gauges} total · {allData.total_duration_s?.toFixed(1)}s duration</span>
        )}
      </div>

      {mode === 'all' && (
        <div className="space-y-6">
          {allData?.has_vertical && allData?.plot_json_ver ? (
            <InteractivePlot plotJson={allData.plot_json_ver} title="Vertical Strain Channels" />
          ) : (
            <div className="card text-muted-foreground text-center py-12 border-dashed border-2 border-border">
              <p className="text-sm">No vertical strain data available</p>
              <p className="text-xs mt-1">Upload a VER file to see vertical channels</p>
            </div>
          )}
          {allData?.has_horizontal && allData?.plot_json_hor ? (
            <InteractivePlot plotJson={allData.plot_json_hor} title="Horizontal Strain Channels" />
          ) : (
            <div className="card text-muted-foreground text-center py-12 border-dashed border-2 border-border">
              <p className="text-sm">No horizontal strain data available</p>
              <p className="text-xs mt-1">Upload a HOR file to see horizontal channels</p>
            </div>
          )}
          {(!allData?.has_vertical && !allData?.has_horizontal) && (
            <InteractivePlot plotJson={allData?.plot_json_ver} />
          )}
        </div>
      )}

      {mode === 'single' && singleData && (
        <div className="space-y-4">
          <InteractivePlot plotJson={singleData.plot_json} />
          <div className="card">
            <h3 className="card-title">Signal Statistics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div><span className="text-muted-foreground">Gauge:</span> <span className="font-medium">{singleData.gauge}</span></div>
              <div><span className="text-muted-foreground">Raw mean:</span> <span className="font-medium">{singleData.raw?.reduce((a: number,b: number) => a + Math.abs(b), 0) / (singleData.raw?.length || 1) | 0} µε</span></div>
              <div><span className="text-muted-foreground">Filtered mean:</span> <span className="font-medium">{singleData.filtered?.reduce((a: number,b: number) => a + Math.abs(b), 0) / (singleData.filtered?.length || 1) | 0} µε</span></div>
              <div><span className="text-muted-foreground">Filter:</span> <span className="font-medium">0.5–30 Hz Bandpass</span></div>
            </div>
          </div>
        </div>
      )}

      <div className="card bg-muted border-border">
        <h3 className="card-title text-sm text-primary">About the Filter</h3>
        <p className="text-xs text-muted-foreground">
          The 0.5–30 Hz bandpass filter preserves axle event waveforms (dominant frequency 12–25 Hz at highway speed)
          while removing drift, DC offset, and high-frequency noise.
        </p>
      </div>
    </div>
  )
}