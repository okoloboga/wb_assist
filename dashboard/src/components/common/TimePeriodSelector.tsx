import { Calendar, TrendingUp, BarChart3, Activity } from 'lucide-react'

type TimePeriod = '1month' | '2months' | '3months' | '6months'

interface TimePeriodSelectorProps {
  value: TimePeriod
  onChange: (period: TimePeriod) => void
}

const periods = [
  { value: '1month' as TimePeriod, label: '1 месяц', icon: Calendar },
  { value: '2months' as TimePeriod, label: '2 месяца', icon: TrendingUp },
  { value: '3months' as TimePeriod, label: '3 месяца', icon: BarChart3 },
  { value: '6months' as TimePeriod, label: '6 месяцев', icon: Activity },
]

export const TimePeriodSelector = ({ value, onChange }: TimePeriodSelectorProps) => {
  return (
    <div className="flex flex-wrap gap-2 mb-8">
      {periods.map(({ value: periodValue, label, icon: Icon }) => (
        <button
          key={periodValue}
          onClick={() => onChange(periodValue)}
          className={`
            flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all
            ${
              value === periodValue
                ? 'bg-primary-600 text-white shadow-md'
                : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
            }
          `}
        >
          <Icon size={18} />
          <span>{label}</span>
        </button>
      ))}
    </div>
  )
}
