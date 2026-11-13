@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_windows.ps1"
if errorlevel 1 (
  echo Nao foi possivel concluir a instalacao. Confira a mensagem acima.
)
pause
