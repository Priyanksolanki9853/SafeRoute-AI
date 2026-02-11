@echo off
echo Starting SafeRoute AI...

SET GROQ_API_KEY=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
SET PYTHON_PATH="C:\Users\anilc\AppData\Local\Programs\Python\Python311\python.exe"

start "Backend" cmd /k "%PYTHON_PATH% app.py"
timeout /t 3 /nobreak >nul
start "Frontend" cmd /k "%PYTHON_PATH% -m http.server 8000"

echo.
echo Backend: http://localhost:5000
echo Frontend: http://localhost:8000
echo.
pause