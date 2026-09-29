@echo off
rem Build dist\ThaiW3Setup-<version>.zip
rem   build.bat            download the latest translations, then build
rem   build.bat offline    reuse assets\translations.json.gz
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    python -m venv .venv || goto :error
)
set PY=.venv\Scripts\python.exe
%PY% -m pip install --disable-pip-version-check -q -r requirements-build.txt || goto :error

if not exist packaging\icon.ico %PY% devtools\make_icon.py || goto :error
%PY% packaging\make_version_info.py || goto :error

if /i "%~1"=="offline" (
    if not exist assets\translations.json.gz (
        echo assets\translations.json.gz is missing, run without "offline" first
        goto :error
    )
) else (
    %PY% -m core.sheet --export assets\translations.json.gz || goto :error
)

%PY% -m PyInstaller --noconfirm --clean ThaiW3Setup.spec || goto :error
copy /y README.md dist\ThaiW3Setup\README.md >nul

for /f %%v in ('%PY% -c "import core; print(core.__version__)"') do set VERSION=%%v
set ZIP=dist\ThaiW3Setup-%VERSION%.zip
if exist "%ZIP%" del "%ZIP%"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\ThaiW3Setup' -DestinationPath '%ZIP%'" || goto :error
powershell -NoProfile -Command "$h=(Get-FileHash '%ZIP%' -Algorithm SHA256).Hash.ToLower(); \"$h  ThaiW3Setup-%VERSION%.zip\" | Out-File -Encoding ascii '%ZIP%.sha256'; Write-Host SHA256 $h"
echo.
echo Built %ZIP%
exit /b 0

:error
echo Build failed.
exit /b 1
