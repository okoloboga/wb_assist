/**
 * Google Apps Script для автоматического обновления данных WB в Google Sheets
 * Версия: 1.0.0
 * Автор: WB Assist
 */

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('WB Assist')
    .addItem('🔄 Обновить данные', 'updateAllData')
    .addItem('🔍 Проверить подключение', 'checkConnection')
    .addItem('⚙️ Настройки', 'showSettings')
    .addItem('❓ Справка', 'showHelp')
    .addToUi();
}

/**
 * Главная функция обновления всех данных
 */
function updateAllData() {
  try {
    const settings = getSettings();
    if (!settings.cabinetId || !settings.token) {
      SpreadsheetApp.getUi().alert(
        'Ошибка настройки', 
        'Не заполнены ID кабинета или Token Export. Перейдите в настройки и заполните все поля.', 
        SpreadsheetApp.getUi().ButtonSet.OK
      );
      return;
    }
    
    SpreadsheetApp.getActiveSpreadsheet().toast('Обновление данных...', 'WB Assist', 3);
    
    // Обновляем все вкладки
    updateOrders(settings);
    updateStocks(settings);
    updateReviews(settings);
    
    // Обновляем статус
    updateConnectionStatus('✅ Успешно обновлено', new Date());
    
    SpreadsheetApp.getActiveSpreadsheet().toast('Данные обновлены!', 'WB Assist', 3);
    
  } catch (error) {
    console.error('Ошибка обновления данных:', error);
    updateConnectionStatus('❌ Ошибка: ' + error.message, new Date());
    SpreadsheetApp.getUi().alert(
      'Ошибка обновления', 
      'Не удалось обновить данные: ' + error.message, 
      SpreadsheetApp.getUi().ButtonSet.OK
    );
  }
}

/**
 * Получает настройки из листа "Настройки"
 */
function getSettings() {
  const settingsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('⚙️ Настройки');
  if (!settingsSheet) {
    throw new Error('Лист "Настройки" не найден');
  }
  
  return {
    cabinetId: settingsSheet.getRange('B1').getValue(),
    token: settingsSheet.getRange('B2').getValue()
  };
}

/**
 * Проверяет подключение к API
 */
function checkConnection() {
  try {
    const settings = getSettings();
    if (!settings.cabinetId || !settings.token) {
      updateConnectionStatus('⚠️ Не настроено', new Date());
      return false;
    }
    
    // Проверяем подключение к API
    const response = UrlFetchApp.fetch('https://your-api-domain.com/api/export/health', {
      method: 'GET',
      headers: {
        'User-Agent': 'WB-Assist-GoogleSheets/1.0'
      }
    });
    
    if (response.getResponseCode() === 200) {
      updateConnectionStatus('✅ Подключено', new Date());
      return true;
    } else {
      updateConnectionStatus('❌ Ошибка подключения', new Date());
      return false;
    }
  } catch (error) {
    console.error('Ошибка проверки подключения:', error);
    updateConnectionStatus('❌ Ошибка: ' + error.message, new Date());
    return false;
  }
}

/**
 * Обновляет данные заказов
 */
function updateOrders(settings) {
  try {
    const url = `https://your-api-domain.com/api/export/orders/${settings.cabinetId}?token=${settings.token}&limit=1000`;
    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: {
        'User-Agent': 'WB-Assist-GoogleSheets/1.0',
        'Accept': 'application/json'
      }
    });
    
    if (response.getResponseCode() !== 200) {
      throw new Error(`Ошибка API: ${response.getResponseCode()}`);
    }
    
    const data = JSON.parse(response.getContentText());
    
    if (data.data && data.data.length > 0) {
      const ordersSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('🛒 Заказы');
      if (!ordersSheet) {
        throw new Error('Лист "Заказы" не найден');
      }
      
      // Очищаем данные (кроме заголовков)
      const lastRow = ordersSheet.getLastRow();
      if (lastRow > 1) {
        ordersSheet.getRange(2, 1, lastRow - 1, ordersSheet.getLastColumn()).clear();
      }
      
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
      
      if (values.length > 0) {
        ordersSheet.getRange(2, 1, values.length, values[0].length).setValues(values);
      }
      
      console.log(`Обновлено заказов: ${values.length}`);
    }
  } catch (error) {
    console.error('Ошибка обновления заказов:', error);
    throw error;
  }
}

/**
 * Обновляет данные остатков
 */
function updateStocks(settings) {
  try {
    const url = `https://your-api-domain.com/api/export/stocks/${settings.cabinetId}?token=${settings.token}&limit=1000`;
    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: {
        'User-Agent': 'WB-Assist-GoogleSheets/1.0',
        'Accept': 'application/json'
      }
    });
    
    if (response.getResponseCode() !== 200) {
      throw new Error(`Ошибка API: ${response.getResponseCode()}`);
    }
    
    const data = JSON.parse(response.getContentText());
    
    if (data.data && data.data.length > 0) {
      const stocksSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('📦 Склад');
      if (!stocksSheet) {
        throw new Error('Лист "Склад" не найден');
      }
      
      // Очищаем данные (кроме заголовков)
      const lastRow = stocksSheet.getLastRow();
      if (lastRow > 1) {
        stocksSheet.getRange(2, 1, lastRow - 1, stocksSheet.getLastColumn()).clear();
      }
      
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
      
      if (values.length > 0) {
        stocksSheet.getRange(2, 1, values.length, values[0].length).setValues(values);
      }
      
      console.log(`Обновлено остатков: ${values.length}`);
    }
  } catch (error) {
    console.error('Ошибка обновления остатков:', error);
    throw error;
  }
}

/**
 * Обновляет данные отзывов
 */
function updateReviews(settings) {
  try {
    const url = `https://your-api-domain.com/api/export/reviews/${settings.cabinetId}?token=${settings.token}&limit=1000`;
    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: {
        'User-Agent': 'WB-Assist-GoogleSheets/1.0',
        'Accept': 'application/json'
      }
    });
    
    if (response.getResponseCode() !== 200) {
      throw new Error(`Ошибка API: ${response.getResponseCode()}`);
    }
    
    const data = JSON.parse(response.getContentText());
    
    if (data.data && data.data.length > 0) {
      const reviewsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('⭐ Отзывы');
      if (!reviewsSheet) {
        throw new Error('Лист "Отзывы" не найден');
      }
      
      // Очищаем данные (кроме заголовков)
      const lastRow = reviewsSheet.getLastRow();
      if (lastRow > 1) {
        reviewsSheet.getRange(2, 1, lastRow - 1, reviewsSheet.getLastColumn()).clear();
      }
      
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
      
      if (values.length > 0) {
        reviewsSheet.getRange(2, 1, values.length, values[0].length).setValues(values);
      }
      
      console.log(`Обновлено отзывов: ${values.length}`);
    }
  } catch (error) {
    console.error('Ошибка обновления отзывов:', error);
    throw error;
  }
}

/**
 * Обновляет статус подключения
 */
function updateConnectionStatus(status, timestamp) {
  try {
    const settingsSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('⚙️ Настройки');
    if (settingsSheet) {
      settingsSheet.getRange('B3').setValue(status);
      settingsSheet.getRange('B4').setValue(timestamp);
    }
  } catch (error) {
    console.error('Ошибка обновления статуса:', error);
  }
}

/**
 * Показывает настройки
 */
function showSettings() {
  const ui = SpreadsheetApp.getUi();
  const settings = getSettings();
  
  ui.alert(
    'Настройки WB Assist',
    `ID кабинета: ${settings.cabinetId || 'Не заполнено'}\\n` +
    `Token Export: ${settings.token ? 'Заполнен' : 'Не заполнен'}\\n\\n` +
    'Для изменения настроек отредактируйте ячейки B1 и B2 в листе "Настройки"',
    ui.ButtonSet.OK
  );
}

/**
 * Показывает справку
 */
function showHelp() {
  const ui = SpreadsheetApp.getUi();
  ui.alert(
    'Справка WB Assist',
    '📋 Инструкция по использованию:\\n\\n' +
    '1. Заполните ID кабинета и Token Export в листе "Настройки"\\n' +
    '2. Нажмите "Обновить данные" для получения данных\\n' +
    '3. Данные обновляются автоматически каждые 6 часов\\n' +
    '4. При проблемах используйте "Проверить подключение"\\n\\n' +
    '🔧 Поддержка: @wb_assist_bot',
    ui.ButtonSet.OK
  );
}

/**
 * Создает триггер для автоматического обновления с интервалом из SYNC_INTERVAL
 */
function createTrigger() {
  try {
    // Удаляем существующие триггеры
    deleteTrigger();
    
    // Получаем интервал синхронизации из API
    const syncInterval = getSyncInterval();
    
    if (syncInterval) {
      // Создаем триггер с полученным интервалом
      ScriptApp.newTrigger('updateAllData')
        .timeBased()
        .everyMinutes(syncInterval)
        .create();
      
      console.log(`Триггер автоматического обновления создан с интервалом ${syncInterval} минут`);
    } else {
      // Fallback на 6 часов, если не удалось получить интервал
      ScriptApp.newTrigger('updateAllData')
        .timeBased()
        .everyHours(6)
        .create();
      
      console.log('Триггер автоматического обновления создан с интервалом 6 часов (fallback)');
    }
  } catch (error) {
    console.error('Ошибка создания триггера:', error);
  }
}

/**
 * Получает интервал синхронизации из API сервера
 */
function getSyncInterval() {
  try {
    const response = UrlFetchApp.fetch('https://your-api-domain.com/api/export/sync-interval', {
      method: 'GET',
      headers: {
        'User-Agent': 'WB-Assist-GoogleSheets/1.0',
        'Accept': 'application/json'
      }
    });
    
    if (response.getResponseCode() === 200) {
      const data = JSON.parse(response.getContentText());
      // Конвертируем секунды в минуты для Google Apps Script
      return Math.max(1, Math.floor(data.sync_interval_seconds / 60));
    }
  } catch (error) {
    console.error('Ошибка получения интервала синхронизации:', error);
  }
  
  return null; // Fallback на 6 часов
}

/**
 * Удаляет триггеры
 */
function deleteTrigger() {
  try {
    const triggers = ScriptApp.getProjectTriggers();
    triggers.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'updateAllData') {
        ScriptApp.deleteTrigger(trigger);
      }
    });
    
    console.log('Старые триггеры удалены');
  } catch (error) {
    console.error('Ошибка удаления триггеров:', error);
  }
}

/**
 * Инициализация при первом запуске
 */
function initialize() {
  try {
    // Создаем триггер для автоматического обновления
    createTrigger();
    
    // Проверяем подключение
    checkConnection();
    
    console.log('WB Assist инициализирован');
  } catch (error) {
    console.error('Ошибка инициализации:', error);
  }
}
