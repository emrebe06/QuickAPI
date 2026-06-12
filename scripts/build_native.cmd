@echo off
cmake -S quickapi\native -B build\native
if errorlevel 1 exit /b %errorlevel%
cmake --build build\native --config Release
