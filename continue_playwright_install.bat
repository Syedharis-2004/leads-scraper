@echo off
echo Continuing Playwright browser installation...
echo This may take several minutes as it downloads ~100MB of browser files...
echo.
cd /d "e:\Haris\leads scraper"
"venv\Scripts\python.exe" -m playwright install
echo.
echo Installation complete! You can now run the lead generator.
pause