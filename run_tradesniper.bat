@echo off
echo Starting TradeSniper in virtual environment...
cd /d "%~dp0"

if exist .venv312\Scripts\python.exe (
    set PY_EXE=.venv312\Scripts\python.exe
) else (
    set PY_EXE=.venv\Scripts\python.exe
)

set USE_LOCAL_BROWSER_ONLY=1
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set ENGINE_RESTART_DELAY=20
set PATROL_SLEEP_MIN=20
set PATROL_SLEEP_MAX=45
set PATROL_PAUSE_FILE=patrol.pause

%PY_EXE% -u trade_engine.py
pause
