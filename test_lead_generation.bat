@echo off
echo Testing Lead Generation Setup...
echo ========================================
echo.

REM Check if backend is running
echo Checking backend status...
netstat -ano | findstr :8765 > nul
if %errorlevel% equ 0 (
    echo ✓ Backend is running on port 8765
) else (
    echo ✗ Backend is not running on port 8765
    echo   Run 'Start Dashboard.bat' first
    goto :end
)

echo.
echo Testing API connectivity...
python -c "
import urllib.request, json
try:
    resp = urllib.request.urlopen('http://127.0.0.1:8765/api/health')
    data = json.loads(resp.read())
    print('✓ API Health:', data['status'])
except Exception as e:
    print('✗ API Error:', str(e)[:100])
" 2>nul

echo.
echo Checking API key...
python -c "
import urllib.request, json
try:
    resp = urllib.request.urlopen('http://127.0.0.1:8765/api/settings/key')
    data = json.loads(resp.read())
    if data['has_key']:
        print('✓ API key is configured')
        print('  Model:', data.get('model', 'N/A'))
    else:
        print('✗ No API key configured')
        print('  Go to API Settings page to add your Gemini API key')
except Exception as e:
    print('✗ Error:', str(e)[:100])
" 2>nul

echo.
echo ========================================
echo Summary:
echo 1. If backend is not running, run 'Start Dashboard.bat'
echo 2. If no API key, add it in the API Settings page
echo 3. If Playwright not installed, run 'continue_playwright_install.bat'
echo.
echo Once all above are fixed, try generating leads again.
pause

:end