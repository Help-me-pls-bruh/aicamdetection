@echo off
setlocal enabledelayedexpansion
title SentinelAI Launcher
color 0B
cd /d "%~dp0"

:menu
cls
echo.
echo  ============================================================
echo                      S E N T I N E L   A I
echo                Crime Prevention ^& Response Platform
echo  ============================================================
echo.
echo     [1]  Open the MAP        (dashboard + backend)
echo.
echo     [2]  Open the CAMERA      (live CCTV detection)
echo.
echo     [3]  Open BOTH            (map + camera)
echo.
echo     [4]  STOP everything      (close all servers)
echo.
echo     [5]  INSTALL / SETUP      (run this once on a new laptop)
echo.
echo     [0]  Exit this menu
echo.
echo  ------------------------------------------------------------
set "choice="
set /p "choice=  Type a number and press Enter:  "

if "%choice%"=="1" goto map
if "%choice%"=="2" goto camera
if "%choice%"=="3" goto both
if "%choice%"=="4" goto stop
if "%choice%"=="5" goto install
if "%choice%"=="0" goto end
echo.
echo   "%choice%" is not an option. Try again.
timeout /t 2 >nul
goto menu

:map
echo.
echo   Starting the MAP...
echo   - Backend  (this trains the models; first run takes a few minutes)
start "SentinelAI Backend" cmd /k "python run.py"
echo   - Dashboard (the map window will open in your browser)
start "SentinelAI Dashboard" cmd /k "python -m streamlit run dashboard\dashboard.py --server.port 8501"
echo.
echo   Two black windows opened (Backend + Dashboard) - leave them running.
echo   The map opens at:  http://localhost:8501
echo.
echo   (If the browser doesn't open by itself, paste that link in.)
echo.
pause
goto menu

:camera
echo.
echo   Starting the CAMERA...
echo   A webcam window will open.  In that window:
echo      q = quit       a = toggle knife all-angle mode
start "SentinelAI Camera" cmd /k "python test_camera.py"
echo.
echo   (First time only: it downloads the YOLO model ~22 MB.)
echo.
pause
goto menu

:both
echo.
echo   Starting the MAP + the CAMERA...
start "SentinelAI Backend" cmd /k "python run.py"
start "SentinelAI Dashboard" cmd /k "python -m streamlit run dashboard\dashboard.py --server.port 8501"
start "SentinelAI Camera" cmd /k "python test_camera.py"
echo.
echo   Map:    http://localhost:8501
echo   Camera: opens in its own window
echo.
pause
goto menu

:stop
echo.
echo   Stopping all SentinelAI servers and camera...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1
echo   Done - everything is stopped.
echo.
pause
goto menu

:install
cls
echo.
echo  ============================================================
echo                 S E N T I N E L   A I   -   S E T U P
echo  ============================================================
echo.
echo   This installs everything the MAP and CAMERA need.
echo   It's a big download (~300-500 MB because of PyTorch),
echo   so it can take 5-15 minutes on the first run.
echo.
echo   You only need to do this ONCE per laptop.
echo.
pause

REM ---- check Python exists ----
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [X] Python was not found on this computer.
    echo       Install Python from https://www.python.org/downloads/
    echo       and TICK "Add Python to PATH" during install, then run this again.
    echo.
    pause
    goto menu
)

echo.
echo   Upgrading pip first...
python -m pip install --upgrade pip >nul 2>&1

REM ---- the package list ----
set "pkgs=flask flask-cors streamlit plotly pandas numpy scipy requests Pillow scikit-learn hdbscan statsmodels h3 opencv-python ultralytics supervision"

REM ---- count how many ----
set /a total=0
for %%p in (%pkgs%) do set /a total+=1

echo.
echo   Installing %total% packages...
echo  ------------------------------------------------------------

set /a count=0
set "start=%TIME%"

for %%p in (%pkgs%) do (
    set /a count+=1
    call :elapsed
    echo.
    echo   [ !count! / %total% ]  elapsed !mins!m !secs!s   ^>^>  installing %%p ...
    python -m pip install %%p >nul 2>&1
    if errorlevel 1 (
        echo        [!] %%p had a problem - retrying once...
        python -m pip install %%p
    ) else (
        echo        [ok] %%p done
    )
)

call :elapsed
echo.
echo  ============================================================
echo     ALL DONE.   Total time: !mins!m !secs!s
echo  ============================================================
echo.
echo   You can now pick [1], [2] or [3] from the menu to run it.
echo.
pause
goto menu

:end
endlocal
exit

REM ---------- elapsed-time helper ----------
:elapsed
set "now=%TIME%"
for /f "tokens=1-3 delims=:.," %%a in ("%start%") do set /a s0=(((%%a*60)+1%%b %% 100)*60)+1%%c %% 100
for /f "tokens=1-3 delims=:.," %%a in ("%now%")   do set /a s1=(((%%a*60)+1%%b %% 100)*60)+1%%c %% 100
set /a diff=s1-s0
if !diff! lss 0 set /a diff+=86400
set /a mins=diff/60
set /a secs=diff%%60
goto :eof
