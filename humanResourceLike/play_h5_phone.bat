@echo off
rem H5 版「手机试玩」：绑 0.0.0.0，窗口里会打印手机该访问的地址
rem 和 play_h5.bat 的区别只有一行 —— 那个绑 127.0.0.1，手机连不上
setlocal
cd /d "%~dp0"
python "%~dp0hrm_godot\tools\serve_web.py" --lan
if errorlevel 1 (
    echo.
    echo [ERROR] 起不来。检查上面那行报错，或手动：
    echo   cd hrm_godot\build\web ^&^& python -m http.server 8123 --bind 0.0.0.0
)

echo.
echo ------------------------------------------------------------
echo 上面那条 http 地址可以直接贴进浏览器打开。
echo 按任意键关闭这个窗口。
pause >nul
