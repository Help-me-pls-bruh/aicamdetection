@echo off
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
echo     [0]  Exit this menu
echo.
echo  ------------------------------------------------------------
set "choice="
set /p "choice=  Type a number and press Enter:  "

if "%choice%"=="1" goto map
if "%choice%"=="2" goto camera
if "%choice%"=="3" goto both
if "%choice%"=="4" goto stop
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
start "SentinelAI Dashboard" cmd /k "streamlit run dashboard\dashboard.py --server.port 8501"
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
start "SentinelAI Dashboard" cmd /k "streamlit run dashboard\dashboard.py --server.port 8501"
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

:end
endlocal
exit
