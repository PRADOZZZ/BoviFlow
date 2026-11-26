@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0publicar-github.ps1"
if errorlevel 1 echo Publicacao nao concluida. Confira a mensagem acima.
pause
