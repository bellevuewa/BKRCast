#Convert PSRC zones to BKR zones (one to one relation - take the max area)
#Nagendra Dhakar, nagendra.dhakar@rsginc.com, 09/21/16

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
import csv

# working directory
wd = r"E:\Projects\Clients\bkr\model\soundcast\inputs\trucks"

# flags to convert specific inputs
runSpclGen = True
runExt = True
runTruck = True
runShares = True
runEmp = True

#input files
files_truck = ["trucks.in"]
files_spclgen = ["special_gen_light_trucks.in", "special_gen_medium_trucks.in", "special_gen_heavy_trucks.in"] #special generator truck input files
files_ext = [ "medium_trucks_ei.in", "medium_trucks_ie.in", "medium_trucks_ee.in", "heavy_trucks_ei.in", "heavy_trucks_ie.in", "heavy_trucks_ee.in"]#external truck input files
files_manu_shares = ["agshar.in","minshar.in","prodshar.in","equipshar.in"]
file_wtcu_shares = ["tcushar.in","whlsshar.in"]
files_emp = ["hhemp","const.in"]
tazSharesFileName = "psrc_to_bkr.txt" #format: psrc_zone_id,bkr_zone_id,percent(1.0=100%)

# read correspondence file
tazSharesFileName = os.path.join(os.getcwd(), tazSharesFileName)
tazShares = pd.read_table(tazSharesFileName)

def expandTazShares(table):
    
    print("expand PSRC to BKR zone crosswalk to full OD percents table")

    #replicate into expanded OD table
    od_table = pd.DataFrame()
    od_table["o"] = np.repeat(table["psrc_zone_id"].tolist(),len(table))
    od_table["bkr_o"] = np.repeat(table["bkr_zone_id"].tolist(),len(table))
    od_table["percent_o"] = np.repeat(table["percent"].tolist(),len(table))
    od_table["d"] = np.tile(table["psrc_zone_id"].tolist(),len(table))
    od_table["bkr_d"] = np.tile(table["bkr_zone_id"].tolist(),len(table))
    od_table["percent_d"] = np.tile(table["percent"].tolist(),len(table))
    
    #calculat the share by OD group
    od_table["od"] = od_table["o"] * 10000 + od_table["d"]
    od_table["percent"] = od_table["percent_o"] * od_table["percent_d"]

    return(od_table)

def runSpclGenPSRCtoBKRZones():

    #number of rows in the begining of the file before the actual data - user input
    header_rows = [5, 5, 9]

    for i in range(0, len(files_spclgen)):
        file = files_spclgen[i]
        print "updating: " + file

        #psrc file
        psrcFileName = file
        psrcFileName = os.path.join(wd, psrcFileName)

        #read header - use "#" as seperator as it is less likely to present in the file
        header = pd.read_table(psrcFileName, delimiter = "#", header = None, nrows = header_rows[i]) 
        
        # skip first few rows, as they contain general information - also ignore rows starting with 'c' (comment lines)
        truck_psrc = pd.read_table(psrcFileName, delimiter = " ", names = ["c","psrc_zone_id","corridor"], comment = "c", skiprows = header_rows[i])
        print("PSRC sum: " + str(truck_psrc.corridor.sum()))

        # merge psrc to bkr correspondence with percent
        tazGroups = pd.merge(truck_psrc, tazShares, left_on = "psrc_zone_id", right_on = "psrc_zone_id")
        tazGroups["corridor"] = tazGroups["corridor"] * tazGroups["percent"]

        # group by unique pair of bkr zone and group
        tazGroups_grouped = tazGroups.groupby(["bkr_zone_id"])

        # calculate sum of percent by unique pair
        tazGroups_sum = tazGroups_grouped['corridor'].sum()
        tazGroups_sum = tazGroups_sum.reset_index() # makes object a data frame by setting the current index to a column
        tazGroups_sum["c"] = "all:"
        tazGroups_bkr = tazGroups_sum[["c","bkr_zone_id", "corridor"]]
        print("BKR sum: " + str(tazGroups_bkr.corridor.sum()))

        # write - first header and then append the updated data
        outfile = psrcFileName.split(".")[0]
        outfile = outfile + "_bkr.in"
        header.to_csv(outfile, sep = " ", header = False, index = False, quoting=csv.QUOTE_NONE, escapechar = " ") #had to add space as escapechar otherwise throws an error - not sure if that would cause any issue in the mdoel

        with open(outfile, 'a') as file:
            tazGroups_bkr.to_csv(file, sep = " " , header = False, index = False)
    
def runTruckPSRCtoBKRZones():

    #number of rows in the begining of the file before the actual data - user input
    header_rows = [3]

    for i in range(0, len(files_truck)):
        file = files_truck[i]
        print "updating: " + file

        #psrc file
        psrcFileName = file
        psrcFileName = os.path.join(wd, psrcFileName)

        #read header - use "#" as seperator as it is less likely to present in the file
        header = pd.read_table(psrcFileName, delimiter = "#", header = None, nrows = header_rows[i]) 
        
        # skip first few rows, as they contain general information - also ignore rows starting with 'c' (comment lines)
        truck_psrc = pd.read_table(psrcFileName, delimiter = " ", names = ["psrc_zone_id", "c", "flag"], comment = "c", skiprows = header_rows[i])
        print("PSRC sum: " + str(truck_psrc.flag.sum()))

        # merge psrc to bkr correspondence with percent
        tazGroups = pd.merge(truck_psrc, tazShares, left_on = "psrc_zone_id", right_on = "psrc_zone_id")

        # group by unique pair of bkr zone and group
        tazGroups_grouped = tazGroups.groupby(["bkr_zone_id"])

        # calculate sum of percent by unique pair
        tazGroups_sum = tazGroups_grouped['flag'].sum()
        tazGroups_sum = tazGroups_sum.reset_index() # makes object a data frame by setting the current index to a column
        tazGroups_sum["c"] = "all:"
        tazGroups_sum["flag"] = 1
        #temp = tazGroups_sum.ix[tazGroups_sum["flag"]>0]

        tazGroups_bkr = tazGroups_sum[["bkr_zone_id", "c", "flag"]]
        print("BKR sum: " + str(tazGroups_bkr.flag.sum()))

        # write - first header and then append the updated data
        outfile = psrcFileName.split(".")[0]
        outfile = outfile + "_bkr.in"
        header.to_csv(outfile, sep = " ", header = False, index = False, quoting=csv.QUOTE_NONE, escapechar = " ") #had to add space as escapechar otherwise throws an error - not sure if that would cause any issue in the mdoel

        with open(outfile, 'a') as file:
            tazGroups_bkr.to_csv(file, sep = " " , header = False, index = False)

def runExtPSRCtoBKRZones():

    # expand taz shares
    odShares = expandTazShares(tazShares)

    #number of rows in the begining of the file before the actual data - user input
    header_rows = [5, 5, 5, 9, 9, 5]

    for i in range(0, len(files_ext)):
        file = files_ext[i]
        print("updating: " + file)

        #psrc file
        psrcFileName = file
        psrcFileName = os.path.join(wd, psrcFileName)

        #read header - use "#" as seperator as it is less likely to present in the file
        header = pd.read_table(psrcFileName, delimiter = "#", header = None, nrows = header_rows[i]) 
        
        # skip first few rows, as they contain general information - also ignore rows starting with 'c' (comment lines)
        truck_psrc = pd.read_table(psrcFileName, delimiter = " ", names = ["o","d","trips"], comment = "c", skiprows = header_rows[i])
        print("PSRC sum: " + str(truck_psrc.trips.sum()))

        #remove ":" from the destination taz
        truck_psrc["d"] = truck_psrc["d"].str.split(":",1).str[0].astype(np.int)

        #join BKR zone shares - keep all od pairs that are common in both data frames, using how = "inner" (also default)         
        print("join BKR zone shares to matrices")
        od_table = pd.merge(truck_psrc, odShares, on=["o","d"], how = "left")
        od_table["trips"] = od_table["trips"] * od_table["percent"]

        #od_table["od"] = od_table["bkr_o"] * 10000 + od_table["bkr_d"]
        od_table_grouped = od_table.groupby(["bkr_o", "bkr_d"])
        od_table_sums = od_table_grouped["trips"].sum()
        #od_table_sums["bkr_od"] = od_table_sums.index
        od_table_sums = od_table_sums.reset_index()

        od_table_sums["bkr_d"] = od_table_sums["bkr_d"].astype(np.str) + ":"

        tazGroups_bkr = od_table_sums[["bkr_o", "bkr_d", "trips"]]
        print("BKR sum: " + str(tazGroups_bkr.trips.sum()))

        # write - first header and then append the updated data
        outfile = psrcFileName.split(".")[0]
        outfile = outfile + "_bkr.in"
        header.to_csv(outfile, sep = " ", header = False, index = False, quoting=csv.QUOTE_NONE, escapechar = " ") #had to add space as escapechar otherwise throws an error - not sure if that would cause any issue in the mdoel

        with open(outfile, 'a') as file:
            tazGroups_bkr.to_csv(file, sep = " " , header = False, index = False)

def runSharesPSRCToBKRZones():
    #list of two lists
    files_shares = [files_manu_shares, file_wtcu_shares]
    header_rows = 3 #number of rows at the begining of a file with header information

    headers = {} #dictionary to save header information
    for files_group in files_shares:
        for file in files_group:
            print("working on file: " + file)
            file_path = os.path.join(wd, file)

            #read header - use "#" as seperator as it is less likely to present in the file
            headers[file] = pd.read_table(file_path, delimiter = "#", header = None, nrows = header_rows) 
        
            # skip first few rows, as they contain general information - also ignore rows starting with 'c' (comment lines)
            shares_psrc = pd.read_table(file_path, delimiter = " ", names = ["o","d",file], comment = "c", skiprows = header_rows)

            if file == files_group[0]:
                #if first file in the group, set to the file shares
                truck_shares_psrc = shares_psrc
            else:
                #add a new column for a new file
                truck_shares_psrc = pd.merge(truck_shares_psrc, shares_psrc, on = ["o","d"])

        # merge psrc to bkr correspondence with percent
        tazGroups = pd.merge(truck_shares_psrc, tazShares, left_on = "o", right_on = "psrc_zone_id")
        tazGroups[file] = tazGroups[file] * tazGroups["percent"]

        # group by unique pair of bkr zone and group
        tazGroups_grouped = tazGroups.groupby(["bkr_zone_id"])

        # calculate sum of percent by unique pair
        tazGroups_sum = tazGroups_grouped[files_group].sum()
        tazGroups_sum['sum'] = tazGroups_sum[files_group].sum(axis=1)

        for file in files_group:
            tazGroups_sum[file] *= 1/tazGroups_sum['sum'] 

        tazGroups_sum['sum'] = tazGroups_sum[files_group].sum(axis=1)
        tazGroups_sum =  tazGroups_sum.round(4) #round values to 4 decimal

        #temp = tazGroups_sum.ix[tazGroups_sum["sum"]>1.0] #debug: to find out rows that have sum value more than 1

        tazGroups_sum = tazGroups_sum[files_group].reset_index() # makes object a data frame by setting the current index to a column
        tazGroups_sum["c"] = "all:"

        for file in files_group:
            tazGroups_bkr = tazGroups_sum[["bkr_zone_id", "c", file]]
            tazGroups_bkr = tazGroups_bkr.sort_values(by = ['bkr_zone_id'], ascending=[True])

            # write - first header and then append the updated data
            outfile = file.split(".")[0]
            outfile = os.path.join(wd, outfile + "_bkr.in")

            #first write header
            headers[file].to_csv(outfile, sep = " ", header = False, index = False, quoting=csv.QUOTE_NONE, escapechar = " ") #had to add space as escapechar otherwise throws an error - not sure if that would cause any issue in the mdoel

            #write data
            with open(outfile, 'a') as wfile:
                tazGroups_bkr.to_csv(wfile, sep = " " , header = False, index = False)

def runEmpPSRCToBKRZones():
    #list of two lists
    header_rows = [5,3] #number of rows at the begining of a file with header information
    #files_emp = ["hhemp"] #debug
    headers = {} #dictionary to save header information
    i=0
    for file in files_emp:
        print("working on file: " + file)
        file_path = os.path.join(wd, file)

        #read header - use "#" as seperator as it is less likely to present in the file
        headers[file] = pd.read_table(file_path, delimiter = "#", header = None, nrows = header_rows[i])
             
        # skip first few rows, as they contain general information - also ignore rows starting with 'c' (comment lines)
        truck_emp_psrc = pd.read_table(file_path, sep='\s+', names = ["o","d",file], comment = "c", skiprows = header_rows[i])

        # merge psrc to bkr correspondence with percent
        tazGroups = pd.merge(truck_emp_psrc, tazShares, left_on = "o", right_on = "psrc_zone_id", how = 'left')
        tazGroups[file] = tazGroups[file] * tazGroups["percent"]

        tazGroups_grouped = tazGroups.groupby(["bkr_zone_id", "d"])

        # group by unique pair of bkr zone and group
        #if file == "hhemp":
        #    tazGroups_grouped = tazGroups.groupby(["bkr_zone_id", "d"])
        #else:
        #    tazGroups_grouped = tazGroups.groupby(["bkr_zone_id"])

        # calculate sum of percent by unique pair
        tazGroups_sum = tazGroups_grouped[file].sum()

        tazGroups_sum = tazGroups_sum.reset_index() # makes object a data frame by setting the current index to a column
        if file == "const.in":
            tazGroups_sum["d"] = "all:"

        tazGroups_bkr = tazGroups_sum[["bkr_zone_id", "d", file]]
        
        tazGroups_bkr = tazGroups_bkr.sort_values(by = ['bkr_zone_id','d'], ascending=[True, True])

        # write - first header and then append the updated data
        outfile = file.split(".")[0]
        outfile = os.path.join(wd, outfile + "_bkr.in")

        #first write header
        headers[file].to_csv(outfile, sep = " ", header = False, index = False, quoting=csv.QUOTE_NONE, escapechar = " ") #had to add space as escapechar otherwise throws an error - not sure if that would cause any issue in the mdoel

        #write data
        with open(outfile, 'a') as wfile:
            tazGroups_bkr.to_csv(wfile, sep = " " , header = False, index = False)

        i += 1

if __name__== "__main__":
    if(runSpclGen):
        runSpclGenPSRCtoBKRZones()
    if(runExt):
        runExtPSRCtoBKRZones()
    if(runTruck):
        runTruckPSRCtoBKRZones()
    if(runShares):
        runSharesPSRCToBKRZones()
    if(runEmp):
        runEmpPSRCToBKRZones()

