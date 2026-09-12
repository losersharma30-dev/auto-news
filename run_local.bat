@echo off
REM Auto-News local test helper
REM ============================
REM First time only:  pip install -r requirements.txt
REM Then run this script anytime to test locally before deploying.

echo [1/2] Collecting headlines...
python collect.py --limit %1
if %ERRORLEVEL% neq 0 goto :err

echo [2/2] Building website...
python generate_site.py
if %ERRORLEVEL% neq 0 goto :err

echo.
echo Done! Open site\index.html in your browser to preview.
echo (For live AI summaries, set your GEMINI_API_KEY env var first.)
exit /b 0

:err
echo Something failed - see the error above.
exit /b 1