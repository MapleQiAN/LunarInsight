# PowerShell script to start Vue frontend
Write-Host "Starting LunarInsight Vue Frontend..." -ForegroundColor Green

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
}

# Start dev server
Write-Host "Starting development server on http://localhost:3000" -ForegroundColor Cyan
npm run dev

