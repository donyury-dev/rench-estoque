@echo off
title RENCH - Servidor de Estoque
cd /d "%~dp0rench_web"

REM Verifica se o Python existe no caminho esperado
if not exist "C:\Users\Kaio\AppData\Local\Programs\Python\Python312\python.exe" (
    echo ========================================
    echo ERRO: Python nao encontrado!
    echo ========================================
    echo Caminho esperado:
    echo C:\Users\Kaio\AppData\Local\Programs\Python\Python312\python.exe
    echo.
    pause
    exit /b 1
)

REM Mata qualquer servidor Python anterior na porta 5000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000') do (
    taskkill /PID %%a /F >NUL 2>&1
)
timeout /t 1 /nobreak >NUL

echo ========================================
echo  RENCH - Controle de Estoque
echo ========================================
echo.
echo Iniciando servidor web...
echo Acesse: http://localhost:5000
echo.
echo NAO FECHE ESTA JANELA!
echo Ela mantem o servidor ativo.
echo ========================================
echo.

"C:\Users\Kaio\AppData\Local\Programs\Python\Python312\python.exe" -c "import os; os.environ['FLASK_ENV']='production'; exec(open('app.py').read())"

echo.
echo Servidor encerrado.
pause
