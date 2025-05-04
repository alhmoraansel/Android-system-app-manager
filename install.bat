@echo off
REM This script installs APK packages listed in google.txt using ADB and saves logs.
REM It assumes that adb is in your system's PATH and the Android device is connected.

SETLOCAL ENABLEDELAYEDEXPANSION

SET "PACKAGE_LIST_FILE=google.txt"
SET "ADB_COMMAND=adb"
SET "LOG_FILE=install_log.txt"

REM Check if the package list file exists
IF NOT EXIST "%PACKAGE_LIST_FILE%" (
    echo Error: Package list file "%PACKAGE_LIST_FILE%" not found.
    echo Please make sure the file exists and is in the same directory as this script.
    PAUSE
    EXIT /B 1
)

REM Create the log file 
echo Script started at %DATE% %TIME% > "%LOG_FILE%"
echo Installing packages from "%PACKAGE_LIST_FILE%" using adb shell pm install-existing... >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

REM Read each line from the file and process it
FOR /F "tokens=*" %%A IN (%PACKAGE_LIST_FILE%) DO (
    SET "PACKAGE_NAME=%%A"

    REM Check if the line is empty or a comment
    IF NOT "!PACKAGE_NAME!"=="" IF NOT "!PACKAGE_NAME:~0,1!"=="#" (
        echo Installing package: !PACKAGE_NAME!
        echo Installing package: !PACKAGE_NAME! >> "%LOG_FILE%"

        REM Use adb shell pm install-existing and redirect output to the log file
        %ADB_COMMAND% shell pm install-existing "!PACKAGE_NAME!" >> "%LOG_FILE%" 2>&1

        REM Check the error level of the adb command
        IF ERRORLEVEL 1 (
            echo Failed to install package: !PACKAGE_NAME!
            echo Failed to install package: !PACKAGE_NAME! >> "%LOG_FILE%"
        ) ELSE (
            echo Package "!PACKAGE_NAME!" installed successfully.
            echo Package "!PACKAGE_NAME!" installed successfully. >> "%LOG_FILE%"
        )
    )
)

echo. >> "%LOG_FILE%"
echo Installation process complete. >> "%LOG_FILE%"
echo Script ended at %DATE% %TIME% >> "%LOG_FILE%"
echo.
echo Installation process complete.  Log file: "%LOG_FILE%"
PAUSE
ENDLOCAL
