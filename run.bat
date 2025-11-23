@echo off
echo ========================================
echo    Face Attendance System - Setup
echo ========================================
echo.

echo Checking Python installation...
"C:/Users/raves/AppData/Local/Programs/Python/Python311/python.exe" --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Creating virtual environment...
"C:/Users/raves/AppData/Local/Programs/Python/Python311/python.exe" -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing dependencies...
python -m pip install -r requirements.txt

echo Starting application...
echo.
echo Access the application at: http://localhost:5000
echo.
echo Demo Accounts:
echo - Instructor: professor / password
echo - Student: student1 / password
echo.
python main.py

pause