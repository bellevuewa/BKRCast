
#Synthetic Population Spatial Sampler Routine
#Ben Stabler, ben.stabler@rsginc.com, 08/29/16

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import os, sys, shutil
import pandas as pd
import h5py
import numpy as np
sys.path.append(os.path.join(os.getcwd(),"inputs"))
from input_configuration import *

def readSynPopTables(fileName):
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
    
    #delete columns first and then write
    popsyn = h5py.File(fileName, "a")
    for hhField in households.columns:
        dataset = "Household/" + hhField
        del popsyn[dataset]
        popsyn.create_dataset(dataset, data = households[hhField],compression="gzip")
    for perField in persons.columns:
        dataset = "Person/" + perField
        del popsyn[dataset]
        popsyn.create_dataset(dataset, data = persons[perField], compression="gzip")
    popsyn.close()

def sample_hhs(group):
    #sample using the taz sample rate with replacement and a stable group seed
    seed = group.hhtaz.min()*100 + group.hhincbin.min()*10 + group.hhsizebin.min()
    sample = group.sample(frac=group.sample_rate.min(), replace=True, random_state=seed)
        
    if len(sample)==0:
        print('sample is empty')
        sample = group
    else:
        #set hh expansion factor based on actual sample size since sampling is lumpy
        sample.hhexpfac = 1.0 / (len(sample)*1.0/len(group))           

    print("hhtaz %i hhincbin %s hhsizebin %s sample rate %.2f effective rate %.2f" % (group.hhtaz.min(), group.hhincbin.min(), group.hhsizebin.min(), group.sample_rate.min(), 1.0 / sample.hhexpfac.min()))
    return(sample)

def runPopSampler(tazSampleRateFileName, popsynFileName, popsynOutFileName):

    #get tables
    #tazSampleRateFileName = "taz_sample_rate.txt" #TAZ, SampleRate 1.0=100%
    tazSampleRateFileName = os.path.join(main_inputs_folder, tazSampleRateFileName)
    sampleRates = pd.read_table(tazSampleRateFileName)

    #popsynFileName = "hh_and_persons.h5"
    popsynFileName = os.path.join(main_inputs_folder, popsynFileName)
    households, persons = readSynPopTables(popsynFileName)

    #join sample rate by home taz
    households = pd.merge(households, sampleRates, left_on="hhtaz", right_on="zone_id")

    #bin hhs by income and size
    incbins = [-1, 50000, 100000, households['hhincome'].max()+1]
    households['hhincbin'] = pd.cut(households['hhincome'], incbins, labels=False)
    sizebins = [-1, 1, 2, 3, households['hhsize'].max()+1]
    households['hhsizebin'] = pd.cut(households['hhsize'], sizebins, labels=False)    

    #group hhs by taz, hhincbin, hhsizebin and sample and reset index
    hhsGrouped = households.groupby(["hhtaz","hhincbin","hhsizebin"])
    new_households = hhsGrouped.apply(sample_hhs)
    new_households = new_households.reset_index(drop=True)
    
    #update ids and expand persons
    new_households['hhno_new'] = range(1,len(new_households)+1)
    new_persons = pd.merge(persons, new_households[["hhno","hhno_new"]], left_on="hhno", right_on="hhno", )
    new_households['hhno'] = new_households['hhno_new'].astype(np.int32)
    new_persons['hhno'] = new_persons['hhno_new'].astype(np.int32)

    #delete added fields
    del new_households['hhno_new']
    del new_households['zone_id']
    del new_households['sample_rate']
    del new_households['hhincbin']
    del new_households['hhsizebin']
    del new_persons['hhno_new']
    
    #write result file by copying input file and writing over arrays
    #popsynOutFileName = "hh_and_persons_sampled.h5"
    popsynOutFileName = os.path.join(main_inputs_folder, popsynOutFileName)
    shutil.copy2(popsynFileName, popsynOutFileName)
    writeSynPopTables(popsynOutFileName, new_households, new_persons)

if __name__== "__main__":
    #set argument inputs
    taz_sample_rate_file = sys.argv[1]
    popsyn_file = sys.argv[2]
    popsyn_out_file = sys.argv[3]
    
    print(taz_sample_rate_file)
    print(popsyn_file)
    print(popsyn_out_file)

    #run popsampler
    runPopSampler(taz_sample_rate_file, popsyn_file, popsyn_out_file)
