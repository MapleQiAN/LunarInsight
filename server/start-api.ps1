# LunarInsight API startup script
# Usage: .\start-api.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LunarInsight API startup script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Virtual environment not found, creating..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Check if requirements are installed
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$requirementsInstalled = $true
try {
    python -c "import fastapi" 2>$null
    if ($LASTEXITCODE -ne 0) { $requirementsInstalled = $false }
} catch {
    $requirementsInstalled = $false
}

if (-not $requirementsInstalled) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    Write-Host "Dependencies installed" -ForegroundColor Green
}

# Ensure uploads directory exists
if (-not (Test-Path "uploads")) {
    Write-Host "Creating uploads directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "uploads" | Out-Null
    Write-Host "Uploads directory created" -ForegroundColor Green
}

# Ensure .env file exists
if (-not (Test-Path ".env")) {
    Write-Host ".env not found, creating default .env..." -ForegroundColor Yellow
    @"
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASS=test1234
REDIS_URL=redis://localhost:6379/0
UPLOAD_DIR=./uploads
OPENAI_API_KEY=
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host ".env created; please edit as needed" -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting API service..." -ForegroundColor Green
Write-Host "API address: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the service" -ForegroundColor Yellow
Write-Host ""

# Start service
uvicorn main:app --reload --host 0.0.0.0 --port 8000
