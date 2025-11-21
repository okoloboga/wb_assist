import { LucideIcon } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: number
  icon: LucideIcon
  color: string
}

export const MetricCard = ({ title, value, icon: Icon, color }: MetricCardProps) => {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-2 sm:mb-4">
        <h3 className="text-xs sm:text-sm font-medium text-gray-600">{title}</h3>
        <div className={`p-1.5 sm:p-2 rounded-lg ${color}`}>
          <Icon size={16} className="sm:w-5 sm:h-5 text-white" />
        </div>
      </div>
      <p className="text-xl sm:text-3xl font-bold text-gray-900">
        {value.toLocaleString('ru-RU')}
      </p>
      <p className="text-[10px] sm:text-xs text-gray-500 mt-1 sm:mt-2">
        За выбранный период
      </p>
    </div>
  )
}
