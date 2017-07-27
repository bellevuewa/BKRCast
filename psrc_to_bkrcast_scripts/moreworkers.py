
#More Workers in the SynPop by TAZ (and less persons in non-worker hhs as a result)
#python moreworkers.py taz_sample_rate.txt hh_and_persons.h5 hh_and_persons_more_workers.h5
#Ben Stabler, ben.stabler@rsginc.com, 07/19/17

import os, sys, shutil
import pandas as pd
import h5py
import numpy as np
pd.options.mode.chained_assignment = None  # turn off SettingWithCopyWarning

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

def scale_hhs(group):
    
    num_persons_hh_with_workers_before = (group['hhsize'][group['NUM_WORKERS']>0] * group['hhexpfac'][group['NUM_WORKERS']>0]).sum()
    num_persons_hh_no_workers_before = (group['hhsize'][group['NUM_WORKERS']==0] * group['hhexpfac'][group['NUM_WORKERS']==0]).sum()

    group['hhexpfac'][group['NUM_WORKERS']>0] = group['workers_factor'][group['NUM_WORKERS']>0]
    
    num_persons_hh_with_workers_after = (group['hhsize'][group['NUM_WORKERS']>0] * group['hhexpfac'][group['NUM_WORKERS']>0]).sum()
    num_new_persons = num_persons_hh_with_workers_after - num_persons_hh_with_workers_before
    
    group['hhexpfac'][group['NUM_WORKERS']==0] = max(0, 1 - ( num_new_persons / num_persons_hh_no_workers_before )) #cap at 0

    num_persons_hh_no_workers_after = (group['hhsize'][group['NUM_WORKERS']==0] * group['hhexpfac'][group['NUM_WORKERS']==0]).sum()

    print("taz %5i p_hh_wkr_b %5i p_h_wkr_a %5i p_hh_nw_b %5i p_hh_nw_a %5i" % (group['hhtaz'].min(), num_persons_hh_with_workers_before, num_persons_hh_with_workers_after, num_persons_hh_no_workers_before, num_persons_hh_no_workers_after))

    return(group)

def runMoreWorkers(tazSampleRateFileName, popsynFileName, popsynOutFileName):

    #get tables
    #tazSampleRateFileName = "taz_sample_rate.txt" #taz, district, workers_factor
    sampleRates = pd.read_table(tazSampleRateFileName)

    #popsynFileName = "hh_and_persons.h5"
    households, persons = readSynPopTables(popsynFileName)

    #join sample rate by home taz
    households = pd.merge(households, sampleRates, left_on="hhtaz", right_on="taz")

    #identify households with workers
    hasWorkers = persons[(persons['pptyp'] == 1) | (persons['pptyp'] == 2)].hhno.value_counts()
    hasWorkers.name = "NUM_WORKERS"
    households.set_index('hhno', drop=False, inplace=True)
    households = households.join(hasWorkers)
    households['NUM_WORKERS'][households['NUM_WORKERS'].isnull()] = 0

    #group hhs by hhtaz and calculate adjustment
    hhsGrouped = households.groupby("hhtaz")
    new_households = hhsGrouped.apply(scale_hhs)
    new_households = new_households.reset_index(drop=True)
    
    print("num workers before: %i" % ((households['NUM_WORKERS'] * households['hhexpfac']).sum()))
    print("num workers after: %i" % ((new_households['NUM_WORKERS'] * new_households['hhexpfac']).sum()))

    print("num persons before: %i" % ((households['hhsize'] * households['hhexpfac']).sum()))
    print("num persons after: %i" % ((new_households['hhsize'] * new_households['hhexpfac']).sum()))

    #delete added fields
    del new_households['taz']
    del new_households['district']
    del new_households['workers_factor']
    del new_households['NUM_WORKERS']
    
    #write result file by copying input file and writing over arrays
    #popsynOutFileName = "hh_and_persons_sampled.h5"
    shutil.copy2(popsynFileName, popsynOutFileName)
    writeSynPopTables(popsynOutFileName, new_households, persons)

if __name__== "__main__":
    #set argument inputs
    taz_sample_rate_file = sys.argv[1]
    popsyn_file = sys.argv[2]
    popsyn_out_file = sys.argv[3]
    
    print(taz_sample_rate_file)
    print(popsyn_file)
    print(popsyn_out_file)

    #run more workers
    runMoreWorkers(taz_sample_rate_file, popsyn_file, popsyn_out_file)
