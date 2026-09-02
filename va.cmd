@echo off
set "VIRTUAL_ENV=%~dp0.venv"

if not exist "%VIRTUAL_ENV%\Scripts\python.exe" (
  echo No encontre la .venv del proyecto en "%VIRTUAL_ENV%"
  exit /b 1
)

if not defined PROMPT set "PROMPT=$P$G"
if defined _OLD_VIRTUAL_PROMPT set "PROMPT=%_OLD_VIRTUAL_PROMPT%"
if defined _OLD_VIRTUAL_PYTHONHOME set "PYTHONHOME=%_OLD_VIRTUAL_PYTHONHOME%"

set "_OLD_VIRTUAL_PROMPT=%PROMPT%"
set "PROMPT=(.venv) %PROMPT%"

if defined PYTHONHOME set "_OLD_VIRTUAL_PYTHONHOME=%PYTHONHOME%"
set "PYTHONHOME="

if defined _OLD_VIRTUAL_PATH set "PATH=%_OLD_VIRTUAL_PATH%"
if not defined _OLD_VIRTUAL_PATH set "_OLD_VIRTUAL_PATH=%PATH%"

set "PATH=%VIRTUAL_ENV%\Scripts;%~dp0;%PATH%"
set "VIRTUAL_ENV_PROMPT=(.venv) "
