/**
 * Mock данные для демонстрации дашборда
 */

// Генерация данных для разных периодов
const generateMockData = (days: number) => {
  const data = []
  const pointsCount = Math.min(days, Math.ceil(days / 7)) // Примерно 1 точка на неделю

  for (let i = 0; i < pointsCount; i++) {
    const dayOffset = Math.floor((days / pointsCount) * i)
    const date = new Date()
    date.setDate(date.getDate() - (days - dayOffset))

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
  '30days': generateMockData(30),
  '60days': generateMockData(60),
  '90days': generateMockData(90),
  '180days': generateMockData(180),
}

// Для обратной совместимости
export const mockChartData = mockChartDataByPeriod['30days']

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
