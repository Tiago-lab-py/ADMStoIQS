@echo off
setlocal EnableExtensions

set "ROOT=D:\ADMStoIQS"
set "TAREFA=ADMStoIQS Orquestrador Diario"
set "BAT=%ROOT%\rodar_orquestrador.bat"

set "ANOMES=%~1"
if "%ANOMES%"=="" (
    echo [ERRO] Informe a competencia no formato YYYYMM. Exemplo: criar_tarefa_orquestrador.bat 202605
    exit /b 2
)

set "HORARIO=%~2"
if "%HORARIO%"=="" set "HORARIO=06:00"

if not exist "%BAT%" (
    echo [ERRO] Arquivo nao encontrado: %BAT%
    exit /b 3
)

echo Criando/atualizando tarefa "%TAREFA%" para %HORARIO% com anomes=%ANOMES%...

schtasks /Create ^
  /TN "%TAREFA%" ^
  /TR "\"%BAT%\" %ANOMES%" ^
  /SC DAILY ^
  /ST %HORARIO% ^
  /F

if errorlevel 1 (
    echo [ERRO] Falha ao criar tarefa. Tente executar este CMD como Administrador.
    exit /b 1
)

echo Tarefa criada com sucesso.
echo Para testar agora:
echo schtasks /Run /TN "%TAREFA%"
