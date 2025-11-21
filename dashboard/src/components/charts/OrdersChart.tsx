import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface OrdersChartProps {
  data: Array<{
    date: string
    orders: number
    purchases: number
    cancellations: number
    returns: number
  }>
}

export const OrdersChart = ({ data }: OrdersChartProps) => {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Динамика заказов
      </h3>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={data}>
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
          />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="circle"
          />
          <Bar dataKey="orders" fill="#0ea5e9" name="Заказы" radius={[4, 4, 0, 0]} />
          <Bar dataKey="purchases" fill="#10b981" name="Выкупы" radius={[4, 4, 0, 0]} />
          <Bar dataKey="cancellations" fill="#f59e0b" name="Отмены" radius={[4, 4, 0, 0]} />
          <Bar dataKey="returns" fill="#ef4444" name="Возвраты" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
