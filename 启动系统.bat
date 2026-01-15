@echo off
chcp 65001 >nul
echo ======================================
echo   国际法知识图谱系统
echo   International Law Knowledge Graph
echo ======================================
echo.
echo 正在启动系统...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 检查依赖是否安装
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [成功] 依赖检查完成
echo.
echo 启动Web服务...
echo 浏览器将自动打开，如未打开请访问: http://localhost:8501
echo.
echo 按 Ctrl+C 可停止服务
echo ======================================
echo.

streamlit run gjf_graph_main.py

pause
