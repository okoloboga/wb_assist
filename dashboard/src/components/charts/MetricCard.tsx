import { LucideIcon } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: number
  icon: LucideIcon
  color: string
}

export const MetricCard = ({ title, value, icon: Icon, color }: MetricCardProps) => {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon size={20} className="text-white" />
        </div>
      </div>
      <p className="text-3xl font-bold text-gray-900">
        {value.toLocaleString('ru-RU')}
      </p>
      <p className="text-xs text-gray-500 mt-2">
        За выбранный период
      </p>
    </div>
  )
}
