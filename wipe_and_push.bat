@echo off
:: ============================================================
:: SiteScope - Wipe Git History & Push Clean to GitHub
:: ============================================================
cd /d "%~dp0"
title SiteScope - Wipe History and Push Clean

echo ============================================================
echo   SiteScope - Wipe All Git History and Push Fresh
echo ============================================================
echo.
echo   WARNING: This will DELETE all previous commit history.
echo   GitHub will show only 1 clean commit after this.
echo.
pause

:: Step 1: Check git is installed
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Git not found. Install from https://git-scm.com/
    pause
    exit /b
)

:: Step 2: Delete old .git folder
echo.
echo [1/6] Wiping old git history...
if exist .git (
    rmdir /s /q .git
    echo   Old .git folder deleted.
) else (
    echo   No .git folder found. Starting fresh anyway.
)

:: Step 3: Initialize fresh repo
echo.
echo [2/6] Initializing fresh git repository...
git init
echo   Done.

:: Step 4: Stage all files
echo.
echo [3/6] Staging all project files...
git add .
echo   Done.

:: Step 5: Make clean commit
echo.
echo [4/6] Creating clean single commit...
git commit -m "SiteScope - Initial Release"
git branch -M main
echo   Done.

:: Step 6: Set remote to SiteScope repo
echo.
echo [5/6] Setting remote origin...
git remote remove origin >nul 2>nul
git remote add origin https://github.com/ayanlogix/SiteScope.git
echo   Remote set to: https://github.com/ayanlogix/SiteScope.git

:: Step 7: Force push
echo.
echo [6/6] Force pushing to GitHub...
git push -u origin main --force

if %ERRORLEVEL% eq 0 (
    echo.
    echo ============================================================
    echo   SUCCESS! Git history wiped and fresh push done!
    echo   Visit: https://github.com/ayanlogix/SiteScope
    echo ============================================================
) else (
    echo.
    echo   FAILED: Push did not go through.
    echo   Make sure you are logged in to GitHub.
    echo   Tip: Run  git config --global credential.helper manager
)

echo.
pause
