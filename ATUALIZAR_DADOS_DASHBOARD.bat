@echo off
setlocal
cd /d "%~dp0"
title Atualizar dados - Dashboard de Acompanhamento de Pedidos

echo.
echo ================================================
echo   ATUALIZACAO DO DASHBOARD DE ACOMPANHAMENTO
echo ================================================
echo.

if not exist "data" mkdir "data"

where py >nul 2>nul
if %errorlevel%==0 (set "PYTHON=py") else (set "PYTHON=python")

if "%~1"=="" (
    echo Procurando automaticamente o Excel operacional mais recente...
    %PYTHON% "scripts\gerar_dados_dashboard.py"
) else (
    echo Processando o arquivo:
    echo %~1
    %PYTHON% "scripts\gerar_dados_dashboard.py" "%~1"
)

echo.
if %errorlevel%==0 (
    echo ================================================
    echo   DADOS ATUALIZADOS COM SUCESSO
    echo ================================================
) else (
    echo ================================================
    echo   FALHA NA ATUALIZACAO
    echo ================================================
)
echo.
pause
endlocal
