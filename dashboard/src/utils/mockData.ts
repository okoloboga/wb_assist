/**
 * Mock данные для демонстрации дашборда
 */

// Генерация данных для разных периодов
const generateMockData = (months: number) => {
  const data = []
  const daysPerMonth = 30
  const totalDays = months * daysPerMonth
  const pointsCount = Math.min(totalDays, months * 4) // 4 точки на месяц максимум

  for (let i = 0; i < pointsCount; i++) {
    const dayOffset = Math.floor((totalDays / pointsCount) * i)
    const date = new Date()
    date.setDate(date.getDate() - (totalDays - dayOffset))

    const baseOrders = 300 + Math.random() * 200
    const purchaseRate = 0.8 + Math.random() * 0.1
    const cancellationRate = 0.1 + Math.random() * 0.05
    const returnRate = 0.05 + Math.random() * 0.03

    data.push({
      date: date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }),
      orders: Math.round(baseOrders),
      purchases: Math.round(baseOrders * purchaseRate),
      cancellations: Math.round(baseOrders * cancellationRate),
      returns: Math.round(baseOrders * returnRate),
    })
  }

  return data
}

export const mockChartDataByPeriod = {
  '1month': generateMockData(1),
  '2months': generateMockData(2),
  '3months': generateMockData(3),
  '6months': generateMockData(6),
}

// Для обратной совместимости
export const mockChartData = mockChartDataByPeriod['1month']

export const mockWarehouseData = [
  {
    id: '1',
    nomenclature: 'Футболка базовая',
    size: 'M',
    warehouse: 'Москва (Подольск)',
    quantity: 87,
  },
  {
    id: '2',
    nomenclature: 'Футболка базовая',
    size: 'L',
    warehouse: 'Москва (Подольск)',
    quantity: 45,
  },
  {
    id: '3',
    nomenclature: 'Футболка базовая',
    size: 'S',
    warehouse: 'Санкт-Петербург',
    quantity: 23,
  },
  {
    id: '4',
    nomenclature: 'Джинсы классические',
    size: '32',
    warehouse: 'Москва (Подольск)',
    quantity: 67,
  },
  {
    id: '5',
    nomenclature: 'Джинсы классические',
    size: '34',
    warehouse: 'Екатеринбург',
    quantity: 12,
  },
  {
    id: '6',
    nomenclature: 'Свитшот оверсайз',
    size: 'M',
    warehouse: 'Новосибирск',
    quantity: 34,
  },
  {
    id: '7',
    nomenclature: 'Свитшот оверсайз',
    size: 'L',
    warehouse: 'Казань',
    quantity: 56,
  },
  {
    id: '8',
    nomenclature: 'Кроссовки спортивные',
    size: '42',
    warehouse: 'Москва (Подольск)',
    quantity: 18,
  },
  {
    id: '9',
    nomenclature: 'Кроссовки спортивные',
    size: '43',
    warehouse: 'Санкт-Петербург',
    quantity: 29,
  },
  {
    id: '10',
    nomenclature: 'Куртка демисезонная',
    size: 'XL',
    warehouse: 'Краснодар',
    quantity: 41,
  },
]

export const mockMetrics = {
  orders: 2404,
  purchases: 2034,
  cancellations: 249,
  returns: 121,
}
