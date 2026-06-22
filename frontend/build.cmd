@echo off
setlocal
set "PATH=%~dp0..\tools\nodejs;%PATH%"
call "%~dp0..\tools\nodejs\npm.cmd" run build
endlocal

