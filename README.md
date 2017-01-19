#BKRCast

The BKR (Bellevue Kirkland Redmond) Activity-Based Model

BKRCast is based on PSRC's (Puget Sound Regional Council) [SoundCast](https://github.com/psrc/soundcast) activity-based regional transportation model.  
Both BKRCast and SoundCast use the same EMME-based network procedures, Daysim for resident demand, and supplemental
demand models for externals, trucks, etc.  BKRCast is different from SoundCast in three primary ways:
  
  - BKRCast uses a BKR specific zone system and networks.  This zone system has more zones in the BKR region and less zones in the rest of the PSRC region
  - BKRCast has four time periods for networks (AM, MD, PM, NT) in order to reduce runtimes and data needs.
  - BKRCast has a population sampling procedure that oversamples households in the BKR region, while undersampling households outside the region, in order to increase model stability and decrease runtime
  - (Still To Do) BKRCast was locally calibrated/validated.

## System Setup

Hardware:
  - 8 CPUs
  - 32 GB RAM
  - 120 GB disk space **per model run**

Software:
  - Windows 7+, 64-bit only
  - Anaconda Python 2.7
  - Emme 4.2.3+
  - Git for Windows and Git LFS for downloading the model setup only; not for running it

The system setup steps are as follows:

  - Install 64-bit Anaconda Python 2.7 from http://www.continuum.io/downloads
  - Find your Python install folder in File Explorer:
    - Go to Anaconda2\Lib\site-packages
    - Delete the folder 'ply'
    - (This is for Emme Python compatibility)
  - Install Emme 4.2.3+
    - NO to Emme Python as the System Python
    - Make sure you can open Emme Desktop and that your license is validated
  - Run Emme Desktop:
    - Go to Tools - App Options - Modeller.
    - Change Python Path to point to your Anaconda install folder, and click "Install Modeller Package".
    - Close Emme.
  - Install [Git for Windows](https://git-scm.com/download/win)
  - Install [Git Large File Storage (LFS)](https://git-lfs.github.com/) 
  - Test git and git lfs:
    - Open a DOS command window
    - Run 'git lfs' to ensure Git for Windows and Git LFS are installed and available as command line tools

## Model Setup

  - Clone this repository, which contain the programs and configuration files:
    - Open a DOS command window and 'cd' into a folder to house the model run
    - Run 'git clone https://github.com/RSGInc/BKRCast.git' to download this repository.
  - Clone the private (limited access) inputs folder repository - https://github.com/RSGInc/BKRCastInputs:
    - Open a DOS command window and 'cd' into a folder to house the model run inputs folder
    - Run 'git clone https://github.com/RSGInc/BKRCastInputs.git' to download this repository.  This will take some time.   
  - Copy the inputs\supplemental\trips\*.* files to outputs\supplemental since they are required in this location as well.
  - Set the working folder in 'input_configuration.py':
    - Set 'main_inputs_folder' to the working folder \inputs folder
    - Set 'daysim_code' to the working folder \daysim2016 folder
  - If desired, set various model run settings in 'input_configuration.py':
      - pop_sample = [50, 100, 100] # household sample rate(50=50%) per overall model feedback loop
      - max_iterations_list = [100, 100, 100] # assignment iterations per overall model feedback loop

## Running the Model

  - Open a DOS prompt in the working folder and run ```python run_bkrcast.py```
  
## SoundCast Documentation
  
  - [SoundCast](https://github.com/psrc/soundcast)
  - http://www.psrc.org/data/models/abmodel/ for design documents and model calibration/validation summaries
  - http://soundcast.readthedocs.org/en/dev/ for full documentation about running the model
  - PSRC's fork of Daysim, the core model on which SoundCast is based, can be found at https://github.com/psrc/daysim

## psrc_to_bkrcast_scripts

This folder contains scripts used to convert various SoundCast inputs to BKRCast inputs
