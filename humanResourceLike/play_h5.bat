@echo off
rem H5 版试玩：起本机静态服务器 + 自动开浏览器
rem 注意：不能双击 index.html —— wasm 在 file:// 下会被浏览器拦，一定白屏
rem 端口由 tools\serve_web.py 从 8123 往上自动挑
setlocal
cd /d "%~dp0"
python "%~dp0hrm_godot\tools\serve_web.py"
if errorlevel 1 (
    echo.
    echo [ERROR] 起不来。检查上面那行报错，或直接手动：
    echo   cd hrm_godot\build\web ^&^& python -m http.server 8123
)

echo.
echo ------------------------------------------------------------
echo 上面那条 http 地址可以直接贴进浏览器打开。
echo 按任意键关闭这个窗口。
pause >nul
