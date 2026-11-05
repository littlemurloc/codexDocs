@echo off
setlocal
set GODOT=D:\XT\godot\Godot_v4.7.2-stable_win64.exe
if not exist "%GODOT%" (
    echo [ERROR] Godot not found: %GODOT%
    pause
    exit /b 1
)
start "" "%GODOT%" --path "%~dp0hrm_godot"
