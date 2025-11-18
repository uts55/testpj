@echo off
setlocal ENABLEDELAYEDEXPANSION

:: --- Configuration ---
set "PYTHON_EXEC=python"
set "VENV_DIR=venv"
set "REQUIREMENTS_FILE=requirements.txt"
set "MAIN_SCRIPT=main.py"
set "ENV_FILE=.env"
set "LOG_FILE=run_log.txt"

:: --- Start Logging Redirection ---
:: Redirect all subsequent output (stdout and stderr) to the log file.
:: Existing log file will be overwritten.
> "%LOG_FILE%" (
    2>&1 (
        echo.
        echo =========================================================
        echo Starting application setup...
        echo Current directory: %CD%
        echo IMPORTANT: Make sure your .env file is in the same directory as this script.
        echo It must contain: GOOGLE_API_KEY="YOUR_ACTUAL_GOOGLE_API_KEY"
        echo (Replace YOUR_ACTUAL_GOOGLE_API_KEY with your real API key)
        echo =========================================================
        echo.

        :: --- Check for .env file ---
        echo Checking for %ENV_FILE% file...
        if not exist "%ENV_FILE%" (
            echo ERROR: %ENV_FILE% not found.
            echo Please create it and add your GOOGLE_API_KEY.
            exit /b 1
        ) else (
            echo %ENV_FILE% found.
        )

        echo.
        echo --- Step 1: Virtual Environment Setup ---
        if not exist "%VENV_DIR%\Scripts\python.exe" (
            echo Virtual environment not found. Creating...
            "%PYTHON_EXEC%" -m venv "%VENV_DIR%"
            if !errorlevel! neq 0 (
                echo ERROR: Failed to create virtual environment. Ensure Python is installed and in PATH.
                exit /b 1
            )
            echo Virtual environment created.
        ) else (
            echo Virtual environment already exists. Skipping creation.
        )

        echo.
        echo --- Step 2: Activate Virtual Environment ---
        call "%VENV_DIR%\Scripts\activate.bat"
        if !errorlevel! neq 0 (
            echo ERROR: Failed to activate virtual environment.
            exit /b 1
        )
        echo Virtual environment activated. PATH updated.

        echo.
        echo --- Step 3: Install/Update Python Dependencies ---
        echo Installing/Updating Python dependencies from %REQUIREMENTS_FILE%...
        pip install -r "%REQUIREMENTS_FILE%"
        if !errorlevel! neq 0 (
            echo ERROR: Failed to install dependencies. Check %REQUIREMENTS_FILE% and network connection.
            deactivate
            exit /b 1
        )
        echo Dependencies installed successfully.

        echo.
        echo --- Step 4: Running the Main Application ---
        echo Executing: python "%MAIN_SCRIPT%"
        :: The actual Python application output will now be redirected to the log file.
        python "%MAIN_SCRIPT%"
        set "APP_EXIT_CODE=!errorlevel!"

        echo.
        echo --- Step 5: Application Execution Summary ---
        if !APP_EXIT_CODE! neq 0 (
            echo Application exited with an ERROR. Exit Code: !APP_EXIT_CODE!
            echo This usually means an issue occurred during Python script execution.
            echo Please review the output above for Python errors or critical logs from main.py.
        ) else (
            echo Application finished successfully.
        )

        :: --- Deactivate virtual environment ---
        deactivate
        echo Virtual environment deactivated.

    )
)

:: --- End Logging Redirection ---
:: After the redirection block, output will go back to console.
echo.
echo --- Script Finished ---
echo.
echo All output has been saved to "%LOG_FILE%".
echo Please open this file to review the full execution log and any errors.
pause
endlocal