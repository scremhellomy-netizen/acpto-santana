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

echo [1/8] Validando Git e repositorio...
where git >nul 2>&1
if errorlevel 1 goto :ERROR_GIT

git rev-parse --show-toplevel >nul 2>&1
if errorlevel 1 goto :ERROR_REPO

for /f "delims=" %%G in ('git remote get-url origin 2^>nul') do set "REMOTE_URL=%%G"
if not defined REMOTE_URL goto :ERROR_REMOTE

for /f "delims=" %%B in ('git branch --show-current 2^>nul') do set "CURRENT_BRANCH=%%B"
if /I not "!CURRENT_BRANCH!"=="master" goto :ERROR_BRANCH

for /f "delims=" %%R in ('git rev-parse --show-toplevel 2^>nul') do set "GIT_ROOT=%%R"
for /f "delims=\" %%P in ("%PROJECT_DIR:~0,-1%") do set "PROJECT_ROOT=%%P"

echo Remote: !REMOTE_URL!
echo Branch: !CURRENT_BRANCH!
echo.

echo [2/8] Validando arquivos...
if not exist "%EXCEL_FILE%" goto :ERROR_EXCEL
if not exist "%PYTHON_SCRIPT%" goto :ERROR_SCRIPT
if not exist "%INDEX_FILE%" goto :ERROR_INDEX
if not exist "%PROJECT_DIR%data\" goto :ERROR_DATA

echo Arquivos principais encontrados.
echo.

echo [3/8] Gerando dados do dashboard...
where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%PYTHON_SCRIPT%"
) else (
    where python >nul 2>&1
    if errorlevel 1 goto :ERROR_PYTHON_NOT_FOUND
    python "%PYTHON_SCRIPT%"
)

if errorlevel 1 goto :ERROR_PYTHON
echo.

echo [4/8] Validando arquivos gerados...
if not exist "%JSON_FILE%" goto :ERROR_JSON
if not exist "%MANIFEST_FILE%" goto :ERROR_MANIFEST

for %%F in ("%JSON_FILE%") do set "JSON_SIZE=%%~zF"
for %%F in ("%MANIFEST_FILE%") do set "MANIFEST_SIZE=%%~zF"

if "!JSON_SIZE!"=="0" goto :ERROR_JSON_EMPTY
if "!MANIFEST_SIZE!"=="0" goto :ERROR_MANIFEST_EMPTY

echo JSON: !JSON_SIZE! bytes
echo Manifest: !MANIFEST_SIZE! bytes
echo.

echo [5/8] Preparando alteracoes locais...
git status --short

git add .
if errorlevel 1 goto :ERROR_ADD

git diff --cached --quiet
if errorlevel 1 (
    for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set "TODAY=%%a-%%b-%%c"
    for /f "tokens=1-2 delims=:." %%a in ("%time%") do set "NOW=%%a-%%b"
    set "COMMIT_MESSAGE=Atualizacao automatica ACPTO SANTANA - !TODAY! !NOW!"

    echo.
    echo Criando commit:
    echo !COMMIT_MESSAGE!

    git commit -m "!COMMIT_MESSAGE!"
    if errorlevel 1 goto :ERROR_COMMIT
) else (
    echo Nenhuma alteracao local para commit.
)

echo.
echo [6/8] Sincronizando com o GitHub...
echo Buscando atualizacoes remotas...
git fetch origin
if errorlevel 1 goto :ERROR_FETCH

echo Aplicando as atualizacoes remotas sem perder o commit local...
git rebase origin/master
if errorlevel 1 (
    git rebase --abort >nul 2>&1
    goto :ERROR_REBASE
)

echo.
echo [7/8] Enviando para o GitHub...
git push origin master
if errorlevel 1 goto :ERROR_PUSH

echo.
echo [8/8] Publicacao finalizada.
goto :SUCCESS


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
echo Os dados foram gerados a partir do Excel atualizado,
echo validados, sincronizados e enviados para a branch master.
echo.
echo ============================================================
echo.
pause
exit /b 0


:ERROR_GIT
echo ERRO: Git nao foi encontrado no PATH.
goto :ERROR

:ERROR_REPO
echo ERRO: A pasta atual nao e um repositorio Git.
echo Verifique se o .bat esta dentro da pasta ACPTO_SANTANA.
goto :ERROR

:ERROR_REMOTE
echo ERRO: O remote "origin" nao esta configurado.
goto :ERROR

:ERROR_BRANCH
echo ERRO: A branch atual nao e "master".
echo Branch encontrada: !CURRENT_BRANCH!
goto :ERROR

:ERROR_EXCEL
echo ERRO: Excel nao encontrado:
echo %EXCEL_FILE%
goto :ERROR

:ERROR_SCRIPT
echo ERRO: Script Python nao encontrado:
echo %PYTHON_SCRIPT%
goto :ERROR

:ERROR_INDEX
echo ERRO: index.html nao encontrado.
goto :ERROR

:ERROR_DATA
echo ERRO: Pasta data nao encontrada.
goto :ERROR

:ERROR_PYTHON_NOT_FOUND
echo ERRO: Python nao foi encontrado.
echo Instale/configure Python ou o launcher "py".
goto :ERROR

:ERROR_PYTHON
echo ERRO: A geracao dos dados falhou.
echo O Git nao sera publicado.
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

:ERROR_FETCH
echo ERRO: git fetch origin falhou.
echo Verifique sua conexao e autenticacao com o GitHub.
goto :ERROR

:ERROR_REBASE
echo ERRO: Nao foi possivel sincronizar sua branch com o GitHub.
echo.
echo O rebase foi abortado para preservar o estado do repositorio.
echo Verifique se existe conflito ou alteracao remota incompatível.
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
echo Nenhuma publicacao incompleta deve ser considerada valida.
echo Corrija o problema indicado acima e execute novamente.
echo.
pause
exit /b 1
