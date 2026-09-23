@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Publicar ACPTO SANTANA - GitHub

set "PROJECT_DIR=%~dp0"
set "PYTHON_SCRIPT=%PROJECT_DIR%scripts\gerar_dados_dashboard.py"
set "EXCEL_FILE=%PROJECT_DIR%1 - Acpto de ordens - Santana.xlsx"
set "JSON_FILE=%PROJECT_DIR%data\ordens_santana.json.gz"
set "MANIFEST_FILE=%PROJECT_DIR%data\manifest.json"
set "INDEX_FILE=%PROJECT_DIR%index.html"

echo.
echo ============================================================
echo             PUBLICACAO ACPTO SANTANA
echo ============================================================
echo.
echo Projeto: %PROJECT_DIR%
echo.

echo [1/7] Validando Git...
where git >nul 2>&1
if errorlevel 1 goto :ERROR_GIT

git rev-parse --show-toplevel >nul 2>&1
if errorlevel 1 goto :ERROR_REPO

for /f "delims=" %%G in ('git remote get-url origin 2^>nul') do set "REMOTE_URL=%%G"
if not defined REMOTE_URL goto :ERROR_REMOTE

for /f "delims=" %%B in ('git branch --show-current 2^>nul') do set "CURRENT_BRANCH=%%B"
if /I not "!CURRENT_BRANCH!"=="master" goto :ERROR_BRANCH

echo Remote: !REMOTE_URL!
echo Branch: !CURRENT_BRANCH!

echo.
echo [2/7] Validando arquivos...
if not exist "%EXCEL_FILE%" goto :ERROR_EXCEL
if not exist "%PYTHON_SCRIPT%" goto :ERROR_SCRIPT
if not exist "%INDEX_FILE%" goto :ERROR_INDEX
if not exist "%PROJECT_DIR%data\" goto :ERROR_DATA
echo Arquivos principais encontrados.

echo.
echo [3/7] Gerando dados do dashboard...
python "%PYTHON_SCRIPT%"
if errorlevel 1 goto :ERROR_PYTHON

echo.
echo [4/7] Validando arquivos gerados...
if not exist "%JSON_FILE%" goto :ERROR_JSON
if not exist "%MANIFEST_FILE%" goto :ERROR_MANIFEST

for %%F in ("%JSON_FILE%") do set "JSON_SIZE=%%~zF"
for %%F in ("%MANIFEST_FILE%") do set "MANIFEST_SIZE=%%~zF"

if "!JSON_SIZE!"=="0" goto :ERROR_JSON_EMPTY
if "!MANIFEST_SIZE!"=="0" goto :ERROR_MANIFEST_EMPTY

echo JSON: !JSON_SIZE! bytes
echo Manifest: !MANIFEST_SIZE! bytes

echo.
echo [5/7] Verificando alteracoes...
git status --short

git status --porcelain | findstr /R /C:"." >nul
if errorlevel 1 (
    echo.
    echo Nenhuma alteracao detectada.
    goto :SUCCESS
)

echo.
echo [6/7] Criando commit...
git add .
if errorlevel 1 goto :ERROR_ADD

for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set "TODAY=%%a-%%b-%%c"
for /f "tokens=1-2 delims=:." %%a in ("%time%") do set "NOW=%%a-%%b"

set "COMMIT_MESSAGE=Atualizacao automatica ACPTO SANTANA - !TODAY! !NOW!"

git diff --cached --quiet
if errorlevel 1 (
    git commit -m "!COMMIT_MESSAGE!"
    if errorlevel 1 goto :ERROR_COMMIT
) else (
    echo Nenhuma alteracao para commit.
)

echo.
echo [7/7] Enviando para o GitHub...
git push origin master
if errorlevel 1 goto :ERROR_PUSH

:SUCCESS
echo.
echo ============================================================
echo          PUBLICACAO CONCLUIDA COM SUCESSO
echo ============================================================
echo.
echo Repositorio:
echo https://github.com/scremhellomy-netizen/acpto-santana
echo.
echo Dashboard:
echo https://scremhellomy-netizen.github.io/acpto-santana/
echo.
echo ============================================================
echo.
pause
exit /b 0

:ERROR_GIT
echo ERRO: Git nao foi encontrado no PATH.
goto :ERROR

:ERROR_REPO
echo ERRO: A pasta nao e um repositorio Git.
goto :ERROR

:ERROR_REMOTE
echo ERRO: O remote "origin" nao esta configurado.
goto :ERROR

:ERROR_BRANCH
echo ERRO: A branch atual nao e "master".
goto :ERROR

:ERROR_EXCEL
echo ERRO: Excel nao encontrado: %EXCEL_FILE%
goto :ERROR

:ERROR_SCRIPT
echo ERRO: Script Python nao encontrado: %PYTHON_SCRIPT%
goto :ERROR

:ERROR_INDEX
echo ERRO: index.html nao encontrado.
goto :ERROR

:ERROR_DATA
echo ERRO: Pasta data nao encontrada.
goto :ERROR

:ERROR_PYTHON
echo ERRO: A geracao dos dados falhou. O Git nao sera publicado.
goto :ERROR

:ERROR_JSON
echo ERRO: ordens_santana.json.gz nao foi gerado.
goto :ERROR

:ERROR_MANIFEST
echo ERRO: manifest.json nao foi gerado.
goto :ERROR

:ERROR_JSON_EMPTY
echo ERRO: ordens_santana.json.gz esta vazio.
goto :ERROR

:ERROR_MANIFEST_EMPTY
echo ERRO: manifest.json esta vazio.
goto :ERROR

:ERROR_ADD
echo ERRO: git add falhou.
goto :ERROR

:ERROR_COMMIT
echo ERRO: git commit falhou.
goto :ERROR

:ERROR_PUSH
echo ERRO: git push falhou.
goto :ERROR

:ERROR
echo.
echo ============================================================
echo             PUBLICACAO NAO CONCLUIDA
echo ============================================================
echo.
echo Corrija o problema indicado acima e execute novamente.
echo.
pause
exit /b 1
