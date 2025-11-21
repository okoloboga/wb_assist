import { useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Eye, EyeOff } from 'lucide-react'

interface ChartDataPoint {
  date: string
  orders: number
  purchases: number
  cancellations: number
  returns: number
}

interface MetricsChartsProps {
  data: ChartDataPoint[]
}

type MetricKey = 'orders' | 'purchases' | 'cancellations' | 'returns'

interface MetricConfig {
  key: MetricKey
  label: string
  color: string
}

const metrics: MetricConfig[] = [
  { key: 'orders', label: 'Заказы', color: '#0ea5e9' },
  { key: 'purchases', label: 'Выкупы', color: '#10b981' },
  { key: 'cancellations', label: 'Отмены', color: '#f59e0b' },
  { key: 'returns', label: 'Возвраты', color: '#ef4444' },
]

export const MetricsCharts = ({ data }: MetricsChartsProps) => {
  const [visibleMetrics, setVisibleMetrics] = useState<Set<MetricKey>>(
    new Set(['orders', 'purchases', 'cancellations', 'returns'])
  )

  const toggleMetric = (key: MetricKey) => {
    setVisibleMetrics((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(key)) {
        newSet.delete(key)
      } else {
        newSet.add(key)
      }
      return newSet
    })
  }

  return (
    <div className="space-y-6">
      {/* Toggle Buttons */}
      <div className="flex flex-wrap gap-3">
        {metrics.map(({ key, label, color }) => {
          const isVisible = visibleMetrics.has(key)
          return (
            <button
              key={key}
              onClick={() => toggleMetric(key)}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all
                ${
                  isVisible
                    ? 'bg-white text-gray-700 shadow-sm border-2'
                    : 'bg-gray-100 text-gray-400 border-2 border-transparent'
                }
              `}
              style={{
                borderColor: isVisible ? color : 'transparent',
              }}
            >
              {isVisible ? <Eye size={18} /> : <EyeOff size={18} />}
              <span>{label}</span>
            </button>
          )
        })}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {metrics.map(({ key, label, color }) => {
          if (!visibleMetrics.has(key)) return null

          return (
            <div
              key={key}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-4">{label}</h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#6b7280', fontSize: 12 }}
                    tickLine={{ stroke: '#e5e7eb' }}
                  />
                  <YAxis
                    tick={{ fill: '#6b7280', fontSize: 12 }}
                    tickLine={{ stroke: '#e5e7eb' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                    }}
                    formatter={(value: number) => [value.toLocaleString('ru-RU'), label]}
                  />
                  <Line
                    type="monotone"
                    dataKey={key}
                    stroke={color}
                    strokeWidth={2}
                    dot={{ fill: color, r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )
        })}
      </div>

      {/* Empty State */}
      {visibleMetrics.size === 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <EyeOff size={48} className="mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500 text-lg">
            Выберите хотя бы одну метрику для отображения
          </p>
        </div>
      )}
    </div>
  )
}
