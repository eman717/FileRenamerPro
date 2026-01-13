@echo off
title File Renamer Pro
echo ========================================
echo    File Renamer Pro - Artwork Tool
echo ========================================
echo.
cd /d "%~dp0"
python file_renamer_pro.py
if errorlevel 1 (
    echo.
    echo Error running the application.
    echo Make sure Python is installed and in your PATH.
    pause
)
