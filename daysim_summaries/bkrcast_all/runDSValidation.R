#DaySim Version - DelPhi or C#
dsVersion                                 = "C#"

parcelfile                                = "./data/parcel.dat"
dshhfile                                  = "./data/_household.tsv"
dsperfile                                 = "./data/_person.tsv"
dspdayfile                                = "./data/_person_day.tsv"
dstourfile                                = "./data/_tour.tsv"
dstripfile                                = "./data/_trip.tsv"
dstriplistfile                            = "./data/Tdm_trip_list.csv"


amskimfile                                = "./data/SKM_AM_D1.TXT"
mdskimfile                                = "./data/SKM_MD_D1.TXT"
pmskimfile                                = "./data/SKM_PM_D1.TXT"
evskimfile                                = "./data/SKM_EV_D1.TXT"

tazcountycorr                             = "./data/county_districts.csv"
outputsDir                                = "./output"
wrklocmodelfile                           = "./templates/WrkLocation.csv"
schlocmodelfile                           = "./templates/SchLocation.csv"
vehavmodelfile                            = "./templates/VehAvailability.csv"
daypatmodelfile1                          = "./templates/DayPattern_pday.csv"
daypatmodelfile2                          = "./templates/DayPattern_tour.csv"
daypatmodelfile3                          = "./templates/DayPattern_trip.csv"
tourdestmodelfile                         = "./templates/TourDestination.csv"
tourdestwkbmodelfile                      = "./templates/TourDestination_wkbased.csv"
tripdestmodelfile                         = "./templates/TripDestination.csv"
tourmodemodelfile                         = "./templates/TourMode.csv"
tourtodmodelfile                          = "./templates/TourTOD.csv"
tripmodemodelfile                         = "./templates/TripMode.csv"
triptodmodelfile                          = "./templates/TripTOD.csv"


validationDir                              = ""


prepNHTS                                   = FALSE
prepDaySim                                 = TRUE


runWrkSchLocationChoice                    = TRUE
runVehAvailability                         = TRUE
runDayPattern                              = TRUE
runTourDestination                         = TRUE
runTourMode                                = TRUE
runTourTOD                                 = TRUE
runTripMode                                = TRUE
runTripTOD                                 = TRUE

pb_globalsummary <- winProgressBar(title = "run DaySim summaries", min = 0, max = 13, width = 600)
setWinProgressBar(pb_globalsummary, 1, title=paste("reading hh data"))
if(runWrkSchLocationChoice | runVehAvailability | runDayPattern | runTourDestination | runTourMode)
{
    dshhdata <- read.table(dshhfile,header=T)
}

setWinProgressBar(pb_globalsummary, 2, title=paste("reading person data"))
if(runWrkSchLocationChoice | runDayPattern | runTourDestination | runTourMode | runTourTOD | runTripMode | runTripTOD)
{
    dsperdata <- read.table(dsperfile,header=T)
}

setWinProgressBar(pb_globalsummary, 3, title=paste("reading person day data"))
if(runDayPattern)
{
    dspdaydata <- read.table(dspdayfile,header=T)
}

setWinProgressBar(pb_globalsummary, 4, title=paste("reading person day tour data"))
if(runDayPattern | runTourDestination | runTourMode | runTourTOD | runTripMode)
{
    dstourdata <- read.table(dstourfile,header=T)
}

setWinProgressBar(pb_globalsummary, 5, title=paste("reading person day trip data"))
if(runDayPattern | runTripMode | runTripTOD)
{
    dstripdata <- read.table(dstripfile,header=T)
}


#source("nonhwy.R")

setWinProgressBar(pb_globalsummary, 6, title=paste("summarizing work location choice"))
if(runWrkSchLocationChoice)
{
    source("WrkSchLocation.R")
}
setWinProgressBar(pb_globalsummary, 7, title=paste("summarizing vehicle ownership choice"))
if(runVehAvailability)
{
    source("VehAvailability.R")
}
setWinProgressBar(pb_globalsummary, 8, title=paste("summarizing Day pattern")) 
if(runDayPattern)
{
    source("DayPattern.R")
}
setWinProgressBar(pb_globalsummary, 9, title=paste("summarizing Destination Choice")) 
if(runTourDestination)
{
    source("TourDestination.R")
}
setWinProgressBar(pb_globalsummary, 10, title=paste("summarizing Trip Destination Choice")) 
if(runTourDestination)
{
    source("TripDestination.R")
}
setWinProgressBar(pb_globalsummary, 10, title=paste("summarizing Tour Mode Choice")) 
if(runTourMode)
{
    source("TourMode.R")
}
setWinProgressBar(pb_globalsummary, 11, title=paste("summarizing Tour Time of Day Choice")) 
if(runTourTOD)
{
    source("TourTOD.R")
}
setWinProgressBar(pb_globalsummary, 12, title=paste("summarizing Trip Mode Choice")) 
if(runTripMode)
{
    source("TripMode.R")
}
setWinProgressBar(pb_globalsummary, 13, title=paste("summarizing Trip Time of Day Choice"))
if(runTripTOD)
{
    source("TripTOD.R")
}
close(pb_globalsummary)
