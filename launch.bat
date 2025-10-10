@echo off
REM --- SETTINGS ---
REM Set the name of your virtual environment folder
set VENV_DIR=audio_env_stable
REM Set the name of your Python script
set SCRIPT_NAME=program.py

REM --- EXECUTION ---
echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

REM Execute the Python script
echo Running the Python program...
python "%SCRIPT_NAME%"

REM Wait for user input if the script runs too fast and closes the window
pause