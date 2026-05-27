import { useEffect, useState } from 'react'
import InteractivePlot from '../components/InteractivePlot'
import { vizApi } from '../api/client'

const GAUGES = ['CH0','CH1','CH2','CH3','CH4','CH5','CH6','CH7','CH8','CH9','CH10','CH11','CH12','CH13','CH14','CH15']

export default function Signals() {
  const [mode, setMode] = useState<'single' | 'all'>('all')
  const [gauge, setGauge] = useState('CH0')
  const [singleData, setSingleData] = useState<any>(null)
  const [allData, setAllData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    if (mode === 'all') {
      vizApi.signalsAll().then(setAllData).finally(() => setLoading(false))
    } else {
      vizApi.signals(gauge).then(setSingleData).finally(() => setLoading(false))
    }
  }, [mode, gauge])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Signal Processing</h2>
        <p className="text-gray-500 text-sm mt-1">Bandpass filter (0.5–30 Hz) · Baseline correction</p>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
          <button onClick={() => setMode('all')} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${mode === 'all' ? 'bg-white shadow text-primary font-medium' : 'text-gray-500 hover:text-gray-700'}`}>
            All Gauges
          </button>
          <button onClick={() => setMode('single')} className={`px-3 py-1.5 text-sm rounded-md transition-colors ${mode === 'single' ? 'bg-white shadow text-primary font-medium' : 'text-gray-500 hover:text-gray-700'}`}>
            Single Gauge
          </button>
        </div>
        {mode === 'single' && (
          <select value={gauge} onChange={e => setGauge(e.target.value)} className="input-field w-auto">
            {GAUGES.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
        )}
        {mode === 'all' && allData && (
          <span className="text-xs text-gray-400">{allData.n_horizontal} horizontal · {allData.n_vertical} vertical · {allData.n_gauges} total</span>
        )}
      </div>

      {mode === 'all' && allData?.plot_json && (
        <InteractivePlot plotJson={allData.plot_json} />
      )}

      {mode === 'single' && singleData && (
        <div className="space-y-4">
          <InteractivePlot plotJson={singleData.plot_json} />
          <div className="card">
            <h3 className="card-title">Signal Statistics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div><span className="text-gray-500">Gauge:</span> <span className="font-medium">{singleData.gauge}</span></div>
              <div><span className="text-gray-500">Raw mean:</span> <span className="font-medium">{singleData.raw?.reduce((a: number,b: number) => a + Math.abs(b), 0) / (singleData.raw?.length || 1) | 0} µε</span></div>
              <div><span className="text-gray-500">Filtered mean:</span> <span className="font-medium">{singleData.filtered?.reduce((a: number,b: number) => a + Math.abs(b), 0) / (singleData.filtered?.length || 1) | 0} µε</span></div>
              <div><span className="text-gray-500">Filter:</span> <span className="font-medium">0.5–30 Hz Bandpass</span></div>
            </div>
          </div>
        </div>
      )}

      <div className="card bg-blue-50 border-blue-100">
        <h3 className="card-title text-sm text-primary">About the Filter</h3>
        <p className="text-xs text-gray-600">
          The 0.5–30 Hz bandpass filter preserves axle event waveforms (dominant frequency 12–25 Hz at highway speed)
          while removing drift, DC offset, and high-frequency noise.
        </p>
      </div>
    </div>
  )
}