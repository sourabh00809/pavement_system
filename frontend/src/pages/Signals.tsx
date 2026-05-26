import { useEffect, useState } from 'react'
import PlotImage from '../components/PlotImage'
import { vizApi } from '../api/client'

export default function Signals() {
  const [data, setData] = useState<any>(null)
  const [gauge, setGauge] = useState('CH0')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    vizApi.signals(gauge).then(setData).finally(() => setLoading(false))
  }, [gauge])

  const gauges = ['CH0','CH1','CH2','CH3','CH4','CH5','CH6','CH7','CH8','CH9','CH10','CH11','CH12','CH13','CH14','CH15']

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Signal Processing</h2>
        <p className="text-gray-500 text-sm mt-1">Bandpass filter (0.5–30 Hz) · Baseline correction</p>
      </div>

      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-600">Gauge:</label>
        <select value={gauge} onChange={e => setGauge(e.target.value)} className="input-field w-auto">
          {gauges.map(g => <option key={g} value={g}>{g}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>
      ) : data ? (
        <div className="space-y-4">
          <PlotImage src={data.plot} alt={`Signal ${gauge}`} />
          <div className="card">
            <h3 className="card-title">Signal Statistics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div><span className="text-gray-500">Gauge:</span> <span className="font-medium">{data.gauge}</span></div>
              <div><span className="text-gray-500">Raw mean:</span> <span className="font-medium">{data.raw?.reduce((a: number,b: number) => a + Math.abs(b), 0) / (data.raw?.length || 1) | 0} µε</span></div>
              <div><span className="text-gray-500">Filtered mean:</span> <span className="font-medium">{data.filtered?.reduce((a: number,b: number) => a + Math.abs(b), 0) / (data.filtered?.length || 1) | 0} µε</span></div>
              <div><span className="text-gray-500">Filter:</span> <span className="font-medium">0.5–30 Hz Bandpass</span></div>
            </div>
          </div>
        </div>
      ) : (
        <div className="card text-center text-gray-400 py-12">Failed to load signal data</div>
      )}

      <div className="card bg-blue-50 border-blue-100">
        <h3 className="card-title text-sm text-primary">About the Filter</h3>
        <p className="text-xs text-gray-600">
          The 0.5–30 Hz bandpass filter is a critical fix from the mid-term pipeline. The previous 0.1 Hz cutoff incorrectly removed vehicle signals (dominant frequency 12–25 Hz at highway speed). The corrected filter preserves axle event waveforms while removing drift, DC offset, and high-frequency noise.
        </p>
      </div>
    </div>
  )
}
