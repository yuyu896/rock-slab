@echo off
echo.
echo ============================================
echo   Rock Slab - Test Environment (Fast Mode)
echo ============================================
echo.

echo [1/2] Starting backend (Django :8000)...
start "Backend" /d "%~dp0backend" cmd /k "python manage.py runserver 0.0.0.0:8000 --insecure"
timeout /t 3 /nobreak >nul

echo [2/2] Starting Cloudflare Tunnel...
echo.
echo ============================================
echo   Send the URL below to your testers:
echo ============================================
echo.
"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe" tunnel --url http://localhost:8000

pause
