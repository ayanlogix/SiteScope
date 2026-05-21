@echo off
:: ============================================================
:: SiteScope - Clean Build & Force Push to GitHub
:: ============================================================
cd /d "%~dp0"
title SiteScope - Final Push

echo ============================================================
echo   SiteScope - Cleanup and Force Push to GitHub
echo ============================================================
echo.

:: Step 1: Delete old utility JS tool files
echo [1/6] Removing old tool scripts...
if exist js\base64-tool.js (
    del /f /q js\base64-tool.js
    echo   Deleted: js\base64-tool.js
)
if exist js\color-tool.js (
    del /f /q js\color-tool.js
    echo   Deleted: js\color-tool.js
)
if exist js\glass-tool.js (
    del /f /q js\glass-tool.js
    echo   Deleted: js\glass-tool.js
)
if exist js\json-tool.js (
    del /f /q js\json-tool.js
    echo   Deleted: js\json-tool.js
)
if exist js\jwt-tool.js (
    del /f /q js\jwt-tool.js
    echo   Deleted: js\jwt-tool.js
)
if exist js\regex-tool.js (
    del /f /q js\regex-tool.js
    echo   Deleted: js\regex-tool.js
)
if exist js\main.js (
    del /f /q js\main.js
    echo   Deleted: js\main.js
)
if exist styles\tools.css (
    del /f /q styles\tools.css
    echo   Deleted: styles\tools.css
)
echo [1/6] Old tool files removed.
echo.

:: Step 2: Verify git is installed
echo [2/6] Checking Git installation...
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Git is not installed or not on PATH.
    echo Install Git from https://git-scm.com/ and retry.
    pause
    exit /b
)
echo [2/6] Git found.
echo.

:: Step 3: Reset git history for a clean fresh push
echo [3/6] Resetting local git repository for clean push...
if exist .git (
    rmdir /s /q .git
    echo   Old .git history removed.
)
git init
echo [3/6] Git re-initialized.
echo.

:: Step 4: Stage all clean files
echo [4/6] Staging clean project files...
git add .
echo [4/6] Files staged.
echo.

:: Step 5: Create clean commit
echo [5/6] Creating clean commit...
git commit -m "SiteScope - Initial Release"
git branch -M main
echo [5/6] Commit created.
echo.

:: Step 6: Set remote and force push
echo [6/6] Setting remote and force-pushing to GitHub...
git remote remove origin >nul 2>nul
git remote add origin https://github.com/ayanlogix/SiteScope.git
git push -u origin main --force

if %ERRORLEVEL% eq 0 (
    echo.
    echo ============================================================
    echo   SUCCESS - SiteScope is LIVE on GitHub!
    echo   Visit: https://github.com/ayanlogix/SiteScope
    echo ============================================================
    echo.
) else (
    echo.
    echo WARNING: Push failed. Check your GitHub authentication.
    echo   Make sure you have a PAT or SSH key configured.
    echo.
)

pause
