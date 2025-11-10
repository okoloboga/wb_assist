# Скрипт для диагностики проблем с GPT анализом
# Использование: .\debug_gpt.ps1

param(
    [switch]$Logs,
    [switch]$Response,
    [switch]$Test,
    [switch]$All
)

$ErrorActionPreference = "Continue"

Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "  GPT ANALYSIS DEBUGGER" -ForegroundColor Yellow
Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

# Функция для показа логов
function Show-Logs {
    Write-Host "[1] Checking GPT service logs..." -ForegroundColor Green
    Write-Host ""
    
    $logOutput = docker-compose logs --tail=100 gpt 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Could not get logs. Is docker-compose running?" -ForegroundColor Red
        return
    }
    
    # Фильтруем важные сообщения
    Write-Host "=== RECENT GPT LOGS ===" -ForegroundColor Cyan
    $logOutput | Select-String -Pattern "Got response|Finish reason|Failed to extract|ERROR|Saved raw response" | Select-Object -Last 20
    
    Write-Host ""
    Write-Host "=== FINISH REASONS ===" -ForegroundColor Cyan
    $logOutput | Select-String -Pattern "Finish reason" | Select-Object -Last 5
    
    Write-Host ""
    Write-Host "=== ERRORS ===" -ForegroundColor Cyan
    $logOutput | Select-String -Pattern "ERROR|Failed|❌" | Select-Object -Last 10
}

# Функция для копирования ответа GPT
function Get-Response {
    Write-Host "[2] Copying last GPT response..." -ForegroundColor Green
    Write-Host ""
    
    # Получаем ID контейнера
    $containerId = docker-compose ps -q gpt 2>&1
    
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($containerId)) {
        Write-Host "ERROR: GPT container not found. Is it running?" -ForegroundColor Red
        Write-Host "Try: docker-compose up -d gpt" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Container ID: $containerId" -ForegroundColor Gray
    
    # Копируем файл
    $outputFile = "last_gpt_response.txt"
    docker cp "${containerId}:/app/gpt_integration/analysis/debug/last_gpt_response.txt" $outputFile 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Could not copy debug file. It may not exist yet." -ForegroundColor Yellow
        Write-Host "Run an AI analysis first, then try again." -ForegroundColor Yellow
        return
    }
    
    Write-Host "SUCCESS: Response saved to $outputFile" -ForegroundColor Green
    Write-Host ""
    
    # Показываем статистику
    $content = Get-Content $outputFile -Raw -Encoding UTF8
    $size = $content.Length
    $lines = ($content -split "`n").Count
    
    Write-Host "=== FILE STATS ===" -ForegroundColor Cyan
    Write-Host "Size: $size chars"
    Write-Host "Lines: $lines"
    Write-Host ""
    
    # Показываем начало и конец
    Write-Host "=== FIRST 500 CHARS ===" -ForegroundColor Cyan
    Write-Host $content.Substring(0, [Math]::Min(500, $size))
    Write-Host ""
    Write-Host "=== LAST 500 CHARS ===" -ForegroundColor Cyan
    $startPos = [Math]::Max(0, $size - 500)
    Write-Host $content.Substring($startPos)
    Write-Host ""
    
    # Проверяем наличие markdown блоков
    if ($content -match '```json') {
        Write-Host "✓ Found ```json markdown block" -ForegroundColor Green
    } elseif ($content -match '```') {
        Write-Host "⚠ Found ``` markdown block (without json label)" -ForegroundColor Yellow
    } else {
        Write-Host "✗ No markdown blocks found" -ForegroundColor Red
    }
    
    # Проверяем наличие JSON
    if ($content -match '\{.*"telegram".*\}') {
        Write-Host "✓ Found JSON with 'telegram' field" -ForegroundColor Green
    } elseif ($content -match '\{') {
        Write-Host "⚠ Found JSON but no 'telegram' field" -ForegroundColor Yellow
    } else {
        Write-Host "✗ No JSON found" -ForegroundColor Red
    }
}

# Функция для запуска теста парсинга
function Run-Test {
    Write-Host "[3] Running JSON extraction test..." -ForegroundColor Green
    Write-Host ""
    
    docker-compose exec -T gpt python /app/gpt_integration/analysis/test_json_extraction.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Test failed" -ForegroundColor Red
        return
    }
    
    Write-Host ""
    Write-Host "=== Testing last response ===" -ForegroundColor Cyan
    docker-compose exec -T gpt sh -c "if [ -f /app/gpt_integration/analysis/debug/last_gpt_response.txt ]; then python /app/gpt_integration/analysis/test_json_extraction.py /app/gpt_integration/analysis/debug/last_gpt_response.txt; else echo 'File not found. Run AI analysis first.'; fi"
}

# Функция для показа конфигурации
function Show-Config {
    Write-Host "[0] Checking GPT configuration..." -ForegroundColor Green
    Write-Host ""
    
    Write-Host "=== GPT ENVIRONMENT ===" -ForegroundColor Cyan
    docker-compose exec -T gpt sh -c "env | grep OPENAI | sort"
    
    Write-Host ""
}

# Основная логика
if ($All -or (-not $Logs -and -not $Response -and -not $Test)) {
    # Запустить все проверки
    Show-Config
    Write-Host ""
    Show-Logs
    Write-Host ""
    Get-Response
    Write-Host ""
    Run-Test
} else {
    if ($Logs) { Show-Logs; Write-Host "" }
    if ($Response) { Get-Response; Write-Host "" }
    if ($Test) { Run-Test; Write-Host "" }
}

Write-Host ""
Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "  DONE!" -ForegroundColor Yellow
Write-Host "=" -ForegroundColor Cyan -NoNewline
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run AI analysis in the bot (🧠 AI-анализ)" -ForegroundColor White
Write-Host "2. If error occurs, run: .\debug_gpt.ps1" -ForegroundColor White
Write-Host "3. Check the output above for issues" -ForegroundColor White
Write-Host ""
Write-Host "For specific checks:" -ForegroundColor Yellow
Write-Host "  .\debug_gpt.ps1 -Logs      # Show only logs" -ForegroundColor White
Write-Host "  .\debug_gpt.ps1 -Response  # Copy and show last response" -ForegroundColor White
Write-Host "  .\debug_gpt.ps1 -Test      # Run parsing tests" -ForegroundColor White
Write-Host ""

