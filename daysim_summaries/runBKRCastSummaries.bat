:: ############################################################################
:: # Batch file to run BKRCast Calibration summaries
:: # Nagendr Dhakar, nagendra.dhakar@rsginc.com, May 2017
:: ############################################################################

SET WORKING_DIR=%CD%

@ECHO OFF
ECHO BKRCast Summaries
SET BATCH_FILE_SUMMARIES=daysim_summaries.cmd
SET BATCH_FILE_DATASET=create_bkr_dataset.cmd
SET PYTHON_SCRIPT=update_data.py

:: Segment DaySim outputs to in/out bkr datasets
ECHO %startTime%%Time%: Running creation of in/out datasets...
call %BATCH_FILE_DATASET%
ECHO %startTime%%Time%: Finished creating in/out bkr datasets...

:: DaySim summaries

:: bkrcast_all
cd bkrcast_all
ECHO %startTime%%Time%: Running DaySim summaries for BKRCast (all)...
call %BATCH_FILE_SUMMARIES%
ECHO %startTime%%Time%: Finished summaries for BKRCast (all)...

:: bkrcast_inbkr
cd ..
cd bkrcast_inbkr
ECHO %startTime%%Time%: Running DaySim summaries for BKRCast (in bkr)...
call %BATCH_FILE_SUMMARIES%
ECHO %startTime%%Time%: Finished summaries for BKRCast (in bkr)...

:: bkrcast_outbkr
cd ..
cd bkrcast_outbkr
ECHO %startTime%%Time%: Running DaySim summaries for BKRCast (out bkr)...
call %BATCH_FILE_SUMMARIES%
ECHO %startTime%%Time%: Finished summaries for BKRCast (out bkr)...

:: run comparison
cd ..
ECHO %startTime%%Time%: Running comparison of all runs...
call python %PYTHON_SCRIPT%
ECHO %startTime%%Time%: Finished comparison of all runs...

:: run district summaries
ECHO %startTime%%Time%: Running district summaries...
ECHO %startTime%%Time%: Finished district summaries...

ECHO FINISHED












