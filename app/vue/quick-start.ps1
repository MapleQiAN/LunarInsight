# LunarInsight Vue 前端快速启动脚本
# Quick Start Script for LunarInsight Vue Frontend

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  LunarInsight Vue 前端快速启动" -ForegroundColor Cyan
Write-Host "  Quick Start for Vue Frontend" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Node.js
Write-Host "[1/4] 检查 Node.js..." -ForegroundColor Yellow
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVersion = node --version
    Write-Host "✓ Node.js 已安装: $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "✗ 未检测到 Node.js，请先安装 Node.js" -ForegroundColor Red
    Write-Host "下载地址: https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}

# 检查包管理器
Write-Host ""
Write-Host "[2/4] 检查包管理器..." -ForegroundColor Yellow
$packageManager = ""
if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    $packageManager = "pnpm"
    Write-Host "✓ 使用 pnpm" -ForegroundColor Green
} elseif (Get-Command npm -ErrorAction SilentlyContinue) {
    $packageManager = "npm"
    Write-Host "✓ 使用 npm" -ForegroundColor Green
} else {
    Write-Host "✗ 未检测到包管理器" -ForegroundColor Red
    exit 1
}

# 安装依赖
Write-Host ""
Write-Host "[3/4] 安装依赖..." -ForegroundColor Yellow
if (Test-Path "node_modules") {
    Write-Host "node_modules 已存在，跳过安装" -ForegroundColor Gray
    $install = Read-Host "是否重新安装？(y/N)"
    if ($install -eq "y" -or $install -eq "Y") {
        Write-Host "重新安装依赖..." -ForegroundColor Yellow
        & $packageManager install
    }
} else {
    Write-Host "正在安装依赖，这可能需要几分钟..." -ForegroundColor Yellow
    & $packageManager install
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ 依赖安装失败" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 依赖安装成功" -ForegroundColor Green

# 启动开发服务器
Write-Host ""
Write-Host "[4/4] 启动开发服务器..." -ForegroundColor Yellow
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  🚀 准备启动..." -ForegroundColor Cyan
Write-Host "  访问地址: http://localhost:3000" -ForegroundColor Cyan
Write-Host "  按 Ctrl+C 停止服务器" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

Start-Sleep -Seconds 2

& $packageManager run dev

