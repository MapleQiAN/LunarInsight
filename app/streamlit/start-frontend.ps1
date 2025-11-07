# LunarInsight Frontend 启动脚本
# 使用方法: .\start-frontend.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LunarInsight Frontend 启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查虚拟环境是否存在
if (-not (Test-Path "venv")) {
    Write-Host "❌ 虚拟环境不存在，正在创建..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "✅ 虚拟环境创建完成" -ForegroundColor Green
}

# 激活虚拟环境
Write-Host "🔧 激活虚拟环境..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# 检查依赖是否安装
Write-Host "📦 检查依赖..." -ForegroundColor Yellow
$requirementsInstalled = $true
try {
    python -c "import streamlit" 2>$null
    if ($LASTEXITCODE -ne 0) { $requirementsInstalled = $false }
} catch {
    $requirementsInstalled = $false
}

if (-not $requirementsInstalled) {
    Write-Host "📥 安装依赖包..." -ForegroundColor Yellow
    pip install -r requirements.txt
    Write-Host "✅ 依赖安装完成" -ForegroundColor Green
}

# 设置环境变量
$env:API_BASE = "http://localhost:8000"
Write-Host "🔧 设置 API_BASE=http://localhost:8000" -ForegroundColor Yellow

Write-Host ""
Write-Host "🚀 启动前端服务..." -ForegroundColor Green
Write-Host "📍 前端地址: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 启动服务
streamlit run app.py

