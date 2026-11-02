@echo off
chcp 65001 >nul
title 打包 exe
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 请先创建虚拟环境并安装依赖
    pause
    exit /b 1
)

set PY=.venv\Scripts\python.exe
%PY% -m pip install -q pyinstaller -i https://mirrors.aliyun.com/pypi/simple/

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

%PY% -m PyInstaller --noconfirm --clean --onedir --windowed ^
  --name "云枢后台管理" ^
  --collect-all nicegui ^
  --collect-submodules uvicorn ^
  --hidden-import sqlalchemy.dialects.sqlite ^
  main.py

echo.
echo 打包完成：dist\云枢后台管理\云枢后台管理.exe
echo 把整个 dist\云枢后台管理 文件夹发给客户即可（data 目录会自动生成在 exe 旁边）
pause
