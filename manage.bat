@echo off
cd /d "%~dp0"

if "%1"=="" goto help
if "%1"=="status" goto status
if "%1"=="once" goto once
if "%1"=="install" goto install
if "%1"=="remove" goto remove
if "%1"=="start" goto start
if "%1"=="stop" goto stop
goto help

:help
echo.
echo  Usage:
echo    manage status     Show status and stats
echo    manage once       Run one round (collect, screen, write, publish)
echo    manage install    Register daily scheduled task at 19:00
echo    manage remove     Remove scheduled task
echo    manage start      Run 7x24 in a window
echo    manage stop       Stop the 7x24 window
echo.
goto end

:status
.venv\Scripts\python status.py
goto end

:once
echo Running one round...
.venv\Scripts\python -m agent_team.orchestrator --once
if %errorlevel%==0 (
    echo Done. Check output\ directory for articles.
) else (
    echo Failed. Check .env config.
)
goto end

:install
echo Registering daily scheduled task at 19:00...
schtasks /create /tn "ZhihuAgentTeam" /tr "%~dp0run_agent_hourly.bat" /sc daily /st 19:00 /f
if %errorlevel%==0 (
    echo OK! Task registered: runs daily at 19:00.
    echo Output directory: %~dp0output\
) else (
    echo Failed. Run as Administrator.
)
goto end

:remove
echo Removing scheduled task...
schtasks /delete /tn "ZhihuAgentTeam" /f 2>nul
echo Done.
goto end

:start
echo Starting 7x24 mode...
start "Zhihu Agent Team" cmd /k ".venv\Scripts\python -m agent_team.orchestrator"
echo OK. Close the window to stop.
goto end

:stop
taskkill /f /fi "WINDOWTITLE eq Zhihu Agent Team" 2>nul
echo Done.
goto end

:end
