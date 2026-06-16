@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_env.ps1" %*
exit /b %ERRORLEVEL%
