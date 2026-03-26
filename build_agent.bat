@echo off
REM Genera dist\RestBarSyncAgent\RestBarSyncAgent.exe (Windows)
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo Crear venv e instalar: pip install -r requirements-agent-build.txt
  exit /b 1
)
call venv\Scripts\activate.bat
pip install -q -r requirements-agent-build.txt
pyinstaller --noconfirm --clean agent_sync.spec
echo Listo: dist\RestBarSyncAgent\RestBarSyncAgent.exe
pause
