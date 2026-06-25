@echo off
setlocal EnableExtensions

set "ROOT=D:\ADMStoIQS"
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "LOGDIR=%ROOT%\data\logs"
set "LOGFILE=%LOGDIR%\orquestrador_agendador.log"

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set "ANOMES=%~1"
if "%ANOMES%"=="" (
    echo [ERRO] Informe a competencia no formato YYYYMM. Exemplo: rodar_orquestrador.bat 202605
    echo [ERRO] Informe a competencia no formato YYYYMM. Exemplo: rodar_orquestrador.bat 202605 >> "%LOGFILE%"
    exit /b 2
)

if not exist "%PYTHON%" (
    echo [ERRO] Python da venv nao encontrado: %PYTHON%
    echo [ERRO] Python da venv nao encontrado: %PYTHON% >> "%LOGFILE%"
    exit /b 3
)

cd /d "%ROOT%"

echo ============================================================ >> "%LOGFILE%"
echo [%date% %time%] Iniciando orquestrador ADMStoIQS - anomes=%ANOMES% >> "%LOGFILE%"
echo ROOT=%ROOT% >> "%LOGFILE%"
echo PYTHON=%PYTHON% >> "%LOGFILE%"

"%PYTHON%" -m backend.scripts.orquestrar_apuracao --anomes "%ANOMES%" >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"

echo [%date% %time%] Finalizado orquestrador ADMStoIQS - rc=%RC% >> "%LOGFILE%"

exit /b %RC%
