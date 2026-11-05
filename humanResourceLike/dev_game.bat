@echo off
rem 开发用：直接跑工程目录（不导出），控制台会打印 push_error / print / 脚本解析错误
rem 改完代码保存 -> 关掉这个窗口重新双击，2 秒就能看到改动
setlocal
set GODOT=D:\XT\godot\Godot_v4.7.2-stable_win64_console.exe
if not exist "%GODOT%" (
    echo [ERROR] Godot not found: %GODOT%
    pause
    exit /b 1
)
"%GODOT%" --path "%~dp0hrm_godot"
if errorlevel 1 pause
