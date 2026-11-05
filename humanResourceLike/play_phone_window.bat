@echo off
rem 手机模拟窗口：不用按 F12，直接开一个竖屏带触摸的窗口看移动版
rem 前提：先双击 play_h5.bat 或 play_h5_phone.bat 把服务起起来
rem 端口不用管，脚本会自己在 8123-8130 里找
setlocal
cd /d "%~dp0"
python "%~dp0hrm_godot\tools\phone_preview.py"
if errorlevel 1 pause
