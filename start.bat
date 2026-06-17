@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
title AI趋势雷达 - 启动器

:: ================================================================
::  AI趋势雷达 - 一键启动脚本
::  适用于: Windows 10 / 11 (需要 PowerShell)
::  用法:   双击 start.bat 即可
:: ================================================================

set "PROJECT_DIR=%~dp0"
set "PYDIR=%PROJECT_DIR%.pyportable"
set "PYTHON_VER=3.12"
set "PYTHON_ZIP=python-3.12.10-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.10/%PYTHON_ZIP%"
set "PIP_URL=https://bootstrap.pypa.io/get-pip.py"
set "MIN_PYTHON=310"

:: ── 检查项目文件 ────────────────────────────────────────────────
if not exist "%PROJECT_DIR%app.py" (
    echo.
    echo  [错误] 未找到 app.py，请确保 start.bat 位于 AI-Trend-Hub 项目目录下。
    echo.
    pause
    exit /b 1
)

:: ── 第1步: 检查 Python 环境 ────────────────────────────────────
set "PYTHON_EXE="

:: 1a: 检查便携 Python (之前安装的)
if exist "%PYDIR%\python.exe" (
    set "PYTHON_EXE=%PYDIR%\python.exe"
    goto :check_deps
)

:: 1b: 检查系统 Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    :: 验证版本 >= 3.10
    for /f "tokens=2 delims= " %%v in ('python -c "import sys; print(sys.version[:4])" 2^>nul') do set "SYS_PYVER=%%v"
    python -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
        echo.
        echo  [OK] 检测到系统 Python !SYS_PYVER!
        goto :check_deps
    )
)

:: 1c: 检查 py 启动器
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=py -3"
        echo.
        echo  [OK] 检测到 py 启动器
        goto :check_deps
    )
)

:: ── 第2步: 下载便携 Python ─────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║          未检测到 Python，正在自动安装运行环境...       ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

mkdir "%PYDIR%" 2>nul

echo  [1/4] 正在下载 Python %PYTHON_VER% 便携版...
echo         (约 12MB，请耐心等待)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYDIR%\%PYTHON_ZIP%' -UseBasicParsing; Write-Host 'OK' } catch { Write-Host \"FAIL: $_\"; exit 1 }"
if errorlevel 1 (
    echo.
    echo  [错误] Python 下载失败，请检查网络连接后重试。
    echo.
    pause
    exit /b 1
)
if not exist "%PYDIR%\%PYTHON_ZIP%" (
    echo  [错误] 下载文件不存在，请重试。
    pause
    exit /b 1
)
echo         下载完成!
echo.

:: ── 第3步: 解压 Python ─────────────────────────────────────────
echo  [2/4] 正在解压 Python...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Expand-Archive -Path '%PYDIR%\%PYTHON_ZIP%' -DestinationPath '%PYDIR%' -Force"
if errorlevel 1 (
    echo  [错误] Python 解压失败。
    pause
    exit /b 1
)
del "%PYDIR%\%PYTHON_ZIP%" 2>nul

:: 修改 ._pth 文件，启用 site-packages (pip 必需)
for %%f in ("%PYDIR%\python*._pth") do (
    powershell -NoProfile -Command ^
        "(Get-Content '%%f') -replace '^#import site','import site' | Set-Content '%%f'"
)
echo         解压完成!
echo.

:: ── 第4步: 安装 pip ────────────────────────────────────────────
echo  [3/4] 正在安装 pip 包管理器...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PIP_URL%' -OutFile '%PYDIR%\get-pip.py' -UseBasicParsing; Write-Host 'OK' } catch { Write-Host \"FAIL: $_\"; exit 1 }"
if errorlevel 1 (
    echo  [错误] pip 下载失败。
    pause
    exit /b 1
)
"%PYDIR%\python.exe" "%PYDIR%\get-pip.py" --no-warn-script-location >nul 2>&1
if errorlevel 1 (
    echo  [错误] pip 安装失败。
    pause
    exit /b 1
)
del "%PYDIR%\get-pip.py" 2>nul
echo         pip 安装完成!
echo.

set "PYTHON_EXE=%PYDIR%\python.exe"

:: ── 第5步: 安装依赖 ────────────────────────────────────────────
:check_deps
echo  [4/4] 正在检查并安装项目依赖...

:: 核心依赖: 通过 requirements.txt 安装
"%PYTHON_EXE%" -c "import flask; import sqlalchemy; import bs4; import lxml; import apscheduler; import readability" >nul 2>&1
if errorlevel 1 (
    echo         正在安装核心依赖 (首次运行需要几分钟)...
    if exist "%PROJECT_DIR%requirements.txt" (
        "%PYTHON_EXE%" -m pip install --quiet --no-warn-script-location -r "%PROJECT_DIR%requirements.txt"
    ) else (
        "%PYTHON_EXE%" -m pip install --quiet --no-warn-script-location ^
            flask flask-sqlalchemy beautifulsoup4 lxml requests apscheduler readability-lxml
    )
    if errorlevel 1 (
        echo  [警告] 部分依赖安装可能失败，尝试继续启动...
    )
)

:: 可选依赖: scrapling (较大，安装失败不影响核心功能)
"%PYTHON_EXE%" -c "import scrapling" >nul 2>&1
if errorlevel 1 (
    echo         正在安装 Scrapling (可选，较大，跳过不影响)...
    "%PYTHON_EXE%" -m pip install --quiet --no-warn-script-location scrapling 2>nul
    if errorlevel 1 (
        echo         [提示] Scrapling 跳过，将使用备用抓取引擎。
    )
)

echo         依赖检查完成!
echo.

:: ── 第6步: 启动服务器 ──────────────────────────────────────────
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                  AI趋势雷达 启动中...                    ║
echo  ╠══════════════════════════════════════════════════════════╣
echo  ║                                                          ║
echo  ║   本地访问:  http://127.0.0.1:5000                      ║
echo  ║   管理后台:  http://127.0.0.1:5000/admin                ║
echo  ║   账    号:  admin / admin123                            ║
echo  ║                                                          ║
echo  ║   关闭方式:  按 Ctrl+C 或直接关闭此窗口                  ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: 延迟2秒后自动打开浏览器
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5000"

:: 启动 Flask
cd /d "%PROJECT_DIR%"
"%PYTHON_EXE%" app.py

:: 如果 Flask 退出了
echo.
echo  [提示] 服务器已停止。
pause
