# LunarInsight API 启动脚本
# 使用方法: .\start-api.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LunarInsight API 启动脚本" -ForegroundColor Cyan
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
    python -c "import fastapi" 2>$null
    if ($LASTEXITCODE -ne 0) { $requirementsInstalled = $false }
} catch {
    $requirementsInstalled = $false
}

if (-not $requirementsInstalled) {
    Write-Host "📥 安装依赖包..." -ForegroundColor Yellow
    pip install -r requirements.txt
    Write-Host "✅ 依赖安装完成" -ForegroundColor Green
}

# 检查 uploads 目录
if (-not (Test-Path "uploads")) {
    Write-Host "📁 创建 uploads 目录..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "uploads" | Out-Null
    Write-Host "✅ uploads 目录创建完成" -ForegroundColor Green
}

# 检查 .env 文件
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env 文件不存在，创建默认配置..." -ForegroundColor Yellow
    @"
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASS=test
REDIS_URL=redis://localhost:6379/0
UPLOAD_DIR=./uploads
OPENAI_API_KEY=
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "✅ .env 文件已创建，请根据需要修改配置" -ForegroundColor Green
}

Write-Host ""
Write-Host "🚀 启动 API 服务..." -ForegroundColor Green
Write-Host "📍 API 地址: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📍 API 文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000

