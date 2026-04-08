@echo off
title Infinite Collager V2
echo Starting Infinite Collager V2...
echo.
echo Server will open at http://localhost:6969
echo Close this window to stop the server.
echo.
start "" "http://localhost:6969"
python server.py
pause
