@echo off
rem 出一版 Android 包：文件名自带「编号 + 日期」，旧包自动删掉
rem 产物在仓库根目录：sheep-counter-v<编号>-<日期>.apk
rem 可选参数：--no-bump（不递增编号，同版重出） --note=xxx（追加短标签）
setlocal
python "%~dp0hrm_godot\tools\export_apk.py" %*
if errorlevel 1 pause
