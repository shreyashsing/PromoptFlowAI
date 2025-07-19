@echo off
REM Quick activation script for the virtual environment

echo Activating PromptFlow AI virtual environment...
call venv\Scripts\activate.bat

echo.
echo 🚀 Virtual environment activated!
echo.
echo Available commands:
echo   python scripts/init_db.py          - Initialize database
echo   uvicorn app.main:app --reload      - Start development server
echo   python tests/test_basic.py         - Run basic tests
echo.
echo To deactivate, type: deactivate
echo.