import { useState, useMemo } from 'react'
import { Package, MapPin, Ruler, Search, X } from 'lucide-react'

interface WarehouseItem {
  id: string
  nomenclature: string
  size: string
  warehouse: string
  quantity: number
}

interface WarehouseTableProps {
  data: WarehouseItem[]
}

export const WarehouseTable = ({ data }: WarehouseTableProps) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>('all')
  const [selectedSize, setSelectedSize] = useState<string>('all')
  const [minQuantity, setMinQuantity] = useState<string>('')
  const [maxQuantity, setMaxQuantity] = useState<string>('')

  // Получаем уникальные значения для фильтров
  const warehouses = useMemo(() => {
    const unique = Array.from(new Set(data.map((item) => item.warehouse)))
    return unique.sort()
  }, [data])

  const sizes = useMemo(() => {
    const unique = Array.from(new Set(data.map((item) => item.size)))
    return unique.sort()
  }, [data])

  // Фильтрация данных
  const filteredData = useMemo(() => {
    return data.filter((item) => {
      const matchesSearch =
        searchQuery === '' ||
        item.nomenclature.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesWarehouse =
        selectedWarehouse === 'all' || item.warehouse === selectedWarehouse
      const matchesSize = selectedSize === 'all' || item.size === selectedSize
      
      const min = minQuantity === '' ? 0 : parseInt(minQuantity)
      const max = maxQuantity === '' ? Infinity : parseInt(maxQuantity)
      const matchesQuantity = item.quantity >= min && item.quantity <= max

      return matchesSearch && matchesWarehouse && matchesSize && matchesQuantity
    })
  }, [data, searchQuery, selectedWarehouse, selectedSize, minQuantity, maxQuantity])

  const hasActiveFilters = searchQuery !== '' || selectedWarehouse !== 'all' || selectedSize !== 'all' || minQuantity !== '' || maxQuantity !== ''

  const clearFilters = () => {
    setSearchQuery('')
    setSelectedWarehouse('all')
    setSelectedSize('all')
    setMinQuantity('')
    setMaxQuantity('')
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Состояние складов</h3>
            <p className="text-sm text-gray-500 mt-1">
              Показано: {filteredData.length} из {data.length}
            </p>
          </div>
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X size={16} />
              Сбросить фильтры
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {/* Search */}
          <div className="relative md:col-span-2">
            <Search
              size={18}
              className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              placeholder="Поиск по номенклатуре..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all"
            />
          </div>

          {/* Warehouse Filter */}
          <select
            value={selectedWarehouse}
            onChange={(e) => setSelectedWarehouse(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all bg-white"
          >
            <option value="all">Все склады</option>
            {warehouses.map((warehouse) => (
              <option key={warehouse} value={warehouse}>
                {warehouse}
              </option>
            ))}
          </select>

          {/* Size Filter */}
          <select
            value={selectedSize}
            onChange={(e) => setSelectedSize(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all bg-white"
          >
            <option value="all">Все размеры</option>
            {sizes.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>

          {/* Quantity Range Filter */}
          <div className="flex items-center gap-2">
            <input
              type="number"
              placeholder="От"
              value={minQuantity}
              onChange={(e) => setMinQuantity(e.target.value)}
              min="0"
              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all text-sm"
            />
            <span className="text-gray-400">-</span>
            <input
              type="number"
              placeholder="До"
              value={maxQuantity}
              onChange={(e) => setMaxQuantity(e.target.value)}
              min="0"
              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all text-sm"
            />
          </div>
        </div>
      </div>

      {/* Desktop Table */}
      <div className="hidden md:block overflow-x-auto">
        {filteredData.length === 0 ? (
          <div className="p-12 text-center">
            <Package size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500 text-lg">Нет данных по заданным фильтрам</p>
            <button
              onClick={clearFilters}
              className="mt-4 text-primary-600 hover:text-primary-700 font-medium"
            >
              Сбросить фильтры
            </button>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <div className="flex items-center gap-2">
                    <Package size={16} />
                    Номенклатура
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <div className="flex items-center gap-2">
                    <Ruler size={16} />
                    Размер
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <div className="flex items-center gap-2">
                    <MapPin size={16} />
                    Склад
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Количество
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredData.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {item.nomenclature}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                  {item.size}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                  {item.warehouse}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      item.quantity > 50
                        ? 'bg-green-100 text-green-800'
                        : item.quantity > 20
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {item.quantity} шт
                  </span>
                </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Mobile Cards */}
      <div className="md:hidden divide-y divide-gray-200">
        {filteredData.length === 0 ? (
          <div className="p-12 text-center">
            <Package size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">Нет данных по заданным фильтрам</p>
            <button
              onClick={clearFilters}
              className="mt-4 text-primary-600 hover:text-primary-700 font-medium"
            >
              Сбросить фильтры
            </button>
          </div>
        ) : (
          filteredData.map((item) => (
          <div key={item.id} className="p-4 hover:bg-gray-50 transition-colors">
            <div className="flex items-start justify-between mb-3">
              <h4 className="font-medium text-gray-900">{item.nomenclature}</h4>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  item.quantity > 50
                    ? 'bg-green-100 text-green-800'
                    : item.quantity > 20
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-red-100 text-red-800'
                }`}
              >
                {item.quantity} шт
              </span>
            </div>
            <div className="space-y-2 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <Ruler size={14} />
                <span>Размер: {item.size}</span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin size={14} />
                <span>Склад: {item.warehouse}</span>
              </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
