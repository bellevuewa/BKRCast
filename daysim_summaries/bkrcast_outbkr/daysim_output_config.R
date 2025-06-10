#DaySim Version - DelPhi or C#
dsVersion                                 = "C#"

#BKRCast
dshhfile                                  = "F:/projects/2024baseyear/BKR3-24-v5_30pctWFH/outputs/daysim/_household_outbkr.tsv"
dsperfile                                 = "F:/projects/2024baseyear/BKR3-24-v5_30pctWFH/outputs/daysim/_person_outbkr.tsv"
dspdayfile                                = "F:/projects/2024baseyear/BKR3-24-v5_30pctWFH/outputs/daysim/_person_day_outbkr.tsv"
dstourfile                                = "F:/projects/2024baseyear/BKR3-24-v5_30pctWFH/outputs/daysim/_tour_outbkr.tsv"
dstripfile                                = "F:/projects/2024baseyear/BKR3-24-v5_30pctWFH/outputs/daysim/_trip_outbkr.tsv"

#calibration
#dshhfile                                  = "E:/Projects/Clients/bkr/tasks/calibration/outputs/_household_outbkr.tsv"
#dsperfile                                 = "E:/Projects/Clients/bkr/tasks/calibration/outputs/_person_outbkr.tsv"
#dspdayfile                                = "E:/Projects/Clients/bkr/tasks/calibration/outputs/_person_day_outbkr.tsv"
#dstourfile                                = "E:/Projects/Clients/bkr/tasks/calibration/outputs/_tour_outbkr.tsv"
#dstripfile                                = "E:/Projects/Clients/bkr/tasks/calibration/outputs/_trip_outbkr.tsv"

# Survey
surveyhhfile                              = "./data/Household_bkr_new_outbkr.dat"
surveyperfile                             = "./data/Person_bkr_new_skim_outbkr.dat"
surveypdayfile                            = "./data/PersonDay_bkr_outbkr.dat"
surveytourfile                            = "./data/Tour_bkr_new_skim_outbkr.dat"
surveytripfile                            = "./data/Trip_bkr_new_skim_outbkr.dat"

tazcountycorr                             = "./data/zone_districts.csv"

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

wrklocmodelout                            = "WrkLocation.xlsm"
schlocmodelout                            = "SchLocation.xlsm"
vehavmodelout                             = "VehAvailability.xlsm"
daypatmodelout                            = "DayPattern.xlsm"
tourdestmodelout                          = c("TourDestination_Escort.xlsm","TourDestination_PerBus.xlsm","TourDestination_Shop.xlsm",
                                              "TourDestination_Meal.xlsm","TourDestination_SocRec.xlsm")
tourdestwkbmodelout                       = "TourDestination_WrkBased.xlsm"
tourmodemodelout                          = "TourMode.xlsm"
tourtodmodelout                           = "TourTOD.xlsm"
tripmodemodelout                          = "TripMode.xlsm"
triptodmodelout                           = "TripTOD.xlsm"

outputsDir                                = "./output"
validationDir                             = ""

prepSurvey                                = FALSE
prepDaySim                                = TRUE

runWrkSchLocationChoice                   = TRUE
runVehAvailability                        = TRUE
runDayPattern                             = TRUE
runTourDestination                        = TRUE
runTourMode                               = TRUE
runTourTOD                                = TRUE
runTripMode                               = TRUE
runTripTOD                                = TRUE

excludeChildren5                          = FALSE
tourAdj                                   = FALSE
tourAdjFile				                        = "./data/peradjfac.csv"