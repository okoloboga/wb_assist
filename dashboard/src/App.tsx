import { useState, useMemo } from 'react'
import { ShoppingCart, CheckCircle, XCircle, RotateCcw } from 'lucide-react'
import { Header } from './components/layout/Header'
import { Container } from './components/layout/Container'
import { TimePeriodSelector } from './components/common/TimePeriodSelector'
import { MetricCard } from './components/charts/MetricCard'
import { MetricsCharts } from './components/charts/MetricsCharts'
import { WarehouseTable } from './components/warehouse/WarehouseTable'
import { useAnalyticsSummary, useStocks, useAnalyticsDailyTrends } from './api/hooks'

type TimePeriod = '30days' | '60days' | '90days' | '180days'

function App() {
  const [period, setPeriod] = useState<TimePeriod>('30days')

  // Преобразуем период в формат API
  const periodMap: Record<TimePeriod, string> = {
    '30days': '30d',
    '60days': '60d',
    '90days': '90d',
    '180days': '180d',
  }
  const apiPeriod = periodMap[period]

  // Получаем данные из API
  const { data: summaryData, isLoading: summaryLoading } = useAnalyticsSummary(apiPeriod)
  const { data: dailyTrendsData, isLoading: trendsLoading } = useAnalyticsDailyTrends(apiPeriod)
  const { data: stocksData, isLoading: stocksLoading } = useStocks({ limit: 100 })

  // Преобразуем данные складов в формат компонента
  const warehouseData = useMemo(() => {
    if (!stocksData?.stocks?.products) return []
    
    const result: any[] = []
    
    // Разворачиваем вложенную структуру products -> warehouses -> sizes
    stocksData.stocks.products.forEach((product: any) => {
      Object.entries(product.warehouses || {}).forEach(([warehouseName, warehouseData]: [string, any]) => {
        Object.entries(warehouseData.sizes || {}).forEach(([size, quantity]: [string, any]) => {
          result.push({
            id: `${product.nm_id}-${warehouseName}-${size}`,
            nomenclature: product.name || `Товар ${product.nm_id}`,
            size: size,
            warehouse: warehouseName,
            quantity: quantity,
          })
        })
      })
    })
    
    return result
  }, [stocksData])

  // Преобразуем данные графика из реального API
  const chartData = useMemo(() => {
    if (!dailyTrendsData?.time_series) {
      return []
    }
    
    return dailyTrendsData.time_series.map((day: any) => ({
      date: new Date(day.date).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }),
      orders: day.orders || 0,
      purchases: day.buyouts || 0,  // В API это называется buyouts (выкупы)
      cancellations: day.cancellations || 0,
      returns: day.returns || 0,
    }))
  }, [dailyTrendsData])

  const isLoading = summaryLoading || trendsLoading || stocksLoading

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <Container>
        {/* Time Period Selector */}
        <TimePeriodSelector value={period} onChange={setPeriod} />

        {/* Orders Section */}
        <section className="mb-6 sm:mb-8">
          <h2 className="text-xl sm:text-2xl font-semibold text-gray-900 mb-4 sm:mb-6">
            Метрики заказов
          </h2>

          {/* Metric Cards */}
          {isLoading ? (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="bg-white p-4 sm:p-6 rounded-lg shadow-sm border animate-pulse">
                  <div className="h-4 bg-gray-200 rounded mb-2"></div>
                  <div className="h-8 bg-gray-200 rounded"></div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
              <MetricCard
                title="Заказы"
                value={summaryData?.summary.orders || 0}
                icon={ShoppingCart}
                color="bg-blue-500"
              />
              <MetricCard
                title="Выкупы"
                value={summaryData?.summary.purchases || 0}
                icon={CheckCircle}
                color="bg-green-500"
              />
              <MetricCard
                title="Отмены"
                value={summaryData?.summary.cancellations || 0}
                icon={XCircle}
                color="bg-amber-500"
              />
              <MetricCard
                title="Возвраты"
                value={summaryData?.summary.returns || 0}
                icon={RotateCcw}
                color="bg-red-500"
              />
            </div>
          )}

          {/* Charts */}
          <MetricsCharts data={chartData} />
        </section>

        {/* Warehouse Section */}
        <section>
          <WarehouseTable data={warehouseData} />
        </section>
      </Container>
    </div>
  )
}

export default App
