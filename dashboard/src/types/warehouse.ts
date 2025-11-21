/**
 * Элемент склада (товар)
 */
export interface WarehouseItem {
  /** Уникальный идентификатор */
  id: string
  /** Номенклатура товара */
  nomenclature: string
  /** Размер товара */
  size: string
  /** Название склада */
  warehouse: string
  /** Количество на складе */
  quantity: number
  /** Дата последнего обновления */
  lastUpdated: string
}

/**
 * Сводная информация о складах
 */
export interface WarehouseSummary {
  /** Общее количество позиций */
  totalItems: number
  /** Общее количество товаров */
  totalQuantity: number
  /** Количество складов */
  warehouseCount: number
}

/**
 * Полные данные складов
 */
export interface WarehouseData {
  /** Список товаров на складах */
  items: WarehouseItem[]
  /** Сводная информация */
  summary: WarehouseSummary
}
