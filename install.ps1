# =============================================================================
# AI Job Search Assistant - One-Command Windows Installer & Setup Script
# =============================================================================
# Run in PowerShell:
#   powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/hellstumy/aijobclean/main/install.ps1 | iex"
# Or locally:
#   .\install.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  🚀 AI Job Search Assistant — Windows Installer & Onboarding" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check if running from cloned repository or web piped
$repoUrl = "https://github.com/hellstumy/aijobclean.git"
$folderName = "aijobclean"

if (-not (Test-Path "setup_wizard.py") -and -not (Test-Path "app.py")) {
    Write-Host "[1/5] Проект запускается через Web-загрузчик..." -ForegroundColor Yellow
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Host "      Клонирование репозитория: $repoUrl" -ForegroundColor Gray
        git clone $repoUrl $folderName
        Set-Location $folderName
    } else {
        Write-Host "      Git не обнаружен. Скачиваем ZIP-архив репозитория..." -ForegroundColor Gray
        $zipUrl = "https://github.com/hellstumy/aijobclean/archive/refs/heads/main.zip"
        $zipFile = "aijobclean.zip"
        Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile
        Expand-Archive -Path $zipFile -DestinationPath "." -Force
        Remove-Item $zipFile
        if (Test-Path "aijobclean-main") {
            Set-Location "aijobclean-main"
        }
    }
} else {
    Write-Host "[1/5] Обнаружена локальная папка проекта: $(Get-Location)" -ForegroundColor Green
}

# 2. Check Python installation
Write-Host "[2/5] Проверка Python 3..." -ForegroundColor Yellow
$pyCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pyCmd = "py"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pyCmd = "python3"
}

if (-not $pyCmd) {
    Write-Host "      ⚠️ Python не найден в системе!" -ForegroundColor Red
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "      Установка Python 3.12 через Windows Package Manager (winget)..." -ForegroundColor Yellow
        winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        $pyCmd = "python"
    } else {
        Write-Host "      Пожалуйста, скачайте и установите Python 3 с официального сайта: https://www.python.org/downloads/" -ForegroundColor Red
        Write-Host "      (Не забудьте поставить галочку 'Add Python to PATH' при установке!)" -ForegroundColor Red
        exit 1
    }
}

$pyVersion = & $pyCmd --version 2>&1
Write-Host "      Обнаружен: $pyVersion" -ForegroundColor Green

# 3. Create Virtual Environment
Write-Host "[3/5] Подготовка виртуального окружения (venv)..." -ForegroundColor Yellow
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "      Создание venv..." -ForegroundColor Gray
    & $pyCmd -m venv venv
}
$venvPy = ".\venv\Scripts\python.exe"
Write-Host "      Виртуальное окружение готово: $venvPy" -ForegroundColor Green

# 4. Install Dependencies
Write-Host "[4/5] Установка зависимостей проекта..." -ForegroundColor Yellow
& $venvPy -m pip install --upgrade pip --quiet
if (Test-Path "requirements.txt") {
    & $venvPy -m pip install -r requirements.txt --quiet
    Write-Host "      Зависимости успешно установлены." -ForegroundColor Green
}

# 5. Run Onboarding Setup Wizard
Write-Host "[5/5] Запуск мастера настройки профиля..." -ForegroundColor Yellow
Write-Host ""
& $venvPy setup_wizard.py

# 6. Start the Web UI
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  ✨ Запуск Web UI интерфейса..." -ForegroundColor Cyan
Write-Host "  Откройте браузер по адресу: http://localhost:5000" -ForegroundColor Green
Write-Host "  (Для остановки нажмите Ctrl+C)" -ForegroundColor Gray
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

& $venvPy app.py
