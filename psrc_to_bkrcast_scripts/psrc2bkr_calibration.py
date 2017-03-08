#Convert calibration summary files from PSRC to BKR: TAZ_TAD_County.csv and FAZ_TAZ.xlsx
#Nagendra Dhakar, nagendra.dhakar@rsginc.com, 09/30/16

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import os, shutil
import pandas as pd
import h5py
import numpy as np

#inputs
calibration_dir = r'E:\Projects\Clients\bkr\model\soundcast\scripts\summarize\inputs\calibration'
zonefiles = ["TAZ_TAD_County.csv","FAZ_TAZ.xlsx"]
survey_file = "survey_psrc.h5"
inputs_dir = r'E:\Projects\Clients\bkr\model\bkrcast_tod\inputs'
parcel_file = "buffered_parcels.dat"
survey_file_new = "survey.h5" #this is required only when runDaySimFormat is run indepently (with runSurveyFile = False)
tazSharesFileName = "psrc_to_bkr.txt"
zone_file = "TAZ_TAD_County.csv"
faz_file = "FAZ_TAZ.xlsx"
district_lookup_file = "district_lookup.csv"
zoneLatLongFileName = 'bkr_zone_lat_long.csv'

#flags
runSurveyFile = True
runDaySimFormat = True

# read file
tazSharesFileName = os.path.join(os.getcwd(), tazSharesFileName)
tazShares = pd.read_table(tazSharesFileName)
    
def readSurveyData(fileName, group, group_fields):
    daysimFile = h5py.File(fileName)
    
    #build pandas data frames
    dataTable = pd.DataFrame()
    for field in group_fields:
        dataTable[field] = daysimFile.get(group).get(field)[:]

    return(dataTable)

def writeSurveyFields(fileName, tripFields, group):
    
    #delete columns first and then write
    daysimFile = h5py.File(fileName, "a")
    for field in tripFields.columns:
        dataset = group + "/" + field
        print(dataset)
        del daysimFile[dataset]
        daysimFile.create_dataset(dataset, data = tripFields[field], compression="gzip")
    daysimFile.close()

def pickTaz(table, tazField, zoneWeights):
    psrcZone = table[tazField].tolist()[0]
    print("sampling tazs for PSRC zone " + str(psrcZone))
    bkrZones = zoneWeights[zoneWeights["psrc_zone_id"]==psrcZone]
    if len(bkrZones) == 0:
        print("psrcZone " + str(psrcZone) + " not found so using zone 1 instead - check externals, PNR nodes")
        bkrZones = zoneWeights[zoneWeights["psrc_zone_id"]==1]
        return(bkrZones.sample(len(table), replace=True, weights="percent"))
    else:
        return(bkrZones.sample(len(table), replace=True, weights="percent"))
'''
updates trips data in survey file
otaz - trip origina taz
dtaz - trip destination taz
'''    
def runSurveyTripsPSRCtoBKRZones(surveyFileName):

    #read daysim trips file
    surveyFilePath = os.path.join(calibration_dir, surveyFileName)
    trips = readSurveyData(surveyFilePath, "Trip", ["otaz", "dtaz"])
    
    #pick a BKR otaz instead
    tripsByPSRCTAZ = trips.groupby("otaz").apply(pickTaz, tazField="otaz", zoneWeights=tazShares)
    tripsByPSRCTAZ = tripsByPSRCTAZ.reset_index(drop=True)
    tripsByPSRCTAZ = tripsByPSRCTAZ.sort_values("psrc_zone_id")

    trips["id"] = range(len(trips))
    trips = trips.sort_values("otaz")
    trips = trips.reset_index(drop=True)
    trips["otaz_new"] = tripsByPSRCTAZ.bkr_zone_id.tolist()
    trips["otaz"] = trips["otaz_new"].astype(np.int32)
    del trips["otaz_new"]
    trips = trips.sort_values("id")

    #pick a BKR dtaz instead
    tripsByPSRCTAZ = trips.groupby("dtaz").apply(pickTaz, tazField="dtaz", zoneWeights=tazShares)
    tripsByPSRCTAZ = tripsByPSRCTAZ.reset_index(drop=True)
    tripsByPSRCTAZ = tripsByPSRCTAZ.sort_values("psrc_zone_id")

    trips["id"] = range(len(trips))
    trips = trips.sort_values("dtaz")
    trips = trips.reset_index(drop=True)
    trips["dtaz_new"] = tripsByPSRCTAZ.bkr_zone_id.tolist()
    trips["dtaz"] = trips["dtaz_new"].astype(np.int32)
    del trips["dtaz_new"]
    trips = trips.sort_values("id")

    #write result file by copying input file and writing over arrays
    surveyOutFileName = surveyFileName.split(".")[0]+ "_bkr.h5"
    surveyOutFilePath = os.path.join(calibration_dir, surveyOutFileName)
    shutil.copy2(surveyFilePath, surveyOutFilePath)
    writeSurveyFields(surveyOutFilePath, trips, "Trip")

    return(surveyOutFileName)
'''
updates tours data in survey file
totaz - tour origina taz
tdtaz - tour destination taz
'''
def runSurveyToursPSRCtoBKRZones(surveyFileName):

    surveyFilePath = os.path.join(calibration_dir, surveyFileName)
    tours = readSurveyData(surveyFilePath, "Tour", ["totaz", "tdtaz"])
    
    #pick a BKR otaz instead
    toursByPSRCTAZ = tours.groupby("totaz").apply(pickTaz, tazField="totaz", zoneWeights=tazShares)
    toursByPSRCTAZ = toursByPSRCTAZ.reset_index(drop=True)
    toursByPSRCTAZ = toursByPSRCTAZ.sort_values("psrc_zone_id")

    tours["id"] = range(len(tours))
    tours = tours.sort_values("totaz")
    tours = tours.reset_index(drop=True)
    tours["totaz_new"] = toursByPSRCTAZ.bkr_zone_id.tolist()
    tours["totaz"] = tours["totaz_new"].astype(np.int32)
    del tours["totaz_new"]
    tours = tours.sort_values("id")

    #pick a BKR dtaz instead
    toursByPSRCTAZ = tours.groupby("tdtaz").apply(pickTaz, tazField="tdtaz", zoneWeights=tazShares)
    toursByPSRCTAZ = toursByPSRCTAZ.reset_index(drop=True)
    toursByPSRCTAZ = toursByPSRCTAZ.sort_values("psrc_zone_id")

    tours["id"] = range(len(tours))
    tours = tours.sort_values("tdtaz")
    tours = tours.reset_index(drop=True)
    tours["tdtaz_new"] = toursByPSRCTAZ.bkr_zone_id.tolist()
    tours["tdtaz"] = tours["tdtaz_new"].astype(np.int32)
    del tours["tdtaz_new"]
    tours = tours.sort_values("id")

    #write result file by copying input file and writing over arrays
    surveyOutFileName = surveyFileName.split(".")[0]+ "_tours.h5"
    surveyOutFilePath = os.path.join(calibration_dir, surveyOutFileName)
    shutil.copy2(surveyFilePath, surveyOutFilePath)
    writeSurveyFields(surveyOutFilePath, tours, "Tour")

    return(surveyOutFileName)

def runDistrictsPSRCtoBKRZones(zoneFileName):

    # read psrc zone group file
    zoneFileName = os.path.join(calibration_dir, zoneFileName)
    zoneDistricts = pd.read_csv(zoneFileName)
    colnames = list(zoneDistricts.columns.values)

    # merge psrc 2 bkr correspondence with percent
    tazGroups = pd.merge(tazShares,zoneDistricts, left_on = "psrc_zone_id", right_on = "TAZ")
    tazGroups["key"] = tazGroups["bkr_zone_id"].astype(str) + "_" + tazGroups["District"].astype(str)

    # group by unique pair of bkr zone and group
    tazGroups_grouped = tazGroups.groupby(["key"])

    # calculate sum of percent by unique pair
    tazGroups_sum = tazGroups_grouped['percent'].sum()
    tazGroups_sum = tazGroups_sum.reset_index() # makes object a data frame by setting the current index to a column

    temp = pd.merge(tazGroups_sum, tazGroups[["key","bkr_zone_id","TAD", "OldDistric", "County","District","New DistrictName"]], on = ["key"], how = "inner")

    #if one bkr in multiple groups, assign to the one with max percent value
    tazGroups_bkr = temp.loc[temp.groupby(["bkr_zone_id"])['percent'].idxmax()]

    #write
    outfile = zoneFileName.split(".")[0]+ "_bkr.csv"
    tazdata_bkr = tazGroups_bkr[["bkr_zone_id", "TAD", "OldDistric", "County","District","New DistrictName"]]
    tazdata_bkr = tazdata_bkr.rename(columns = {"bkr_zone_id":"TAZ"})
    tazdata_bkr.to_csv(outfile, sep = "," , header = True, index = False)

def runPSRCtoBKRFAZ(zoneFileName):

    # read psrc zone group file
    zoneFileName = os.path.join(calibration_dir, zoneFileName)
    zoneDistricts = pd.read_excel(zoneFileName)
    zoneDistricts = zoneDistricts[["zone_id","large_area_id","large_area_name"]]

    # merge psrc 2 bkr correspondence with percent
    tazGroups = pd.merge(tazShares,zoneDistricts, left_on = "psrc_zone_id", right_on = "zone_id")
    tazGroups["key"] = tazGroups["bkr_zone_id"].astype(str) + "_" + tazGroups["large_area_id"].astype(str)

    # group by unique pair of bkr zone and group
    tazGroups_grouped = tazGroups.groupby(["key"])

    # calculate sum of percent by unique pair
    tazGroups_sum = tazGroups_grouped['percent'].sum()
    tazGroups_sum = tazGroups_sum.reset_index() # makes object a data frame by setting the current index to a column

    temp = pd.merge(tazGroups_sum, tazGroups[["key","bkr_zone_id","zone_id","large_area_id","large_area_name"]], on = ["key"], how = "inner")

    #if one bkr in multiple groups, assign to the one with max percent value
    tazGroups_bkr = temp.loc[temp.groupby(["bkr_zone_id"])['percent'].idxmax()]

    #write
    outfile = zoneFileName.split(".")[0]+ "_bkr.xlsx"
    tazdata_bkr = tazGroups_bkr[["bkr_zone_id","large_area_id","large_area_name"]]
    tazdata_bkr = tazdata_bkr.rename(columns = {"bkr_zone_id":"zone_id"})
    tazdata_bkr.to_excel(outfile, 'taz4k_to_fazlarge_area', index=False)
    
def runPSRCtoBKRDistrictLookup(zoneFileName):

    # read psrc zone group file
    zoneFileName = os.path.join(calibration_dir, zoneFileName)
    zoneDistricts = pd.read_csv(zoneFileName)
    colnames = list(zoneDistricts.columns.values)

    # merge psrc 2 bkr correspondence with percent
    tazGroups = pd.merge(tazShares,zoneDistricts, left_on = "psrc_zone_id", right_on = "taz")
    tazGroups["key"] = tazGroups["bkr_zone_id"].astype(str) + "_" + tazGroups["district"].astype(str)

    # group by unique pair of bkr zone and group
    tazGroups_grouped = tazGroups.groupby(["key"])

    # calculate sum of percent by unique pair
    tazGroups_sum = tazGroups_grouped['percent'].sum()
    tazGroups_sum = tazGroups_sum.reset_index() # makes object a data frame by setting the current index to a column

    temp = pd.merge(tazGroups_sum, tazGroups[["key","bkr_zone_id","tad", "county","district","district_name","lat_taz","lon_taz","TAZ","lat_district","lon_district"]], on = ["key"], how = "inner")

    #if one bkr in multiple groups, assign to the one with max percent value
    tazGroups_bkr = temp.loc[temp.groupby(["bkr_zone_id"])['percent'].idxmax()]

    #add taz lat long
    zoneLatLongFile = os.path.join(os.getcwd(), zoneLatLongFileName)
    zoneLatLong = pd.read_csv(zoneLatLongFile)
    tazGroups_bkr = pd.merge(tazGroups_bkr, zoneLatLong, left_on = "bkr_zone_id", right_on = "TAZNUM")

    #write
    outfile = zoneFileName.split(".")[0]+ "_bkr.csv"
    tazdata_bkr = tazGroups_bkr[["bkr_zone_id","tad", "county","district","district_name","lat","long","TAZ","lat_district","lon_district"]]
    tazdata_bkr['TAZ'] = tazdata_bkr['bkr_zone_id']
    tazdata_bkr = tazdata_bkr.rename(columns = {"bkr_zone_id":"taz", "lat":"lat_taz", "long":"lon_taz"})
    tazdata_bkr.to_csv(outfile, sep = "," , header = True, index = False)

def readSynPopTables(fileName):
    print('read synpop file')
    popsyn = h5py.File(fileName)
    hhFields = map(lambda x: x[0], popsyn.get("Household").items())
    perFields = map(lambda x: x[0], popsyn.get("Person").items())
    
    #build pandas data frames
    #hhFields.remove('incomeconverted') #not a column attribute
    hhTable = pd.DataFrame()
    for hhField in hhFields:
        hhTable[hhField] = popsyn.get("Household").get(hhField)[:]

    perTable = pd.DataFrame()
    for perField in perFields:
        perTable[perField] = popsyn.get("Person").get(perField)[:]

    return(hhTable, perTable)

def writeSynPopTables(fileName, households, persons):
    print('write synpop file')
    #delete columns first and then write
    popsyn = h5py.File(fileName, "a")
    for hhField in households.columns:
        dataset = "Household/" + hhField
        print(dataset)
        del popsyn[dataset]
        popsyn.create_dataset(dataset, data = households[hhField],compression="gzip")
    for perField in persons.columns:
        dataset = "Person/" + perField
        print(dataset)
        del popsyn[dataset]
        popsyn.create_dataset(dataset, data = persons[perField], compression="gzip")
    popsyn.close()
    
'''
updates household and person data in survey file

household
-hhtaz

person
-pwtaz
-pstaz
'''

def runSurveyPopPSRCtoBKRZones(surveyFileName, parcelFileName):

    #read popsyn file
    surveyFilePath = os.path.join(calibration_dir, surveyFileName)
    households, persons = readSynPopTables(surveyFilePath)

    #get parcle-taz correspondence
    parcelFileName = os.path.join(inputs_dir, parcelFileName)
    parcels = pd.read_table(parcelFileName, sep=" ")
    parcels = parcels[["parcelid","taz_p"]]

    #merge to households
    print('assign bkr tazs to household')
    households = pd.merge(households, parcels, left_on = "hhparcel", right_on = "parcelid")
    
    households["hhtaz"] = households["taz_p"].astype(np.int32)
    households.drop(["parcelid","taz_p"], inplace=True, axis=1)
    
    households = households.sort_values("hhno")

    #update persons - student taz
    print('assign bkr tazs to persons')
    persons = pd.merge(persons, parcels, left_on = "pspcl", right_on = "parcelid", how = 'left')
    persons["taz_p"] = persons["taz_p"].fillna(-1)
    persons["pstaz"] = persons["taz_p"].astype(np.int32)
    persons.drop(["parcelid","taz_p"], inplace=True, axis=1)

    #update persons - worker taz
    persons = pd.merge(persons, parcels, left_on = "pwpcl", right_on = "parcelid", how = 'left')
    persons["taz_p"] = persons["taz_p"].fillna(-1)
    persons["pwtaz"] = persons["taz_p"].astype(np.int32)
    persons.drop(["parcelid","taz_p"], inplace=True, axis=1)

    #write result file by copying input file and writing over arrays
    surveyOutFileName = surveyFileName.split(".")[0]+ "_popsyn.h5"
    surveyOutFilePath = os.path.join(calibration_dir, surveyOutFileName)
    shutil.copy2(surveyFilePath, surveyOutFilePath)
    writeSynPopTables(surveyOutFilePath, households, persons)

    return(surveyOutFileName)

def convertSurveyToDaysimFormat(surveyFileName):
    print("convert survey data to daysim format")
    popsyn = h5py.File(os.path.join(calibration_dir, surveyFileName))

    #groups in the survey file
    groups = ["Household", "Person", "Trip", "Tour", "PersonDay", "HouseholdDay"]

    # convert to .dat format
    for group in groups:
        print(group)
        fields = map(lambda x: x[0], popsyn.get(group).items())
        groupTable = pd.DataFrame()
        for field in fields:
            print(field)
            groupTable[field] = popsyn.get(group).get(field)[:]
        
        groupTable.to_csv(os.path.join(calibration_dir, group+"_bkr.dat"), sep = " ", index = False)

    print("finished converting to daysim format")

if __name__== "__main__":
    if(runSurveyFile):
        runDistrictsPSRCtoBKRZones(zone_file)
        runPSRCtoBKRFAZ(faz_file)
        runPSRCtoBKRDistrictLookup(district_lookup_file)
        survey_file_new = runSurveyTripsPSRCtoBKRZones(survey_file)
        survey_file_new = runSurveyToursPSRCtoBKRZones(survey_file_new)
        survey_file_new = runSurveyPopPSRCtoBKRZones(survey_file_new, parcel_file)

    if(runDaySimFormat):
        convertSurveyToDaysimFormat(survey_file_new)

