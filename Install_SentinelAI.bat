@echo off
setlocal enabledelayedexpansion
title SentinelAI Installer
color 0E
cd /d "%~dp0"

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
    exit /b
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
echo   Next step:  double-click  SentinelAI.bat  to open the
echo   map or the camera.
echo.
pause
exit /b

REM ---------- elapsed-time helper ----------
:elapsed
set "now=%TIME%"
REM strip to seconds since midnight for start and now
for /f "tokens=1-3 delims=:.," %%a in ("%start%") do set /a s0=(((%%a*60)+1%%b %% 100)*60)+1%%c %% 100
for /f "tokens=1-3 delims=:.," %%a in ("%now%")   do set /a s1=(((%%a*60)+1%%b %% 100)*60)+1%%c %% 100
set /a diff=s1-s0
if !diff! lss 0 set /a diff+=86400
set /a mins=diff/60
set /a secs=diff%%60
goto :eof
