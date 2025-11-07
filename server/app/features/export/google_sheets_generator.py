"""
Генератор шаблонов Google Sheets для экспорта данных WB
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleSheetsTemplateGenerator:
    """Генератор шаблонов Google Sheets для экспорта данных WB"""

    def __init__(self):
        self.service = None
        self.drive_service = None  # Добавить клиент Drive
        self._initialize_service()

    def _initialize_service(self):
        """Инициализирует Google Sheets и Drive API сервисы"""
        try:
            key_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'config/wb-assist.json')
            scopes = os.getenv('GOOGLE_SCOPES', 'https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive').split(',')
            
            if not os.path.exists(key_file):
                raise FileNotFoundError(f"Файл ключа не найден: {key_file}")
            
            # Загружаем учетные данные
            credentials = service_account.Credentials.from_service_account_file(
                key_file, 
                scopes=scopes
            )
            
            # Создаем клиенты для Sheets и Drive
            self.service = build('sheets', 'v4', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)  # Добавить
            
            logger.info("Google Sheets API и Drive API сервисы инициализированы успешно")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации Google API: {e}")
            raise

    def create_template(self, template_name: str = None) -> Dict[str, Any]:
        """Возвращает ссылку на готовый шаблон для ручного копирования пользователем"""
        try:
            # Получаем ID шаблона из переменных окружения
            template_id = os.getenv('GOOGLE_TEMPLATE_SPREADSHEET_ID')
            
            if not template_id:
                raise ValueError("GOOGLE_TEMPLATE_SPREADSHEET_ID не установлен в .env")
            
            # Возвращаем ссылку на шаблон с параметром /copy для ручного копирования
            logger.info(f"Предоставлена ссылка на шаблон для копирования: {template_id}")
            
            return {
                'spreadsheet_id': template_id,
                'url': f"https://docs.google.com/spreadsheets/d/{template_id}/copy",
                'title': "WB Assist Template",
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения ссылки на шаблон: {e}")
            raise

    def _setup_spreadsheet_structure(self, spreadsheet_id: str):
        """Настраивает структуру таблицы с вкладками"""
        try:
            # Получаем информацию о существующих листах
            spreadsheet_info = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            existing_sheets = {sheet['properties']['title'] for sheet in spreadsheet_info.get('sheets', [])}
            
            # Создаем необходимые листы
            sheets_to_create = [
                {'title': '⚙️ Настройки'},
                {'title': '📦 Склад'},
                {'title': '🛒 Заказы'},
                {'title': '⭐ Отзывы'},
                {
                    'title': '📅 В разрезе дня',
                    'properties': {
                        'gridProperties': {
                            'columnCount': 35,  # 5 базовых + 29 дат + 1 СУММА
                            'rowCount': 1000
                        }
                    }
                }
            ]
            
            requests = []
            for sheet_info in sheets_to_create:
                if sheet_info['title'] not in existing_sheets:
                    # Формируем properties для листа
                    sheet_properties = {'title': sheet_info['title']}
                    # Если есть дополнительные properties (например, gridProperties), добавляем их
                    if 'properties' in sheet_info:
                        sheet_properties.update(sheet_info['properties'])
                    
                    requests.append({
                        'addSheet': {
                            'properties': sheet_properties
                        }
                    })
            
            if requests:
                body = {'requests': requests}
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                logger.info(f"Создано листов: {len(requests)}")
            
            # Настраиваем заголовки для каждого листа
            self._setup_sheet_headers(spreadsheet_id)
            
        except Exception as e:
            logger.error(f"Ошибка настройки структуры таблицы: {e}")
            raise

    def _setup_sheet_headers(self, spreadsheet_id: str):
        """Настраивает заголовки для всех листов"""
        try:
            # Получаем информацию о листах
            spreadsheet_info = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = spreadsheet_info.get('sheets', [])
            
            # Генерируем заголовки для вкладки "В разрезе дня" (28 дней назад до сегодня)
            daily_headers = self._generate_daily_headers()
            
            # Заголовки для каждого листа
            headers = {
                '⚙️ Настройки': [
                    ['ID кабинета', 'Значение'],
                    ['Token Export', ''],
                    ['Статус подключения', 'Не подключен'],
                    ['Последнее обновление', ''],
                    ['', ''],
                    ['Инструкция:', ''],
                    ['1. Скопируйте эту таблицу в свой Google аккаунт', ''],
                    ['2. Введите ID кабинета и Token Export из бота', ''],
                    ['3. Нажмите "Обновить данные" в меню WB Assist', ''],
                    ['4. Данные будут обновляться автоматически каждые 6 часов', '']
                ],
                '📦 Склад': [
                    ['Артикул', 'Название товара', 'Бренд', 'Размер', 'Склад', 'Количество', 
                     'В пути к клиенту', 'В пути от клиента', 'Цена', 'Скидка', 'Последнее обновление']
                ],
                '🛒 Заказы': [
                    ['Номер заказа', 'Артикул', 'Название', 'Размер', 'Количество', 'Цена', 
                     'Общая сумма', 'Статус', 'Дата заказа', 'Склад отправки', 'Регион доставки',
                     'Комиссия WB', 'СПП %', 'Цена клиента', 'Скидка %']
                ],
                '⭐ Отзывы': [
                    ['ID отзыва', 'Артикул', 'Название', 'Рейтинг', 'Текст отзыва', 'Плюсы', 
                     'Минусы', 'Имя пользователя', 'Цвет', 'Размер', 'Дата отзыва', 
                     'Ответ продавца', 'Просмотрен']
                ],
                '📅 В разрезе дня': [daily_headers]
            }
            
            # Записываем заголовки
            for sheet in sheets:
                sheet_title = sheet['properties']['title']
                if sheet_title in headers:
                    sheet_id = sheet['properties']['sheetId']
                    range_name = f"{sheet_title}!A1"
                    
                    body = {
                        'values': headers[sheet_title]
                    }
                    
                    self.service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption='RAW',
                        body=body
                    ).execute()
            
            logger.info("Заголовки листов настроены")
            
        except Exception as e:
            logger.error(f"Ошибка настройки заголовков: {e}")
            raise
    
    def _generate_daily_headers(self) -> List[str]:
        """Генерирует заголовки для вкладки 'В разрезе дня' (28 дней назад до сегодня)"""
        from datetime import datetime, timedelta
        
        headers = ['📷 Фото', '🆔 Номенклатура', '👗 Название', '↔️ Размер', '⏳ Запас на Дней']
        
        # Генерируем даты за последние 28 дней (от 28 дней назад до сегодня)
        today = datetime.now().date()
        for i in range(28, -1, -1):  # От 28 дней назад до сегодня (включительно)
            date = today - timedelta(days=i)
            date_str = date.strftime('%d.%m.%Y')
            headers.append(date_str)
        
        # Добавляем колонку СУММА в конце
        headers.append('СУММА')
        
        return headers

    def _embed_google_apps_script(self, spreadsheet_id: str):
        """Встраивает Google Apps Script в таблицу"""
        try:
            # Google Apps Script код
            script_code = self._get_google_apps_script()
            
            # Получаем ID скрипта (если есть)
            script_id = self._get_or_create_script(script_code)
            
            if script_id:
                # Привязываем скрипт к таблице
                self._bind_script_to_spreadsheet(script_id, spreadsheet_id)
                logger.info(f"Google Apps Script встроен в таблицу {spreadsheet_id}")
            else:
                logger.warning("Не удалось создать Google Apps Script")
                
        except Exception as e:
            logger.error(f"Ошибка встраивания Google Apps Script: {e}")
            # Не прерываем выполнение, так как это не критично

    def _get_google_apps_script(self) -> str:
        """Возвращает код Google Apps Script"""
        # Получаем базовый URL API из переменных окружения
        import os
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        return f"""
/**
 * Google Apps Script для автоматического обновления данных WB в Google Sheets
 * Версия: 1.0.0
 * Автор: WB Assist
 */

function onOpen() {{
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('WB Assist')
    .addItem('🔄 Обновить данные', 'updateAllData')
    .addItem('🔍 Проверить подключение', 'checkConnection')
    .addItem('⚙️ Настройки', 'showSettings')
    .addItem('❓ Справка', 'showHelp')
    .addToUi();
}}

/**
 * Главная функция обновления всех данных
 */
function updateAllData() {{
  try {{
    const settings = getSettings();
    if (!settings.cabinetId || !settings.token) {{
      SpreadsheetApp.getUi().alert(
        'Ошибка настройки', 
        'Не заполнены ID кабинета или Token Export. Перейдите в настройки и заполните все поля.', 
        SpreadsheetApp.getUi().ButtonSet.OK
      );
      return;
    }}
    
    SpreadsheetApp.getActiveSpreadsheet().toast('Обновление данных...', 'WB Assist', 3);
    
    // Обновляем все вкладки
    updateOrders(settings);
    updateStocks(settings);
    updateReviews(settings);
    
    // Обновляем статус
    updateConnectionStatus('✅ Успешно обновлено', new Date());
    
    SpreadsheetApp.getActiveSpreadsheet().toast('Данные обновлены!', 'WB Assist', 3);
    
  }} catch (error) {{
    console.error('Ошибка обновления данных:', error);
    updateConnectionStatus('❌ Ошибка: ' + error.message, new Date());
    SpreadsheetApp.getUi().alert(
      'Ошибка обновления', 
      'Не удалось обновить данные: ' + error.message, 
      SpreadsheetApp.getUi().ButtonSet.OK
    );
  }}
}}

/**
 * Получает настройки из листа "Настройки"
 */
function getSettings() {{
  const settingsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('⚙️ Настройки');
  if (!settingsSheet) {{
    throw new Error('Лист "Настройки" не найден');
  }}
  
  return {{
    cabinetId: settingsSheet.getRange('B1').getValue(),
    token: settingsSheet.getRange('B2').getValue()
  }};
}}

/**
 * Проверяет подключение к API
 */
function checkConnection() {{
  try {{
    const settings = getSettings();
    if (!settings.cabinetId || !settings.token) {{
      updateConnectionStatus('⚠️ Не настроено', new Date());
      return false;
    }}
    
    // Проверяем подключение к API
    const response = UrlFetchApp.fetch('{api_base_url}/api/export/health', {{
      method: 'GET',
      headers: {{
        'User-Agent': 'WB-Assist-GoogleSheets/1.0'
      }}
    }});
    
    if (response.getResponseCode() === 200) {{
      updateConnectionStatus('✅ Подключено', new Date());
      return true;
    }} else {{
      updateConnectionStatus('❌ Ошибка подключения', new Date());
      return false;
    }}
  }} catch (error) {{
    console.error('Ошибка проверки подключения:', error);
    updateConnectionStatus('❌ Ошибка: ' + error.message, new Date());
    return false;
  }}
}}

/**
 * Обновляет данные заказов
 */
function updateOrders(settings) {{
  try {{
    const url = `{api_base_url}/api/export/orders/${{settings.cabinetId}}?token=${{settings.token}}&limit=1000`;
    const response = UrlFetchApp.fetch(url, {{
      method: 'GET',
      headers: {{
        'User-Agent': 'WB-Assist-GoogleSheets/1.0',
        'Accept': 'application/json'
      }}
    }});
    
    if (response.getResponseCode() !== 200) {{
      throw new Error(`Ошибка API: ${{response.getResponseCode()}}`);
    }}
    
    const data = JSON.parse(response.getContentText());
    
    if (data.data && data.data.length > 0) {{
      const ordersSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('🛒 Заказы');
      if (!ordersSheet) {{
        throw new Error('Лист "Заказы" не найден');
      }}
      
      // Очищаем данные (кроме заголовков)
      const lastRow = ordersSheet.getLastRow();
      if (lastRow > 1) {{
        ordersSheet.getRange(2, 1, lastRow - 1, ordersSheet.getLastColumn()).clear();
      }}
      
      // Записываем новые данные
      const values = data.data.map(row => [
        row.order_id || '',
        row.article || '',
        row.name || '',
        row.size || '',
        row.quantity || 0,
        row.price || 0,
        row.total_price || 0,
        row.status || '',
        row.order_date || '',
        row.warehouse_from || '',
        row.warehouse_to || '',
        row.commission_amount || 0,
        row.spp_percent || 0,
        row.customer_price || 0,
        row.discount_percent || 0
      ]);
      
      if (values.length > 0) {{
        ordersSheet.getRange(2, 1, values.length, values[0].length).setValues(values);
      }}
      
      console.log(`Обновлено заказов: ${{values.length}}`);
    }}
  }} catch (error) {{
    console.error('Ошибка обновления заказов:', error);
    throw error;
  }}
}}

/**
 * Обновляет данные остатков
 */
function updateStocks(settings) {{
  try {{
    const url = `{api_base_url}/api/export/stocks/${{settings.cabinetId}}?token=${{settings.token}}&limit=1000`;
    const response = UrlFetchApp.fetch(url, {{
      method: 'GET',
      headers: {{
        'User-Agent': 'WB-Assist-GoogleSheets/1.0',
        'Accept': 'application/json'
      }}
    }});
    
    if (response.getResponseCode() !== 200) {{
      throw new Error(`Ошибка API: ${{response.getResponseCode()}}`);
    }}
    
    const data = JSON.parse(response.getContentText());
    
    if (data.data && data.data.length > 0) {{
      const stocksSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('📦 Склад');
      if (!stocksSheet) {{
        throw new Error('Лист "Склад" не найден');
      }}
      
      // Очищаем данные (кроме заголовков)
      const lastRow = stocksSheet.getLastRow();
      if (lastRow > 1) {{
        stocksSheet.getRange(2, 1, lastRow - 1, stocksSheet.getLastColumn()).clear();
      }}
      
      // Записываем новые данные
      const values = data.data.map(row => [
        row.article || '',
        row.name || '',
        row.brand || '',
        row.size || '',
        row.warehouse_name || '',
        row.quantity || 0,
        row.in_way_to_client || 0,
        row.in_way_from_client || 0,
        row.price || 0,
        row.discount || 0,
        row.last_updated || ''
      ]);
      
      if (values.length > 0) {{
        stocksSheet.getRange(2, 1, values.length, values[0].length).setValues(values);
      }}
      
      console.log(`Обновлено остатков: ${{values.length}}`);
    }}
  }} catch (error) {{
    console.error('Ошибка обновления остатков:', error);
    throw error;
  }}
}}

/**
 * Обновляет данные отзывов
 */
function updateReviews(settings) {{
  try {{
    const url = `{api_base_url}/api/export/reviews/${{settings.cabinetId}}?token=${{settings.token}}&limit=1000`;
    const response = UrlFetchApp.fetch(url, {{
      method: 'GET',
      headers: {{
        'User-Agent': 'WB-Assist-GoogleSheets/1.0',
        'Accept': 'application/json'
      }}
    }});
    
    if (response.getResponseCode() !== 200) {{
      throw new Error(`Ошибка API: ${{response.getResponseCode()}}`);
    }}
    
    const data = JSON.parse(response.getContentText());
    
    if (data.data && data.data.length > 0) {{
      const reviewsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('⭐ Отзывы');
      if (!reviewsSheet) {{
        throw new Error('Лист "Отзывы" не найден');
      }}
      
      // Очищаем данные (кроме заголовков)
      const lastRow = reviewsSheet.getLastRow();
      if (lastRow > 1) {{
        reviewsSheet.getRange(2, 1, lastRow - 1, reviewsSheet.getLastColumn()).clear();
      }}
      
      // Записываем новые данные
      const values = data.data.map(row => [
        row.review_id || '',
        row.nm_id || '',
        row.product_name || '',
        row.rating || 0,
        row.text || '',
        row.pros || '',
        row.cons || '',
        row.user_name || '',
        row.color || '',
        row.matching_size || '',
        row.created_date || '',
        row.is_answered || false,
        row.was_viewed || false
      ]);
      
      if (values.length > 0) {{
        reviewsSheet.getRange(2, 1, values.length, values[0].length).setValues(values);
      }}
      
      console.log(`Обновлено отзывов: ${{values.length}}`);
    }}
  }} catch (error) {{
    console.error('Ошибка обновления отзывов:', error);
    throw error;
  }}
}}

/**
 * Обновляет статус подключения
 */
function updateConnectionStatus(status, timestamp) {{
  try {{
    const settingsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('⚙️ Настройки');
    if (settingsSheet) {{
      settingsSheet.getRange('B3').setValue(status);
      settingsSheet.getRange('B4').setValue(timestamp);
    }}
  }} catch (error) {{
    console.error('Ошибка обновления статуса:', error);
  }}
}}

/**
 * Показывает настройки
 */
function showSettings() {{
  const ui = SpreadsheetApp.getUi();
  const settings = getSettings();
  
  ui.alert(
    'Настройки WB Assist',
    `ID кабинета: ${{settings.cabinetId || 'Не заполнено'}}\\n` +
    `Token Export: ${{settings.token ? 'Заполнен' : 'Не заполнен'}}\\n\\n` +
    'Для изменения настроек отредактируйте ячейки B1 и B2 в листе "Настройки"',
    ui.ButtonSet.OK
  );
}}

/**
 * Показывает справку
 */
function showHelp() {{
  const ui = SpreadsheetApp.getUi();
  ui.alert(
    'Справка WB Assist',
    '📋 Инструкция по использованию:\\n\\n' +
    '1. Заполните ID кабинета и Token Export в листе "Настройки"\\n' +
    '2. Нажмите "Обновить данные" для получения данных\\n' +
    '3. Данные обновляются автоматически с интервалом из SYNC_INTERVAL\\n' +
    '4. При проблемах используйте "Проверить подключение"\\n\\n' +
    '🔧 Поддержка: @wb_assist_bot',
    ui.ButtonSet.OK
  );
}}

/**
 * Создает триггер для автоматического обновления с интервалом из SYNC_INTERVAL
 */
function createTrigger() {{
  try {{
    // Удаляем существующие триггеры
    deleteTrigger();
    
    // Получаем интервал синхронизации из API
    const syncInterval = getSyncInterval();
    
    if (syncInterval) {{
      // Создаем триггер с полученным интервалом
      ScriptApp.newTrigger('updateAllData')
        .timeBased()
        .everyMinutes(syncInterval)
        .create();
      
      console.log(`Триггер автоматического обновления создан с интервалом ${{syncInterval}} минут`);
    }} else {{
      // Fallback на 6 часов, если не удалось получить интервал
      ScriptApp.newTrigger('updateAllData')
        .timeBased()
        .everyHours(6)
        .create();
      
      console.log('Триггер автоматического обновления создан с интервалом 6 часов (fallback)');
    }}
  }} catch (error) {{
    console.error('Ошибка создания триггера:', error);
  }}
}}

/**
 * Получает интервал синхронизации из API сервера
 */
function getSyncInterval() {{
  try {{
    const response = UrlFetchApp.fetch('{api_base_url}/api/export/sync-interval', {{
      method: 'GET',
      headers: {{
        'User-Agent': 'WB-Assist-GoogleSheets/1.0',
        'Accept': 'application/json'
      }}
    }});
    
    if (response.getResponseCode() === 200) {{
      const data = JSON.parse(response.getContentText());
      // Конвертируем секунды в минуты для Google Apps Script
      return Math.max(1, Math.floor(data.sync_interval_seconds / 60));
    }}
  }} catch (error) {{
    console.error('Ошибка получения интервала синхронизации:', error);
  }}
  
  return null; // Fallback на 6 часов
}}

/**
 * Удаляет триггеры
 */
function deleteTrigger() {{
  try {{
    const triggers = ScriptApp.getProjectTriggers();
    triggers.forEach(trigger => {{
      if (trigger.getHandlerFunction() === 'updateAllData') {{
        ScriptApp.deleteTrigger(trigger);
      }}
    }});
    
    console.log('Старые триггеры удалены');
  }} catch (error) {{
    console.error('Ошибка удаления триггеров:', error);
  }}
}}

/**
 * Инициализация при первом запуске
 */
function initialize() {{
  try {{
    // Создаем триггер для автоматического обновления
    createTrigger();
    
    // Проверяем подключение
    checkConnection();
    
    console.log('WB Assist инициализирован');
  }} catch (error) {{
    console.error('Ошибка инициализации:', error);
  }}
}}
"""

    def _get_or_create_script(self, script_code: str) -> Optional[str]:
        """Создает или получает Google Apps Script"""
        # В реальной реализации здесь будет создание скрипта через Google Apps Script API
        # Пока возвращаем None, так как это требует дополнительной настройки
        logger.info("Google Apps Script код подготовлен (требует ручного встраивания)")
        return None

    def _bind_script_to_spreadsheet(self, script_id: str, spreadsheet_id: str):
        """Привязывает скрипт к таблице"""
        # В реальной реализации здесь будет привязка скрипта
        logger.info(f"Скрипт {script_id} привязан к таблице {spreadsheet_id}")

    def _setup_formatting(self, spreadsheet_id: str):
        """Настраивает форматирование таблицы"""
        try:
            # Получаем информацию о листах
            spreadsheet_info = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = spreadsheet_info.get('sheets', [])
            
            format_requests = []
            
            for sheet in sheets:
                sheet_id = sheet['properties']['sheetId']
                sheet_title = sheet['properties']['title']
                
                # Форматирование заголовков
                format_requests.append({
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {
                                    'red': 0.2,
                                    'green': 0.6,
                                    'blue': 0.9
                                },
                                'textFormat': {
                                    'bold': True,
                                    'foregroundColor': {
                                        'red': 1.0,
                                        'green': 1.0,
                                        'blue': 1.0
                                    }
                                }
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                    }
                })
                
                # Автоширина колонок
                format_requests.append({
                    'autoResizeDimensions': {
                        'dimensions': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': 20  # Достаточно для всех колонок
                        }
                    }
                })
            
            if format_requests:
                body = {'requests': format_requests}
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                
            logger.info("Форматирование применено")
            
        except Exception as e:
            logger.error(f"Ошибка применения форматирования: {e}")
            # Не прерываем выполнение

    def get_template_info(self, spreadsheet_id: str) -> Dict[str, Any]:
        """Получает информацию о шаблоне"""
        try:
            spreadsheet_info = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            
            return {
                'spreadsheet_id': spreadsheet_id,
                'title': spreadsheet_info['properties']['title'],
                'url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                'sheets_count': len(spreadsheet_info.get('sheets', [])),
                'is_ready': True
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о шаблоне: {e}")
            raise
