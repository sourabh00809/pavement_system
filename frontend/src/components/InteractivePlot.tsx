import Plot from 'react-plotly.js'

export default function InteractivePlot({ plotJson, title }: { plotJson?: string; title?: string }) {
  if (!plotJson) return null

  let figure: any
  try {
    figure = JSON.parse(plotJson)
  } catch {
    return <div className="card text-muted-foreground text-center py-8">Failed to load plot</div>
  }

  return (
    <div className="card overflow-hidden">
      {title && <h3 className="card-title">{title}</h3>}
      <Plot
        data={figure.data || []}
        layout={{
          ...(figure.layout || {}),
          autosize: true,
          margin: { l: 50, r: 20, t: 40, b: 50 },
        }}
        config={{
          responsive: true,
          displayModeBar: true,
          modeBarButtonsToRemove: ['lasso2d', 'select2d'],
          displaylogo: false,
        }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </div>
  )
}
