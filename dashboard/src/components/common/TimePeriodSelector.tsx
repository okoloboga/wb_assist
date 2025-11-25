import { Calendar, TrendingUp, BarChart3, Activity } from 'lucide-react'

type TimePeriod = '30days' | '60days' | '90days' | '180days'

interface TimePeriodSelectorProps {
  value: TimePeriod
  onChange: (period: TimePeriod) => void
}

const periods = [
  { value: '30days' as TimePeriod, label: '30 дней', icon: Calendar },
  { value: '60days' as TimePeriod, label: '60 дней', icon: TrendingUp },
  { value: '90days' as TimePeriod, label: '90 дней', icon: BarChart3 },
  { value: '180days' as TimePeriod, label: '180 дней', icon: Activity },
]

export const TimePeriodSelector = ({ value, onChange }: TimePeriodSelectorProps) => {
  return (
    <div className="flex flex-wrap justify-center sm:justify-start gap-2 mb-4 sm:mb-6 lg:mb-8">
      {periods.map(({ value: periodValue, label, icon: Icon }) => (
        <button
          key={periodValue}
          onClick={() => onChange(periodValue)}
          className={`
            flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-lg text-sm sm:text-base font-medium transition-all
            ${
              value === periodValue
                ? 'bg-primary-600 text-white shadow-md'
                : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
            }
          `}
        >
          <Icon size={16} className="sm:w-[18px] sm:h-[18px]" />
          <span>{label}</span>
        </button>
      ))}
    </div>
  )
}
