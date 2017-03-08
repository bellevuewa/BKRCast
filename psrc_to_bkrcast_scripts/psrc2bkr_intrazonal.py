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

# inputs
wd = r"E:\Projects\Clients\bkr\model\soundcast\inputs\IntraZonals"
files_list = ["origin_tt.in", "destination_tt.in"]
file_termtime = r'E:\Projects\Clients\bkr\data\frombkr\Network\network updates\bkrcast_autoterminaltime.csv'
    
def runPSRCtoBKRZones():

    #read terminal times
    auto_tt = pd.read_csv(file_termtime)

    #number of rows in the begining of the file before the actual data - user input
    header_rows = [5, 5]

    for i in range(0, len(files_list)):
        file = files_list[i]
        print "updating: " + file

        #psrc file
        psrcFileName = file
        psrcFileName = os.path.join(wd, psrcFileName)

        #read header - use "#" as seperator as it is less likely to present in the file
        header = pd.read_table(psrcFileName, delimiter = "#", header = None, nrows = header_rows[i])
        
        #initialize taz index file
        tazdata_bkr = pd.DataFrame(index = range(1,1531), columns = ["Zone_id", "c", "termtime"])
        tazdata_bkr = tazdata_bkr.fillna(0)

        #set terminal times - internal: 1 min, external = 3 mins, external = 30 mins
        for j in range(1,1531):
            tazdata_bkr["Zone_id"][j] = j

            if(False):
                if (i<=1355):
                    tazdata_bkr["termtime"][j] = 1        
                elif (i<=1510):
                    tazdata_bkr["termtime"][j] = 3           
                else:
                    tazdata_bkr["termtime"][j] = 30           

        tazdata_bkr = pd.merge(tazdata_bkr, auto_tt, left_on = 'Zone_id', right_on = 'TAZNUM', how = 'left')
        tazdata_bkr['termtime'] = tazdata_bkr['AutoTermTime']
        tazdata_bkr = tazdata_bkr.fillna(0)
        tazdata_bkr = tazdata_bkr[["Zone_id", "c", "termtime"]]

        if i==0: #origin file
            tazdata_bkr["c"] = "all:"
        else: #destination file
            tazdata_bkr["c"] = " all" #space before the word 'all' is intentional, the model throws an error if space is not there
            tazdata_bkr["Zone_id"] = tazdata_bkr["Zone_id"].astype(np.str) + ":"
            tazdata_bkr = tazdata_bkr[["c", "Zone_id", "termtime"]]
                        
        # write - first header and then append the updated data
        outfile = psrcFileName.split(".")[0]
        outfile = outfile + "_bkr.in"
        header.to_csv(outfile, sep = " ", header = False, index = False, quoting=csv.QUOTE_NONE, escapechar = " ") #had to add space as escapechar otherwise throws an error

        with open(outfile, 'a') as file:
            tazdata_bkr.to_csv(file, sep = " " , header = False, index = False)

if __name__== "__main__":
    runPSRCtoBKRZones()

