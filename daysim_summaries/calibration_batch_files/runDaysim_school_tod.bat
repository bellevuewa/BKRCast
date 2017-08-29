:: ############################################################################
:: # Batch file to run DayPattern and Work-based Subtour Generation Calibration
:: # nagednra.dhakar@rsginc.com, May 2017

:: # Setup:
:: # Three directories: 
:: # 	daysim - all daysim inputs and coefficients with "output" and "working" folders. This batchfile should be in this folder.
:: # 	daysim_summaries - R scripts and output folder
:: # 	iterations - "TourTOD_CR0" folder with the two daysim coefficient files (TourTOD and workbased subtour generation) and shadow prices (including park and ride shadow prices)

:: # Process:
:: # User need to update "iteration_no" for every calibration round
:: # Always start with iteration=0 by running your base DaySim run - for this you need to have "TourTOD_CR0" in the "iterations" folder with the two daysim coefficent files (TourTOD and workbased subtour generation) and shadow prices (including park and ride shadow prices)

:: # Example:
:: # for illustration purpose, let's say iteration_no=1
:: # 1. copies two coefficient files from "TourTOD_CR1" under the folder "iterations" to DaySim folder
:: # 2. Runs DaySim
:: # 3. Runs DaySim summaries
:: # 4. Copies "TourTOD.xlsm" from summaries output folder to "TourTOD_CR1" under the folder "iterations" as "TourTOD_CR1.xlsm".
:: # 5. Creates a new directory "TourTOD_CR2" for the next iteration (iteration=2) under "iterations"
:: # 6. Copies two shadow prices and two coefficients files from current iteration folder (TourTOD_CR1) to the next iteration folder (TourTOD_CR2) created in the last step
:: # 7. Copies shadow prices from current iteration folder (TourTOD_CR1) to DaySim Folder

:: # USER NEEDS TO PERFORM THESE BEFORE RUNNING THE BATCH FILE FOR THE NEXT ITERATION
:: # 1. First, update coefficients in tabs "TourTODCoefficients" and "WorkbasedSubtourGenerationCoeff" under "TourTOD_CR1.xlsm" with the two coefficient files in folder "TourTOD_CR1"
:: #    this step would update the coefficients in the spreadsheet "TourTOD_CR1.xlsm"
:: # 2. Now, update coefficient files under the next iteration folder "TourTOD_CR" with the new coefficients from "calibration" tab in spreadsheet "TourTOD_CR1.xlsm"
:: # 3. Update Iteration_no = 2 in this batch file
:: # 4. Run the batch file
:: ############################################################################

@echo off

set iteration_no=0
set project_directory=E:\Projects\Clients\bkr\tasks\calibration
set folder_name=TourTOD_CR%iteration_no%

rem copy the coefficient file to the DaySim folder
set copy_from=%project_directory%\Iterations\%folder_name%\SchoolTourTimeModel.F12
set copy_to=%project_directory%\inputs\coefficients\SchoolTourTimeModel.F12

copy %copy_from% %copy_to%

rem run daysim
daysim\Daysim.exe -c daysim\daysim_configuration.properties
if ERRORLEVEL 1 goto DONE

cd daysim_summaries

rem daysim summaries
call runBKRCastSummaries.bat

rem goto DONE

set copy_from=%project_directory%\daysim_summaries\bkrcast_all\output\TourTOD.xlsm
set copy_to=%project_directory%\Iterations\%folder_name%\TourTOD_CR%iteration_no%.xlsm

rem copy the summary file
copy %copy_from% %copy_to%

cd ..
cd iterations

rem for next iteration
set /A next_iteration = %iteration_no%
set /A next_iteration+ = 1
set new_directory=TourTOD_CR%next_iteration%

rem make new directory
md %new_directory%

rem copy the shadow pricing to the new folder
set copy_from=%project_directory%\Iterations\%folder_name%\shadow_prices.txt
set copy_to=%project_directory%\Iterations\%new_directory%\shadow_prices.txt

copy %copy_from% %copy_to%

rem copy the PNR shadow pricing to the new folder
set copy_from=%project_directory%\Iterations\%folder_name%\park_and_ride_shadow_prices.txt
set copy_to=%project_directory%\Iterations\%new_directory%\park_and_ride_shadow_prices.txt

copy %copy_from% %copy_to%

rem copy the school tour time coefficient file to the new folder
set copy_from=%project_directory%\Iterations\%folder_name%\SchoolTourTimeModel.F12
set copy_to=%project_directory%\Iterations\%new_directory%\SchoolTourTimeModel.F12

copy %copy_from% %copy_to%

rem copy the shadow price to daysim/working folder
set copy_from=%project_directory%\Iterations\%folder_name%\shadow_prices.txt
set copy_to=%project_directory%\working\shadow_prices.txt

copy %copy_from% %copy_to%

rem copy the PNR shadow price to daysim/working folder
set copy_from=%project_directory%\Iterations\%folder_name%\park_and_ride_shadow_prices.txt
set copy_to=%project_directory%\working\park_and_ride_shadow_prices.txt

copy %copy_from% %copy_to%

cd ..

:done
set RESULT=FAILED
