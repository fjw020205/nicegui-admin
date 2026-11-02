@echo off
chcp 65001 >nul
title 云枢后台管理 - 开发模式
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    echo [提示] 未找到虚拟环境，使用系统 Python
    python main.py
)

if errorlevel 1 pause
