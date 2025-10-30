#!/usr/bin/env python3
"""
Тестовый скрипт для проверки подключения к Google Sheets API
"""

import os
import sys
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def load_credentials():
    """Загружает учетные данные из .env файла"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv не установлен, используем переменные окружения напрямую")
    
    # Получаем путь к файлу ключа
    key_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'server/config/wb-assist-352ded7b5635.json')
    scopes = os.getenv('GOOGLE_SCOPES', 'https://www.googleapis.com/auth/spreadsheets').split(',')
    
    print(f"🔑 Загружаем ключ из: {key_file}")
    print(f"📋 Scopes: {scopes}")
    
    if not os.path.exists(key_file):
        print(f"❌ Файл ключа не найден: {key_file}")
        return None, None
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            key_file, 
            scopes=scopes
        )
        print("✅ Учетные данные загружены успешно")
        return credentials, scopes
    except Exception as e:
        print(f"❌ Ошибка загрузки учетных данных: {e}")
        return None, None

def test_google_sheets_connection():
    """Тестирует подключение к Google Sheets API"""
    print("🚀 Начинаем тестирование Google Sheets API...")
    print("=" * 50)
    
    # Загружаем учетные данные
    credentials, scopes = load_credentials()
    if not credentials:
        return False
    
    try:
        # Создаем клиент
        print("🔧 Создаем клиент Google Sheets...")
        service = build('sheets', 'v4', credentials=credentials)
        print("✅ Клиент создан успешно")
        
        # Тест 1: Работа с существующей таблицей
        print("\n📊 Тест 1: Работа с существующей таблицей...")
        existing_spreadsheet_id = "1ElbYUDv0hesvYx4h6s_8L6EQzQtoPu5mqcndt2-ATJc"
        
        try:
            # Получаем информацию о таблице
            spreadsheet_info = service.spreadsheets().get(spreadsheetId=existing_spreadsheet_id).execute()
            print(f"✅ Доступ к таблице получен: {spreadsheet_info['properties']['title']}")
            print(f"🔗 Ссылка: https://docs.google.com/spreadsheets/d/{existing_spreadsheet_id}")
        except HttpError as e:
            if e.resp.status == 403:
                print("❌ Нет доступа к таблице. Убедитесь, что Service Account добавлен в таблицу.")
                print(f"📧 Email Service Account: {credentials.service_account_email}")
                return False
            else:
                print(f"❌ Ошибка доступа к таблице: {e}")
                return False
        
        # Получаем список листов
        sheets = spreadsheet_info.get('sheets', [])
        print(f"📋 Найдено листов: {len(sheets)}")
        for sheet in sheets:
            print(f"  - {sheet['properties']['title']}")
        
        # Тест 2: Чтение данных
        print("\n📊 Тест 2: Чтение данных...")
        range_name = f"{sheets[0]['properties']['title']}!A1:Z10"
        result = service.spreadsheets().values().get(
            spreadsheetId=existing_spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        print(f"✅ Прочитано строк: {len(values)}")
        if values:
            print(f"📝 Первая строка: {values[0]}")
        
        # Тест 3: Запись данных
        print("\n📊 Тест 3: Запись данных...")
        test_data = [
            ['Тест', 'Данные', 'WB Assist'],
            ['Время', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ''],
            ['Статус', 'Успешно', '✅']
        ]
        
        body = {
            'values': test_data
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=existing_spreadsheet_id,
            range=f"{sheets[0]['properties']['title']}!A1:C3",
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"✅ Данные записаны: {result['updatedCells']} ячеек обновлено")
        
        # Тест 4: Создание листов
        print("\n📊 Тест 4: Создание листов...")
        requests = [
            {
                'addSheet': {
                    'properties': {
                        'title': 'Настройки'
                    }
                }
            },
            {
                'addSheet': {
                    'properties': {
                        'title': 'Склад'
                    }
                }
            },
            {
                'addSheet': {
                    'properties': {
                        'title': 'Заказы'
                    }
                }
            },
            {
                'addSheet': {
                    'properties': {
                        'title': 'Отзывы'
                    }
                }
            }
        ]
        
        body = {
            'requests': requests
        }
        
        result = service.spreadsheets().batchUpdate(
            spreadsheetId=existing_spreadsheet_id,
            body=body
        ).execute()
        
        print(f"✅ Создано листов: {len(result['replies'])}")
        
        # Тест 5: Форматирование
        print("\n📊 Тест 5: Форматирование...")
        format_requests = [
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
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
            }
        ]
        
        body = {
            'requests': format_requests
        }
        
        result = service.spreadsheets().batchUpdate(
            spreadsheetId=existing_spreadsheet_id,
            body=body
        ).execute()
        
        print("✅ Форматирование применено")
        
        print("\n" + "=" * 50)
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print(f"🔗 Ссылка на тестовую таблицу: https://docs.google.com/spreadsheets/d/{existing_spreadsheet_id}")
        print("=" * 50)
        
        return True
        
    except HttpError as e:
        print(f"❌ Ошибка Google Sheets API: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def main():
    """Главная функция"""
    print("🧪 Тестирование Google Sheets API для WB Assist")
    print("=" * 50)
    
    # Проверяем зависимости
    try:
        import google.auth
        import googleapiclient
        print("✅ Google API библиотеки установлены")
    except ImportError as e:
        print(f"❌ Не установлены зависимости: {e}")
        print("📦 Установите: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return
    
    # Запускаем тесты
    success = test_google_sheets_connection()
    
    if success:
        print("\n✅ Готово к работе с Google Sheets!")
        print("🚀 Можно приступать к реализации экспорта данных")
    else:
        print("\n❌ Есть проблемы с подключением")
        print("🔧 Проверьте настройки и попробуйте снова")

if __name__ == "__main__":
    main()
