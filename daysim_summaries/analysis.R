library(data.table)
library(foreign)

#user input - directory where DaySim outputs reside
wd <- 'D:/projects/PostCOVID19/BKR1-20T30/outputs'

#read inputs
base_dir <- wd
hhs <- fread(paste(base_dir, '_household.tsv',sep='\\'))
pers <- fread(paste(base_dir, '_person.tsv',sep='\\'))
persDay <- fread(paste(base_dir, '_person_day.tsv',sep='\\'))
tours <- fread(paste(base_dir, '_tour.tsv',sep='\\'))
trips <- fread(paste(base_dir, '_trip.tsv',sep='\\'))

#tours_pers <- merge(tours, pers, by= c("hhno","pno"))
#trips_pers <- merge(trips, pers, by= c("hhno","pno"))
#trips_pers_hh <- merge(trips_pers, hhs, by= c("hhno"))
#trips_all <- merge(trips_pers_hh, persDay, by= c("hhno","pno"))

pers_allattr <- merge(pers, persDay, by= c("hhno","pno"))
pers_allattr$hhparcel <- hhs$hhparcel[match(pers_allattr$hhno, hhs$hhno)]
#pers_allattr <- merge(pers_allattr, hhs, by= c("hhno"))

#worker (pptyp = 1 or 2) day pattern
#1.went to work - uwplace not home (pwpcl != hhparcel); went to uwplace or work-related (wktours>0)
#2.teleworked - uwplace not home (pwpcl != hhparcel);did not go to uwplace or work-related (wktours=0); did paid work at home (>2hrs)
#3.did not work - uwplace not home (pwpcl != hhparcel);did not go to uwplace or work-related (wktours=0);did not do paid work at home (>2hrs)
#4.work from home - uplace is home (pwpcl == hhparcel)

#PPTYP	
#1 Full time worker
#2 Part time worker
#3 Non working adult age 65+
#4 Non working adult age<65
#5 University student
#6 High school student age 16+
#7 Child age 5-15
#8 Child age 0-4

#create work type categories
#pers_allattr$workpattern <- 0
#pers_allattr$workpattern <- ifelse(pers_allattr$pptyp %in% c(1,2) & pers_allattr$pwpcl!=pers_allattr$hhparcel & pers_allattr$wktours>0,1,pers_allattr$workpattern) #worker - went to work
#pers_allattr$workpattern <- ifelse(pers_allattr$pptyp %in% c(1,2) & pers_allattr$pwpcl!=pers_allattr$hhparcel & pers_allattr$wktours==0,2,pers_allattr$workpattern) #worker - teleworked or did not work
#pers_allattr$workpattern <- ifelse(pers_allattr$pptyp %in% c(1,2) & pers_allattr$pwpcl==pers_allattr$hhparcel,3,pers_allattr$workpattern) #worker - work from home

pers_allattr$workpattern <- 0
pers_allattr$workpattern <- ifelse(pers_allattr$pwpcl>0 & pers_allattr$pwpcl!=pers_allattr$hhparcel & pers_allattr$wktours>0,1,pers_allattr$workpattern) #worker - went to work
pers_allattr$workpattern <- ifelse(pers_allattr$pwpcl>0 & pers_allattr$pwpcl!=pers_allattr$hhparcel & pers_allattr$wktours==0,2,pers_allattr$workpattern) #worker - teleworked or did not work
pers_allattr$workpattern <- ifelse(pers_allattr$pwpcl>0 & pers_allattr$pwpcl==pers_allattr$hhparcel,3,pers_allattr$workpattern) #worker - work from home

pers_allattr$wplace <- ifelse(pers_allattr$pwpcl>0, 1, 0)

table(pers_allattr$workpattern)
summary_persons_workpattern <- table(pers_allattr$pptyp, pers_allattr$workpattern)

#TRIP TYPE
#11.work to wp (dpurp=work & dparcel==uwplace)
#12. work-related (dpurp=work & & dparcel!=uwplace)

#OPURP DPURP 
#0 'none/home'
#1 'work'
#2 'school'
#3 'escort'
#4 'pers.bus'
#5 'shop'
#6 'meal'
#7 'social'
#8 'recreational' (currently combined with social)
#9 'medical' (currently combined with pers.bus.)
#10 'change mode inserted purpose'

#tours$pdpurp2 <- 
tours[pdpurp==8,pdpurp:=7]
tours[pdpurp==9,pdpurp:=4]
tours[,pdpurp2:=ifelse(parent == 0,pdpurp,8)]

trips_pers <- merge(trips, pers_allattr, by= c("hhno","pno"))
trips_pers$tourdpurp <- tours$pdpurp2[match(trips_pers$tour_id, tours$id)]

#REDEFINE WORK TRIPS
trips_pers$trip_purp <- trips_pers$dpurp
trips_pers$trip_purp <- ifelse(trips_pers$tourdpurp==8,13,trips_pers$trip_purp) #13-WORK-BASED
summary_trips_pertype_daysimcat <- table(trips_pers$trip_purp, trips_pers$pptyp)

trips_pers$trip_purp <- ifelse(trips_pers$trip_purp != 13 & trips_pers$dpurp==1 & trips_pers$dpcl==trips_pers$pwpcl,11,trips_pers$trip_purp) #11-WORK TO WORKPLACE
trips_pers$trip_purp <- ifelse(trips_pers$trip_purp != 13 & trips_pers$dpurp==1 & trips_pers$dpcl!=trips_pers$pwpcl,12,trips_pers$trip_purp) #12-WORK-RELATED

summary_trips_workpattern <- table(trips_pers$trip_purp, trips_pers$workpattern)
summary_trips_pertype <- table(trips_pers$trip_purp, trips_pers$pptyp)

#write summaries to "summary_model.csv" - ptoduced under DaySim directory
cat("Persons by Person Day Pattern \n",file=paste(wd, "summary_model.csv", sep = "\\"))
write.table(summary_persons_workpattern, paste(wd, "summary_model.csv", sep = "\\"), sep = ",", append = T, col.names=NA)

cat("Trips By Worker's Work Pattern Type \n",file=paste(wd, "summary_model.csv", sep = "\\"), append = T)
write.table(summary_trips_workpattern, paste(wd, "summary_model.csv", sep = "\\"), sep = ",", append=T, col.names=NA)

cat("Trips by Person Type and Purpose \n",file=paste(wd, "summary_model.csv", sep = "\\"), append = T)
write.table(summary_trips_pertype, paste(wd, "summary_model.csv", sep = "\\"), sep = ",", append=T, col.names=NA)

cat("Trips by Person Type and Purpose \n",file=paste(wd, "summary_model_calibration.csv", sep = "\\"))
row_names_to_remove <- c("0","10")
summary_trips_pertype_daysimcat <- summary_trips_pertype_daysimcat[!(row.names(summary_trips_pertype_daysimcat) %in% row_names_to_remove),]
write.table(summary_trips_pertype_daysimcat, paste(wd, "summary_model_calibration.csv", sep = "\\"), sep = ",", append=T, col.names=NA)

print('Done')