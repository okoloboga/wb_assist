# Smoke Test Script for GPT Integration Service
# Проверяет все критичные эндпоинты после слияния AI Chat

param(
    [string]$BaseUrl = "http://localhost:9000",
    [string]$ApiKey = $env:API_SECRET_KEY
)

Write-Host "🧪 Starting Smoke Test for GPT Integration Service" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl" -ForegroundColor Gray
Write-Host ""

$headers = @{
    "X-API-KEY" = $ApiKey
    "Content-Type" = "application/json"
}

$testsPassed = 0
$testsFailed = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers = @{},
        [string]$Body = $null
    )
    
    Write-Host "Testing: $Name" -NoNewline
    
    try {
        $params = @{
            Method = $Method
            Uri = $Url
            Headers = $Headers
            ErrorAction = "Stop"
        }
        
        if ($Body) {
            $params.Body = $Body
        }
        
        $response = Invoke-RestMethod @params
        Write-Host " ✅ PASSED" -ForegroundColor Green
        $script:testsPassed++
        return $true
    }
    catch {
        Write-Host " ❌ FAILED" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        $script:testsFailed++
        return $false
    }
}

# Test 1: Health Check
Write-Host "`n📋 General Endpoints" -ForegroundColor Yellow
Test-Endpoint -Name "Health Check" -Method "GET" -Url "$BaseUrl/health"

# Test 2: AI Chat Endpoints
Write-Host "`n💬 AI Chat Endpoints" -ForegroundColor Yellow

Test-Endpoint `
    -Name "Get Chat Limits" `
    -Method "GET" `
    -Url "$BaseUrl/v1/chat/limits/123456789" `
    -Headers $headers

$chatBody = @{
    telegram_id = 123456789
    message = "Привет! Это тестовое сообщение."
} | ConvertTo-Json

Test-Endpoint `
    -Name "Send Chat Message" `
    -Method "POST" `
    -Url "$BaseUrl/v1/chat/send" `
    -Headers $headers `
    -Body $chatBody

$historyBody = @{
    telegram_id = 123456789
    limit = 5
    offset = 0
} | ConvertTo-Json

Test-Endpoint `
    -Name "Get Chat History" `
    -Method "POST" `
    -Url "$BaseUrl/v1/chat/history" `
    -Headers $headers `
    -Body $historyBody

Test-Endpoint `
    -Name "Get Chat Stats" `
    -Method "GET" `
    -Url "$BaseUrl/v1/chat/stats/123456789?days=7" `
    -Headers $headers

# Test 3: Analysis Endpoints
Write-Host "`n📊 Analysis Endpoints" -ForegroundColor Yellow

$analysisBody = @{
    telegram_id = 123456789
    period = "7d"
    validate_output = $true
} | ConvertTo-Json

Test-Endpoint `
    -Name "Start Analysis" `
    -Method "POST" `
    -Url "$BaseUrl/v1/analysis/start" `
    -Headers $headers `
    -Body $analysisBody

# Summary
Write-Host "`n" + "="*50 -ForegroundColor Cyan
Write-Host "📊 Test Summary" -ForegroundColor Cyan
Write-Host "="*50 -ForegroundColor Cyan
Write-Host "Passed: $testsPassed" -ForegroundColor Green
Write-Host "Failed: $testsFailed" -ForegroundColor Red
Write-Host "Total:  $($testsPassed + $testsFailed)" -ForegroundColor Gray

if ($testsFailed -eq 0) {
    Write-Host "`n✅ All tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n❌ Some tests failed. Please check the logs." -ForegroundColor Red
    exit 1
}
