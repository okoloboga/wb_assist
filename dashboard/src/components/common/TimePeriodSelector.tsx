import { Calendar, TrendingUp, BarChart3, Activity, CalendarRange } from 'lucide-react'

type TimePeriod = '1month' | '2months' | '3months' | '6months' | 'custom'

interface TimePeriodSelectorProps {
  value: TimePeriod
  onChange: (period: TimePeriod) => void
  onCustomClick: () => void
  customLabel?: string
}

const periods = [
  { value: '1month' as TimePeriod, label: '1 месяц', icon: Calendar },
  { value: '2months' as TimePeriod, label: '2 месяца', icon: TrendingUp },
  { value: '3months' as TimePeriod, label: '3 месяца', icon: BarChart3 },
  { value: '6months' as TimePeriod, label: '6 месяцев', icon: Activity },
]

export const TimePeriodSelector = ({
  value,
  onChange,
  onCustomClick,
  customLabel,
}: TimePeriodSelectorProps) => {
  return (
    <div className="flex flex-wrap gap-2 mb-4 sm:mb-6 lg:mb-8">
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

      {/* Custom Period Button */}
      <button
        onClick={onCustomClick}
        className={`
          flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-lg text-sm sm:text-base font-medium transition-all
          ${
            value === 'custom'
              ? 'bg-primary-600 text-white shadow-md'
              : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
          }
        `}
      >
        <CalendarRange size={16} className="sm:w-[18px] sm:h-[18px]" />
        <span className="whitespace-nowrap">{customLabel || 'Выбрать период'}</span>
      </button>
    </div>
  )
}
