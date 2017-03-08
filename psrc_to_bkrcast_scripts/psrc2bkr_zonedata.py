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


# NOTE:
# Added special generator data manually
# copy pasted thecorresponding zone data in soundacast

# inputs
wd = r"E:\Projects\Clients\bkr\model\soundcast\inputs\supplemental\generation\landuse"
files_zone = ["tazdata.in"]
tazSharesFileName = "psrc_to_bkr.txt"

# read correspondence file
tazSharesFileName = os.path.join(os.getcwd(), tazSharesFileName)
tazShares = pd.read_table(tazSharesFileName)

def runPSRCtoBKRZones():

    #number of rows in the begining of the file before the actual data - user input
    header_rows = [4]
    num_bkr_zones = 1359 #internal: 1-1355; special generators: 1356-1359

    for i in range(0, len(files_zone)):
        file = files_zone[i]
        print "updating: " + file

        #psrc file
        psrcFileName = file
        psrcFileName = os.path.join(wd, psrcFileName)

        #read header - use "#" as seperator as it is less likely to present in the file
        header = pd.read_table(psrcFileName, delimiter = "#", header = None, nrows = header_rows[i]) 
        
        # skip first few rows, as they contain general information - also ignore rows starting with 'c' (comment lines)
        data_psrc = pd.read_table(psrcFileName, delimiter = " ", names = ["o","group","value"], comment = "c", skiprows = header_rows[i])
        print("PSRC sum: " + str(data_psrc.value.sum()))

        # merge psrc to bkr correspondence with percent
        tazGroups = pd.merge(data_psrc, tazShares, left_on = "o", right_on = "psrc_zone_id")
        tazGroups["value"] = tazGroups["value"] * tazGroups["percent"]

        # group by unique pair of bkr zone and group
        tazGroups_grouped = tazGroups.groupby(["bkr_zone_id", "group"])

        # calculate sum of percent by unique pair
        tazGroups_sum = tazGroups_grouped['value'].sum()
        tazGroups_sum = tazGroups_sum.reset_index() # makes object a data frame by setting the current index to a column

        groups = tazGroups_sum.group.unique()

        #initialize bkr data frame
        data_bkr  = pd.DataFrame()
        data_bkr["o"]  = np.repeat(range(1,num_bkr_zones+1), len(groups))
        data_bkr["group"] = np.tile(groups, num_bkr_zones)

        data_bkr = pd.merge(data_bkr, tazGroups_sum, left_on = ["o","group"], right_on = ["bkr_zone_id", "group"], how = "left")
        data_bkr["value"].fillna(0, inplace = True)
        data_bkr = data_bkr[["o", "group", "value"]]
        print("BKR sum: " + str(data_bkr.value.sum()))

        # write - first header and then append the updated data
        outfile = psrcFileName.split(".")[0]
        outfile = outfile + "_bkr.in"
        header.to_csv(outfile, sep = " ", header = False, index = False, quoting=csv.QUOTE_NONE, escapechar = " ") #had to add space as escapechar otherwise throws an error - not sure if that would cause any issue in the mdoel

        with open(outfile, 'a') as file:
            data_bkr.to_csv(file, sep = " " , header = False, index = False)
    

if __name__== "__main__":
    runPSRCtoBKRZones()

