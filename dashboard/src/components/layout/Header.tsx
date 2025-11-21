export const Header = () => {
  return (
    <header className="bg-white border-b border-gray-200">
      <div className="container mx-auto px-4 py-6">
        <h1 className="text-3xl font-bold text-gray-900">
          Аналитический дашборд
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Последнее обновление: {new Date().toLocaleString('ru-RU')}
        </p>
      </div>
    </header>
  )
}
