@echo off
setlocal enabledelayedexpansion
title AI Job Search Assistant - Windows Installer
echo =================================================================
echo   AI Job Search Assistant - Windows One-Command Setup
echo =================================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Setup encountered an issue. Code: %errorlevel%
    pause
)
