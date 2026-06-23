@echo off
title RENCH Estoque - Abrir Sistema
cd /d "%~dp0"
start "RENCH Estoque - Servidor" /min cmd /c "C:\Users\Kaio\AppData\Local\Programs\Python\Python312\python.exe app.py"
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5000"
exit