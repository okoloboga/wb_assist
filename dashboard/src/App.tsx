import { useState } from 'react'
import { ShoppingCart, CheckCircle, XCircle, RotateCcw } from 'lucide-react'
import { Header } from './components/layout/Header'
import { Container } from './components/layout/Container'
import { TimePeriodSelector } from './components/common/TimePeriodSelector'
import { MetricCard } from './components/charts/MetricCard'
import { MetricsCharts } from './components/charts/MetricsCharts'
import { WarehouseTable } from './components/warehouse/WarehouseTable'
import { mockChartDataByPeriod, mockWarehouseData, mockMetrics } from './utils/mockData'

type TimePeriod = '1month' | '2months' | '3months' | '6months'

function App() {
  const [period, setPeriod] = useState<TimePeriod>('1month')
  const chartData = mockChartDataByPeriod[period]

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <Container>
        {/* Time Period Selector */}
        <TimePeriodSelector value={period} onChange={setPeriod} />

        {/* Orders Section */}
        <section className="mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-6">
            Метрики заказов
          </h2>

          {/* Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <MetricCard
              title="Заказы"
              value={mockMetrics.orders}
              icon={ShoppingCart}
              color="bg-blue-500"
            />
            <MetricCard
              title="Выкупы"
              value={mockMetrics.purchases}
              icon={CheckCircle}
              color="bg-green-500"
            />
            <MetricCard
              title="Отмены"
              value={mockMetrics.cancellations}
              icon={XCircle}
              color="bg-amber-500"
            />
            <MetricCard
              title="Возвраты"
              value={mockMetrics.returns}
              icon={RotateCcw}
              color="bg-red-500"
            />
          </div>

          {/* Charts */}
          <MetricsCharts data={chartData} />
        </section>

        {/* Warehouse Section */}
        <section>
          <WarehouseTable data={mockWarehouseData} />
        </section>
      </Container>
    </div>
  )
}

export default App
