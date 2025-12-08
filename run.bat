@echo off
echo ======================================================
echo  STARTING ACCIDENT RISK ADVISOR
echo  Using Python 3.11 (The one with Flask installed)
echo ======================================================

REM 1. Define the path to the "Good" Python
SET PYTHON_PATH="C:\Users\anilc\AppData\Local\Programs\Python\Python311\python.exe"

REM 2. Install requirements (Quietly, just to be safe)
echo Checking libraries...
%PYTHON_PATH% -m pip install flask flask-cors osmnx networkx scikit-learn scipy

REM 3. Run the App
echo.
echo Starting Server...
%PYTHON_PATH% app.py

pause