@echo off
cd /d "C:\Users\Kaio\.verdent\verdent-projects\agora-como-um-novo\rench_web"
start /B "" "C:\Users\Kaio\AppData\Local\Programs\Python\Python312\python.exe" "app.py" >nul 2>nul
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5000"
