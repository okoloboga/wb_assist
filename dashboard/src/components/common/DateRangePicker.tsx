import { useState } from 'react'
import { Calendar, X } from 'lucide-react'

interface DateRangePickerProps {
  onRangeSelect: (startDate: Date, endDate: Date) => void
  onClose: () => void
}

export const DateRangePicker = ({ onRangeSelect, onClose }: DateRangePickerProps) => {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const handleApply = () => {
    if (startDate && endDate) {
      onRangeSelect(new Date(startDate), new Date(endDate))
      onClose()
    }
  }

  const today = new Date().toISOString().split('T')[0]

  return (
    <div className="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-4 sm:p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4 sm:mb-6">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900">Выбрать период</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="space-y-4">
          {/* Start Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Дата начала
            </label>
            <div className="relative">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                max={endDate || today}
                className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all [&::-webkit-calendar-picker-indicator]:cursor-pointer [&::-webkit-calendar-picker-indicator]:opacity-100 [&::-webkit-calendar-picker-indicator]:hover:opacity-80"
                style={{ colorScheme: 'light' }}
              />
            </div>
          </div>

          {/* End Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Дата окончания
            </label>
            <div className="relative">
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                min={startDate}
                max={today}
                className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all [&::-webkit-calendar-picker-indicator]:cursor-pointer [&::-webkit-calendar-picker-indicator]:opacity-100 [&::-webkit-calendar-picker-indicator]:hover:opacity-80"
                style={{ colorScheme: 'light' }}
              />
            </div>
          </div>

          {/* Quick Presets */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Быстрый выбор
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <button
                onClick={() => {
                  const end = new Date()
                  const start = new Date()
                  start.setDate(start.getDate() - 7)
                  setStartDate(start.toISOString().split('T')[0])
                  setEndDate(end.toISOString().split('T')[0])
                }}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Последние 7 дней
              </button>
              <button
                onClick={() => {
                  const end = new Date()
                  const start = new Date()
                  start.setDate(start.getDate() - 30)
                  setStartDate(start.toISOString().split('T')[0])
                  setEndDate(end.toISOString().split('T')[0])
                }}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Последние 30 дней
              </button>
              <button
                onClick={() => {
                  const end = new Date()
                  const start = new Date()
                  start.setDate(start.getDate() - 90)
                  setStartDate(start.toISOString().split('T')[0])
                  setEndDate(end.toISOString().split('T')[0])
                }}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Последние 90 дней
              </button>
              <button
                onClick={() => {
                  const end = new Date()
                  const start = new Date()
                  start.setMonth(start.getMonth() - 6)
                  setStartDate(start.toISOString().split('T')[0])
                  setEndDate(end.toISOString().split('T')[0])
                }}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Последние 6 месяцев
              </button>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 mt-4 sm:mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors font-medium"
          >
            Отмена
          </button>
          <button
            onClick={handleApply}
            disabled={!startDate || !endDate}
            className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
          >
            Применить
          </button>
        </div>
      </div>
    </div>
  )
}
