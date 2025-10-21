from competitive_analysis.price_monitoring.core.google_sheets_client import GoogleSheetsClient
import os, sys

def main():
    client = GoogleSheetsClient(credentials_path='config/credentials.json')
    print('Service ready:', client.service is not None)
    print('Token exists:', os.path.exists('config/token.json'))
    if '--create-test' in sys.argv:
        try:
            resp = client.create_spreadsheet('Auth Test')
            print('Spreadsheet created:', resp.get('spreadsheetId'))
        except Exception as e:
            print('Create spreadsheet error:', e)

if __name__ == '__main__':
    main()