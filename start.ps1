<#
.SYNOPSIS
    Music Agent 一键启动脚本
.DESCRIPTION
    自动检测 Python 环境，安装依赖，构建前端，启动应用。
    跨设备可迁移：只需复制整个目录，在新设备上运行此脚本即可。
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Music Agent - AI 编曲工作站" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Find Python - try multiple strategies
$Python = $null
$SitePackages = $null

# Strategy 1: project-local .venv
if (Test-Path "$Root\.venv\Scripts\python.exe") {
    $Python = "$Root\.venv\Scripts\python.exe"
    $SitePackages = "$Root\.venv\Lib\site-packages"
    Write-Host "[OK] Using project venv: $Python" -ForegroundColor Green
}

# Strategy 2: venv pyvenv.cfg -> base Python + venv site-packages
if (-not $Python -or -not (Test-Path $Python)) {
    # Look for any nearby venv with site-packages
    $candidates = @(
        "$Root\.venv",
        "$Root\..\jieshi10\.venv",
        "$Root\..\.venv"
    )
    foreach ($v in $candidates) {
        $cfg = Join-Path $v "pyvenv.cfg"
        $sp = Join-Path $v "Lib\site-packages"
        if ((Test-Path $cfg) -and (Test-Path $sp)) {
            # Extract base Python from pyvenv.cfg
            $home = (Get-Content $cfg | Where-Object { $_ -match '^home\s*=' }) -replace 'home\s*=\s*', ''
            $basePy = Join-Path $home.Trim() "python.exe"
            if (Test-Path $basePy) {
                $Python = $basePy
                $SitePackages = $sp
                Write-Host "[OK] Using base Python: $Python" -ForegroundColor Green
                Write-Host "     with site-packages: $SitePackages" -ForegroundColor Green
                break
            }
        }
    }
}

# Strategy 3: system Python
if (-not $Python) {
    $Python = "python"
    Write-Host "[OK] Using system Python" -ForegroundColor Green
}

# 2. Create venv if needed (only for strategy 3)
if ($Python -eq "python" -and -not (Test-Path "$Root\.venv")) {
    Write-Host "[..] Creating virtual environment..." -ForegroundColor Yellow
    & $Python -m venv "$Root\.venv"
    $SitePackages = "$Root\.venv\Lib\site-packages"
    Write-Host "[OK] venv created" -ForegroundColor Green
}

# 3. Install Python dependencies
Write-Host "[..] Installing Python dependencies..." -ForegroundColor Yellow
if ($SitePackages) {
    & $Python -m pip install --target="$SitePackages" -r "$Root\requirements.txt" --quiet 2>&1 | Out-Null
} else {
    & $Python -m pip install -r "$Root\requirements.txt" --quiet 2>&1 | Out-Null
}
Write-Host "[OK] Python deps installed" -ForegroundColor Green

# 4. Install Node dependencies & build frontend
if (Get-Command npm -ErrorAction SilentlyContinue) {
    if (-not (Test-Path "$Root\node_modules")) {
        Write-Host "[..] Installing Node dependencies..." -ForegroundColor Yellow
        Set-Location $Root
        & npm install --silent 2>&1 | Out-Null
    }
    Write-Host "[..] Building frontend..." -ForegroundColor Yellow
    Set-Location $Root
    & npm run build --silent 2>&1 | Out-Null
    Write-Host "[OK] Frontend built" -ForegroundColor Green
} else {
    Write-Host "[WARN] npm not found. Using pre-built frontend." -ForegroundColor Yellow
}

# 5. Check .env
if (-not (Test-Path "$Root\.env")) {
    if (Test-Path "$Root\.env.example") {
        Copy-Item "$Root\.env.example" "$Root\.env"
        Write-Host "[WARN] Created .env from example. Please edit it with your API Key." -ForegroundColor Yellow
    }
}

# 6. Launch
Write-Host ""
Write-Host "[>>] Starting Music Agent..." -ForegroundColor Green
Set-Location $Root
& $Python "$Root\launch_window.py"
