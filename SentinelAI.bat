@echo off
setlocal enabledelayedexpansion
title SENTINEL AI - Command Center
cd /d "%~dp0"
mode con: cols=100 lines=42 >nul 2>&1

:menu
color 0B
cls
echo.
echo.
echo     ____  _____ _   _ _____ ___ _   _ _____ _          _    ___
echo    / ___^|^| ____^| \ ^| ^|_   _^|_ _^| \ ^| ^| ____^| ^|        / \  ^|_ _^|
echo    \___ \^|  _^| ^|  \^| ^| ^| ^|  ^| ^|^|  \^| ^|  _^| ^| ^|       / _ \  ^| ^|
echo     ___) ^| ^|___^| ^|\  ^| ^| ^|  ^| ^|^| ^|\  ^| ^|___^| ^|___   / ___ \ ^| ^|
echo    ^|____/^|_____^|_^| \_^| ^|_^| ^|___^|_^| \_^|_____^|_____^| /_/   \_\___^|
echo.
echo         CRIME PREVENTION ^& RESPONSE PLATFORM   ::   TEAM TECHNOSAPIENS
echo    ----------------------------------------------------------------------------
echo                          "  Smart-city  =  Safe-city  "
echo.
echo.
echo       +------------------------------------------------------------------+
echo       ^|                                                                  ^|
echo       ^|    [1]   LAUNCH RISK MAP      live KL hexagon map + incidents    ^|
echo       ^|                                                                  ^|
echo       ^|    [2]   LAUNCH WEBCAM        laptop webcam threat detection     ^|
echo       ^|                                                                  ^|
echo       ^|    [3]   LAUNCH CCTV CAMERA   TP-Link / RTSP IP camera           ^|
echo       ^|                                                                  ^|
echo       ^|    [4]   FULL SYSTEM DEMO     map + webcam together              ^|
echo       ^|                                                                  ^|
echo       ^|    [5]   SHUT DOWN            stop every running component       ^|
echo       ^|                                                                  ^|
echo       ^|    [6]   FIRST-TIME SETUP     install requirements (once)        ^|
echo       ^|                                                                  ^|
echo       ^|    [0]   EXIT                                                    ^|
echo       ^|                                                                  ^|
echo       +------------------------------------------------------------------+
echo.
set "choice="
set /p "choice=        >>  SELECT AN OPTION:  "

if "%choice%"=="1" goto map
if "%choice%"=="2" goto camera
if "%choice%"=="3" goto cctv
if "%choice%"=="4" goto both
if "%choice%"=="5" goto stop
if "%choice%"=="6" goto install
if "%choice%"=="0" goto end
echo.
echo        X   "%choice%" is not an option - try again.
timeout /t 2 >nul
goto menu

:: ============================ LAUNCH MAP ============================
:map
call :launchmap
pause
goto menu

:: =========================== LAUNCH WEBCAM ==========================
:camera
color 0A
cls
echo.
echo    ----------------------  WEBCAM  ----------------------
echo.
echo     ^>^>  Starting the laptop webcam...
start /min "SentinelAI Webcam" cmd /c "python test_camera.py || pause"
echo.
echo     OK  A camera window will appear in a few seconds.
echo.
echo         Inside the camera window:
echo            q  =  quit            a  =  knife all-angle mode
echo            or simply click the window's X to close the system
echo.
echo         First-ever run downloads the AI model, about 22 MB.
echo.
pause
goto menu

:: ========================= LAUNCH CCTV (RTSP) =======================
:cctv
color 0A
cls
echo.
echo    --------------------  CCTV  CAMERA  (RTSP)  --------------------
echo.
echo     This connects to a TP-Link Tapo / RTSP IP camera over the network.
echo.
echo     BEFORE it can connect, the camera's address must be set in the
echo     file  test_rtsp.py  (line with RTSP_URL), in this format:
echo         rtsp://USERNAME:PASSWORD@CAMERA_IP:554/stream2
echo.
echo     The camera and THIS laptop must be on the SAME Wi-Fi network.
echo     Tip: test the URL in VLC first to confirm it works.
echo.
echo     ^>^>  Starting the CCTV detector...
start /min "SentinelAI CCTV" cmd /c "python test_rtsp.py || pause"
echo.
echo     OK  A camera window will appear once it connects.
echo         q  =  quit          (if it can't connect, its window shows why)
echo.
pause
goto menu

:: ============================ FULL DEMO =============================
:both
start /min "SentinelAI Camera" cmd /c "python test_camera.py || pause"
call :launchmap
echo     OK  Camera is starting in its own window as well.
echo.
pause
goto menu

:: ============================ SHUT DOWN =============================
:stop
color 0C
cls
echo.
echo    ----------------------  SHUT  DOWN  ----------------------
echo.
echo     ^>^>  Stopping every SentinelAI component...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1
echo.
echo     OK  All systems stopped. Safe to close this window.
echo.
pause
goto menu

:: ========================= FIRST-TIME SETUP =========================
:install
color 0E
cls
echo.
echo    ------------------  FIRST-TIME  SETUP  ------------------
echo.
echo     This installs everything SentinelAI needs - one time only.
echo     Big download, 300-500 MB. Usually 5 to 15 minutes.
echo.
pause

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo     X   Python was not found on this computer.
    echo         Install it from  https://www.python.org/downloads/
    echo         and TICK "Add Python to PATH", then run this again.
    echo.
    pause
    goto menu
)

echo.
echo     ^>^>  Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

set "pkgs=flask flask-cors streamlit plotly pandas numpy scipy requests Pillow scikit-learn hdbscan statsmodels h3 opencv-python ultralytics supervision"

set /a total=0
for %%p in (%pkgs%) do set /a total+=1

echo     ^>^>  Installing %total% packages...
echo    -------------------------------------------------------

set /a count=0
set "start=%TIME%"

for %%p in (%pkgs%) do (
    set /a count+=1
    call :elapsed
    echo.
    echo     [ !count! / %total% ]   elapsed !mins!m !secs!s   installing %%p ...
    python -m pip install %%p >nul 2>&1
    if errorlevel 1 (
        echo          WARN  %%p had a problem - retrying once...
        python -m pip install %%p
    ) else (
        echo          OK    %%p ready
    )
)

call :elapsed
echo.
echo    =======================================================
echo       SETUP COMPLETE      total time: !mins!m !secs!s
echo    =======================================================
echo.
echo       Pick [1] map, [2] webcam, [3] CCTV, or [4] full demo to launch.
echo.
pause
goto menu

:end
endlocal
exit

:: --------------- subroutine: start map + wait until ready ---------------
:launchmap
color 0A
cls
echo.
echo    ----------------------  RISK  MAP  ----------------------
echo.
echo     ^>^>  Starting intelligence backend   - HDBSCAN, SARIMA, fusion
start /min "SentinelAI Backend" cmd /k "python run.py"
echo     ^>^>  Starting command dashboard      - Uber H3 hexagon grid
start /min "SentinelAI Dashboard" cmd /k "python -m streamlit run dashboard\dashboard.py --server.port 8501 --server.headless true"
echo.
echo     ^>^>  Waiting for the map to come online...
echo         Normally 15-60 seconds. The very first run trains the
echo         AI models and can take a few minutes.
echo.
set /a waited=0
:waitmap
set "code=000"
for /f %%c in ('curl -s -o NUL -w "%%{http_code}" http://localhost:8501 2^>NUL') do set "code=%%c"
if "%code%"=="200" goto mapready
set /a waited+=5
echo         ...  preparing systems - %waited%s elapsed
if %waited% GEQ 300 goto maptimeout
timeout /t 5 >nul
goto waitmap

:mapready
start "" http://localhost:8501
echo.
echo    =========================================================
echo       MAP IS LIVE - opening it in your browser now.
echo    =========================================================
echo.
echo        Address if you ever need it:   http://localhost:8501
echo        Two minimised windows in your taskbar keep it running.
echo.
goto :eof

:maptimeout
start "" http://localhost:8501
echo.
echo     WARN  Taking longer than usual - first-run model training.
echo           The browser is open. Just refresh the page in a minute.
echo.
goto :eof

:: --------------- subroutine: elapsed-time counter ---------------
:elapsed
set "now=%TIME%"
for /f "tokens=1-3 delims=:.," %%a in ("%start%") do set /a s0=(((%%a*60)+1%%b %% 100)*60)+1%%c %% 100
for /f "tokens=1-3 delims=:.," %%a in ("%now%")   do set /a s1=(((%%a*60)+1%%b %% 100)*60)+1%%c %% 100
set /a diff=s1-s0
if !diff! lss 0 set /a diff+=86400
set /a mins=diff/60
set /a secs=diff%%60
goto :eof
