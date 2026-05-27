import { useEffect, useState } from 'react'
import InteractivePlot from '../components/InteractivePlot'
import { vizApi } from '../api/client'

export default function Temperature() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [offset10, setOffset10] = useState(0)
  const [offset11, setOffset11] = useState(0)

  useEffect(() => {
    vizApi.temperature(offset10, offset11).then(setData).finally(() => setLoading(false))
  }, [offset10, offset11])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div></div>

  const stats = data?.stats || {}

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-primary">Temperature Monitoring</h2>
        <p className="text-gray-500 text-sm mt-1">In-pavement temperature channels · Calibration offset controls</p>
      </div>

      {data?.plot_json && <InteractivePlot plotJson={data.plot_json} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="card-title">CH10 Calibration</h3>
          <div className="mb-4">
            <label className="block text-xs text-gray-500 mb-1">Offset (°C): <span className="font-mono font-bold text-accent">{offset10 >= 0 ? `+${offset10}` : offset10}</span></label>
            <input type="range" min={-50} max={50} value={offset10} onChange={e => setOffset10(Number(e.target.value))}
              className="w-full accent-accent" />
          </div>
          {stats.CH10 && (
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div><span className="text-gray-500">Mean:</span> <span className="font-medium">{stats.CH10.mean} °C</span></div>
              <div><span className="text-gray-500">Min:</span> <span className="font-medium">{stats.CH10.min} °C</span></div>
              <div><span className="text-gray-500">Max:</span> <span className="font-medium">{stats.CH10.max} °C</span></div>
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="card-title">CH11 Calibration</h3>
          <div className="mb-4">
            <label className="block text-xs text-gray-500 mb-1">Offset (°C): <span className="font-mono font-bold text-primary">{offset11 >= 0 ? `+${offset11}` : offset11}</span></label>
            <input type="range" min={-50} max={50} value={offset11} onChange={e => setOffset11(Number(e.target.value))}
              className="w-full accent-primary" />
          </div>
          {stats.CH11 && (
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div><span className="text-gray-500">Mean:</span> <span className="font-medium">{stats.CH11.mean} °C</span></div>
              <div><span className="text-gray-500">Min:</span> <span className="font-medium">{stats.CH11.min} °C</span></div>
              <div><span className="text-gray-500">Max:</span> <span className="font-medium">{stats.CH11.max} °C</span></div>
            </div>
          )}
        </div>
      </div>

      <div className="card bg-blue-50 border-blue-100">
        <h3 className="card-title text-sm text-primary">About Temperature Calibration</h3>
        <p className="text-xs text-gray-600">
          CH10 and CH11 are thermocouple channels embedded in the pavement. Raw readings may require
          a constant offset correction based on field calibration. Adjust the sliders above to apply
          an additive offset and observe the calibrated trace update in real time.
        </p>
      </div>
    </div>
  )
}