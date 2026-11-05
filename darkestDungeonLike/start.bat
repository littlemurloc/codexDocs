@echo off
rem ---------------------------------------------------------------
rem DarkestLike launcher
rem   Double-click to play. Edit GODOT below if the path changes.
rem ---------------------------------------------------------------
setlocal

set "GODOT=D:\XT\godot\Godot_v4.7.2-stable_win64.exe"

if not exist "%GODOT%" (
  echo [ERROR] Godot not found at:
  echo         %GODOT%
  echo Edit GODOT in this file to point at your Godot 4 executable.
  pause
  exit /b 1
)

start "" "%GODOT%" --path "%~dp0."
exit /b 0
