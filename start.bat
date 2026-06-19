@echo off
set "LOG=%~dp0start.log"

(
    echo ============================================
    echo  AI Trend Radar - Startup
    echo ============================================

    chcp 65001 >nul 2>&1
    setlocal EnableDelayedExpansion

    set "SCRIPT_DIR=%~dp0"
    set "SETUP_PY=%SCRIPT_DIR%setup.py"

    echo [INFO] SCRIPT_DIR=%SCRIPT_DIR%
    echo [INFO] SETUP_PY=%SETUP_PY%
    echo [INFO] Current directory=%cd%

    set "PY="
    if exist "%SCRIPT_DIR%.pyportable\python.exe" (
        set "PY=%SCRIPT_DIR%.pyportable\python.exe"
        echo [INFO] Found portable Python
        goto :run
    )

    where python >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] Found python command, checking version...
        python -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            set "PY=python"
            echo [INFO] Using system python
            goto :run
        ) else (
            echo [WARN] python version < 3.10
        )
    )

    where py >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] Found py launcher, checking version...
        py -3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            for /f "tokens=*" %%a in ('py -3 -c "import sys; print(sys.executable)"') do (
                set "PY=%%a"
                echo [INFO] py path=%%a
            )
            goto :run
        ) else (
            echo [WARN] py -3 version not match
        )
    )

    echo [INFO] Python 3.10+ not found. Downloading portable Python...
    echo [INFO] First run needs ~12MB download, please wait.

    set "PYDIR=%SCRIPT_DIR%.pyportable"
    set "PYURL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
    set "PYZIP=%PYDIR%\python-embed.zip"

    mkdir "%PYDIR%" 2>nul

    echo [1/3] Downloading Python...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PYURL%' -OutFile '%PYZIP%' -UseBasicParsing"
    if errorlevel 1 (
        echo [ERROR] Download failed. Please check network and retry.
        pause
        exit /b 1
    )

    echo [2/3] Extracting...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%PYZIP%' -DestinationPath '%PYDIR%' -Force"
    del "%PYZIP%" 2>nul

    for %%f in ("%PYDIR%\python*._pth") do (
        powershell -NoProfile -Command "(Get-Content '%%f') -replace '^#import site','import site' | Set-Content '%%f'"
    )

    echo [3/3] Configuring environment...
    set "PY=%PYDIR%\python.exe"

    :run
    echo [INFO] Ready to run: %PY% %SETUP_PY%
    if defined PY (
        cd /d "%SCRIPT_DIR%"
        "%PY%" "%SETUP_PY%"
    ) else (
        echo [ERROR] Failed to find or install Python.
        pause
        exit /b 1
    )

    echo [INFO] Exit code: %errorlevel%
    if errorlevel 1 (
        echo [ERROR] Startup failed. Check error messages above.
    )
    echo.
    echo Press any key to close...
    pause >nul
) >"%LOG%" 2>&1 & type "%LOG%"
