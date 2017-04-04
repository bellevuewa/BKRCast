#DaySim Version - DelPhi or C#
dsVersion                                 = "C#"

parcelfile                                = "E:/Projects/Clients/bkr/model/bkrcast_tod_new/inputs/buffered_parcels.dat"
dshhfile                                  = "E:/Projects/Clients/bkr/model/bkrcast_tod_new/outputs/_household.tsv"
dsperfile                                 = "E:/Projects/Clients/bkr/model/bkrcast_tod_new/outputs/_person.tsv"
dspdayfile                                = "E:/Projects/Clients/bkr/model/bkrcast_tod_new/outputs/_person_day.tsv"
dstourfile                                = "E:/Projects/Clients/bkr/model/bkrcast_tod_new/outputs/_tour.tsv"
dstripfile                                = "E:/Projects/Clients/bkr/model/bkrcast_tod_new/outputs/_trip.tsv"
#dstriplistfile                            = "E:/Projects/Clients/bkr/model/bkrcast_tod_new/outputs/Tdm_trip_list.csv"

# BKRCast Survey
surveyhhfile                              = "./data/Household_bkr.dat"
surveyperfile                             = "./data/Person_bkr.dat"
surveypdayfile                            = "./data/PersonDay_bkr.dat"
surveytourfile                            = "./data/Tour_bkr.dat"
surveytripfile                            = "./data/Trip_bkr.dat"

amskimfile                                = "../DaySim/hwyskim_am.TXT"
mdskimfile                                = "../DaySim/hwyskim_md.TXT"
pmskimfile                                = "../DaySim/hwyskim_pm.TXT"
evskimfile                                = "../DaySim/hwyskim_op.TXT"

tazcountycorr                             = "./data/taz_districts_bkr.csv"

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

prepSurvey                                = TRUE
prepDaySim                                = TRUE

runWrkSchLocationChoice                   = TRUE
runVehAvailability                        = TRUE
runDayPattern                             = TRUE
runTourDestination                        = TRUE
runTourMode                               = TRUE
runTourTOD                                = TRUE
runTripMode                               = TRUE
runTripTOD                                = TRUE

excludeChildren5                          = TRUE
tourAdj                                   = FALSE
tourAdjFile				                        = "./data/peradjfac.csv"