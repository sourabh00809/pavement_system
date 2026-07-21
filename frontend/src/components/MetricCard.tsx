export default function MetricCard({ title, value, subtitle, color = 'primary', icon, trend }: {
  title: string
  value: string | number
  subtitle?: string
  color?: 'primary' | 'secondary' | 'accent' | 'success' | 'danger' | 'warning'
  icon?: string
  trend?: { up: boolean; text: string }
}) {
  const colorMap = { primary: 'text-primary', secondary: 'text-secondary', accent: 'text-accent', success: 'text-success', danger: 'text-danger', warning: 'text-warning' }
  const bgMap = { primary: 'bg-blue-50', secondary: 'bg-blue-50', accent: 'bg-yellow-50', success: 'bg-green-50', danger: 'bg-red-50', warning: 'bg-yellow-50' }

  return (
    <div className="card flex items-start gap-4">
      {icon && (
        <div className={`${bgMap[color]} p-3 rounded-lg`}>
          <svg className={`w-6 h-6 ${colorMap[color]}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={icon} />
          </svg>
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-muted-foreground truncate">{title}</p>
        <p className={`metric-value ${colorMap[color]}`}>{value}</p>
        {subtitle && <p className="metric-label">{subtitle}</p>}
        {trend && (
          <p className={`text-xs mt-1 ${trend.up ? 'text-success' : 'text-danger'}`}>
            {trend.up ? '↑' : '↓'} {trend.text}
          </p>
        )}
      </div>
    </div>
  )
}
