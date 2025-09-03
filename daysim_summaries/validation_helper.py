

import logging
import numpy as np
import pandas as pd

from input_configuration import base_year
from config import dataset

WORKER_TYPE_MAP = {#pptyp: wrkrtyp
                   1: 1, 
                   2: 2, 
                   3: 3, 
                   4: 3, 
                   5: 3, 
                   6: 3, 
                   7: 3, 
                   8: 3}

STUDENT_TYPE_MAP = {#pptyp: stutyp
                    1: 4, 
                    2: 4, 
                    3: 4, 
                    4: 4, 
                    5: 3, 
                    6: 2, 
                    7: 1, 
                    8: 4}


def prep_wrkschloc(perdata: pd.DataFrame, 
                   hhdata: pd.DataFrame, 
                   countycorr: pd.DataFrame,
                   max_distance_bin=90,  #(-inf,0], (0,1], (1,2], ... (88,89], (89,inf)
                   max_time_bin=90,  #(-inf,0], (0,1], (1,2], ... (88,89], (89,inf)
                   ) -> pd.DataFrame:
    
    perdata = perdata.merge(hhdata, on="hhno", how="left")
    
    perdata["wrkr"] = np.where((perdata["pwtyp"] > 0) & (perdata["pwtaz"] != 0), 1, 0)
    perdata["outhmwrkr"] = np.where((perdata["pwtaz"] > 0) & (perdata["hhparcel"] != perdata["pwpcl"]), 1, 0)
    
    perdata["wrkrtyp"] = perdata["pptyp"].map(WORKER_TYPE_MAP)

    distance_bins = np.arange(0, max_distance_bin)  # (-inf,0], (0,1], (1,2], ... (88,89], (89,inf)
    time_bins = np.arange(0, max_time_bin)  # (-inf,0], (0,1], (1,2], ... (88,89], (89,inf)
    perdata["wrkdistcat"] = np.searchsorted(distance_bins, perdata["pwaudist"], side="right")
    perdata["wrktimecat"] = np.searchsorted(time_bins, perdata["pwautime"], side="right")    
    perdata.loc[perdata["pwtaz"] < 0, ["wrkdistcat", "wrktimecat"]] = max_time_bin

    perdata["stud"] = np.where(perdata["pptyp"].isin([5, 6, 7]) & (perdata["pstaz"] != 0), 1, 0)
    perdata["outhmstud"] = np.where((perdata["pstaz"] > 0) & (perdata["hhparcel"] != perdata["pspcl"]), 1, 0)
    
    perdata["stutyp"] = perdata["pptyp"].map(STUDENT_TYPE_MAP)    
    perdata["schdistcat"] = np.searchsorted(distance_bins, perdata["psaudist"], side="right")
    perdata["schtimecat"] = np.searchsorted(time_bins, perdata["psautime"], side="right")
    
    perdata.loc[perdata["pstaz"] < 0, ["schdistcat", "schtimecat"]] = max_time_bin

    taz_to_county = dict(zip(countycorr["BKRCastTAZ"], countycorr["DistrictFlowID"]))
    perdata["hhcounty"] = perdata["hhtaz"].map(taz_to_county)
    perdata["pwcounty"] = perdata["pwtaz"].map(taz_to_county)
    perdata["pscounty"] = perdata["pstaz"].map(taz_to_county)

    perdata.loc[perdata["pwtaz"] < 0, "pwcounty"] = 8
    perdata.loc[perdata["pstaz"] < 0, "pscounty"] = 8
    
    perdata["wfh"] = np.where((perdata["wrkr"] == 1) & (perdata["hhparcel"] == perdata["pwpcl"]), 1, 0)
    perdata["sfh"] = np.where((perdata["stud"] == 1) & (perdata["hhparcel"] == perdata["pspcl"]), 1, 0)

    perdata["pwautime"] = perdata["pwautime"].mask(perdata["pwautime"] < 0)
    perdata["pwaudist"] = perdata["pwaudist"].mask(perdata["pwaudist"] < 0)
    perdata["psautime"] = perdata["psautime"].mask(perdata["psautime"] < 0)
    perdata["psaudist"] = perdata["psaudist"].mask(perdata["psaudist"] < 0)

    return perdata


def prep_vehavail(perdata: pd.DataFrame, hhdata: pd.DataFrame, countycorr: pd.DataFrame) -> pd.DataFrame:
    # Household vehicle category (cap at 4+)
    hhdata["hhvehcat"] = np.where(hhdata["hhvehs"] > 4, 4, hhdata["hhvehs"])

    # Person 16+ indicator
    perdata["hh16cat"] = np.where(perdata["pagey"] >= 16, 1, 0)

    # Aggregate number of 16+ persons by household
    aggper = perdata.groupby("hhno", as_index=False)["hh16cat"].sum()

    # Merge into household data
    hhdata = hhdata.merge(aggper, on="hhno", how="left")

    # Cap hh16cat at 4+
    hhdata.loc[hhdata["hh16cat"] > 4, "hh16cat"] = 4

    # Income categories: 1 = <=15k, 2 = 15–50k, 3 = 50–75k, 4 = >75k
    hhdata["inccat"] = 1 + np.searchsorted([15000, 50000, 75000], hhdata["hhincome"], side="right")

    # County lookup based on TAZ
    hhdata["hhcounty"] = hhdata["hhtaz"].map(dict(zip(countycorr["BKRCastTAZ"], countycorr["DistrictFlowID"])))

    return hhdata


def prep_perdata(perdata: pd.DataFrame, hhdata: pd.DataFrame, countycorr: pd.DataFrame) -> pd.DataFrame:
    # County lookup
    hhdata["hhcounty"] = hhdata["hhtaz"].map(dict(zip(countycorr["BKRCastTAZ"], countycorr["DistrictFlowID"])))

    # Income categories (similar to findInterval)
    hhdata["inccat"] = np.searchsorted([0, 15000, 50000, 75000], hhdata["hhincome"], side="right")

    # Persons age 16+
    perdata["hh16cat"] = np.where(perdata["pagey"] >= 16, 1, 0)

    # Aggregate # of 16+ per hh
    aggper = perdata.groupby("hhno", as_index=False)["hh16cat"].sum()
    hhdata = hhdata.merge(aggper, on="hhno", how="left")
    hhdata.loc[hhdata["hh16cat"] > 4, "hh16cat"] = 4

    # Vehicle sufficiency
    hhdata["vehsuf"] = np.nan
    hhdata.loc[hhdata["hhvehs"] == 0, "vehsuf"] = 1
    hhdata.loc[(hhdata["hhvehs"] > 0) & (hhdata["hhvehs"] < hhdata["hh16cat"]), "vehsuf"] = 2
    hhdata.loc[(hhdata["hhvehs"] > 0) & (hhdata["hhvehs"] == hhdata["hh16cat"]), "vehsuf"] = 3
    hhdata.loc[(hhdata["hhvehs"] > 0) & (hhdata["hhvehs"] > hhdata["hh16cat"]), "vehsuf"] = 4

    # Merge attributes back to perdata
    hhdata["vehcat"] = (hhdata["hhvehs"] > 0).astype(int)
    perdata = perdata.merge(hhdata[["hhno", "hhcounty", "inccat", "vehsuf", "hhtaz", "vehcat"]], on="hhno", how="left")

    return perdata


def prep_pdaydata(pdaydata: pd.DataFrame, perdata: pd.DataFrame, excludeChildren5=True) -> pd.DataFrame:
    if int(base_year) in [2023, 2024] and dataset == "survey":
        pdaydata['hhno_'] = pdaydata['hhno'].astype(str)
        pdaydata['hhno_'] = pdaydata['hhno_'].str[:-1].astype('int64')
    else:
        pdaydata['hhno_'] = pdaydata['hhno']
    
    pdaydata['key'] = pdaydata['hhno_'].astype(str) + "_" + pdaydata['pno'].astype(str)
    perdata['key'] = perdata['hhno'].astype(str) + "_" + perdata['pno'].astype(str)
    pdaydata = pdaydata.merge(perdata, on=["key"], how="left")

    if int(base_year) in [2023, 2024] and dataset == "survey":
        pdaydata['psexpfac'] = pdaydata['pdexpfac']

    if excludeChildren5:
        pdaydata = pdaydata[pdaydata["pptyp"] < 8].copy(deep=True)

    # Combine tour/stop types
    pdaydata["pbtours"] += pdaydata["metours"]
    pdaydata["sotours"] += pdaydata["retours"]
    pdaydata["pbstops"] += pdaydata["mestops"]
    pdaydata["sostops"] += pdaydata["restops"]

    # Total tours & stops
    pdaydata["tottours"] = (
        pdaydata["wktours"] + pdaydata["sctours"] + pdaydata["estours"] +
        pdaydata["pbtours"] + pdaydata["shtours"] + pdaydata["mltours"] +
        pdaydata["sotours"]
    ).clip(upper=3)

    pdaydata["totstops"] = (
        pdaydata["wkstops"] + pdaydata["scstops"] + pdaydata["esstops"] +
        pdaydata["pbstops"] + pdaydata["shstops"] + pdaydata["mlstops"] +
        pdaydata["sostops"]
    )

    # Tour-stop categorization (nested ifs in R)
    def get_tourstop(row):
        if row.tottours == 0 and row.totstops == 0: return 0
        if row.tottours == 1 and row.totstops == 0: return 1
        if row.tottours == 1 and row.totstops == 1: return 2
        if row.tottours == 1 and row.totstops == 2: return 3
        if row.tottours == 1 and row.totstops >= 3: return 4
        if row.tottours == 2 and row.totstops == 0: return 5
        if row.tottours == 2 and row.totstops == 1: return 6
        if row.tottours == 2 and row.totstops == 2: return 7
        if row.tottours == 2 and row.totstops >= 3: return 8
        if row.tottours == 3 and row.totstops == 0: return 9
        if row.tottours == 3 and row.totstops == 1: return 10
        if row.tottours == 3 and row.totstops == 2: return 11
        if row.tottours == 3 and row.totstops >= 3: return 12
        return np.nan

    pdaydata["tourstop"] = pdaydata.apply(get_tourstop, axis=1)

    # Purpose-specific tour/stop flags
    def binary_map(tours, stops):
        if tours == 0 and stops == 0: return 1
        if tours == 0 and stops >= 1: return 2
        if tours >= 1 and stops == 0: return 3
        if tours >= 1 and stops >= 1: return 4

    for prefix in ["wk", "sc", "es", "pb", "sh", "ml", "so"]:
        pdaydata[f"{prefix}tostp"] = pdaydata.apply(
            lambda r: binary_map(r[f"{prefix}tours"], r[f"{prefix}stops"]), axis=1
        )

    # Top-coded tour counts (0–3 range)
    for prefix in ["wk", "sc", "es", "pb", "sh", "ml", "so"]:
        pdaydata[f"{prefix}topt"] = np.searchsorted([0, 1, 2, 3], pdaydata[f"{prefix}tours"], side="right")

    return pdaydata


# -------------------------------
# Tour preprocessing
# -------------------------------
def prep_tourdata(tourdata: pd.DataFrame, 
                  perdata: pd.DataFrame, 
                  countycorr: pd.DataFrame, 
                  work_tours_only=False,
                  excludeChildren5=True,
                  max_distance_bin=90,  #(-inf,0], (0,1], (1,2], ... (88,89], (89,inf)
                  max_time_bin=90,  #(-inf,0], (0,1], (1,2], ... (88,89], (89,inf)
                  ) -> pd.DataFrame:
    tourdata = tourdata.merge(perdata, 
                              left_on=["hhno_", "pno"], right_on=["hhno", "pno"], 
                              how="left", suffixes=("", "_"))

    if excludeChildren5:
        tourdata = tourdata[tourdata["pptyp"] < 8].copy(deep=True)

    # Recode purposes
    tourdata.loc[tourdata["pdpurp"] == 8, "pdpurp"] = 7
    tourdata.loc[tourdata["pdpurp"] == 9, "pdpurp"] = 4

    # FTW indicator
    tourdata["ftwind"] = np.where(tourdata["pptyp"] == 1, 1, 2)

    # Stop categories
    tourdata["stcat"] = np.searchsorted([0, 1, 2, 3], tourdata["subtrs"], side="right")
    tourdata["stops"] = tourdata["tripsh1"] + tourdata["tripsh2"] - 2
    tourdata["stopscat"] = np.searchsorted([1, 2, 3, 4, 5, 6], tourdata["stops"], side="right")
    tourdata["h1stopscat"] = np.searchsorted([1, 2, 3, 4, 5, 6], tourdata["tripsh1"] - 1, side="right")
    tourdata["h2stopscat"] = np.searchsorted([1, 2, 3, 4, 5, 6], tourdata["tripsh2"] - 1, side="right")

    # Adjusted purpose
    tourdata["pdpurp2"] = np.where(tourdata["parent"] == 0, tourdata["pdpurp"], 8)

    tourdata["ocounty"] = tourdata["totaz"].map(dict(zip(countycorr["BKRCastTAZ"], countycorr["DistrictFlowID"])))
    tourdata["dcounty"] = tourdata["tdtaz"].map(dict(zip(countycorr["BKRCastTAZ"], countycorr["DistrictFlowID"])))

    tourdata["distcat"] = np.searchsorted(np.arange(0, max_distance_bin), tourdata["tautodist"], side="right")
    tourdata["timecat"] = np.searchsorted(np.arange(0, max_time_bin), tourdata["tautotime"], side="right")
    wrkrtyp_map = dict(zip(range(1, 9), [1, 2, 3, 3, 3, 3, 3, 3]))
    tourdata["wrkrtyp"] = tourdata["pptyp"].map(wrkrtyp_map)

    tourdata.loc[tourdata["tautotime"] < 0, "tautotime"] = np.nan
    tourdata.loc[tourdata["tautodist"] < 0, "tautodist"] = np.nan

    # extract departure times
    tourdata['deppdhr'] = (tourdata['tlvdest'] // 100).astype(int)
    tourdata['deppdmin'] = tourdata['tlvdest'] - tourdata['deppdhr'] * 100

    if (tourdata['deppdmin'] > 60).any():
        # R branch: minutes > 60 (use /60 directly)
        tourdata['deptime'] = tourdata['tlvdest'] / 60.0
        tourdata['arrtime'] = tourdata['tardest'] / 60.0
    else:
        # compute departure and arrival times in hours
        tourdata['deptime'] = tourdata['deppdhr'] + tourdata['deppdmin'] / 60.0
        tourdata['arrpdhr'] = (tourdata['tardest'] // 100).astype(int)
        tourdata['arrpdmin'] = tourdata['tardest'] - tourdata['arrpdhr'] * 100
        tourdata['arrtime'] = tourdata['arrpdhr'] + tourdata['arrpdmin'] / 60.0

    # duration at destination
    tourdata['durdest'] = tourdata['deptime'] - tourdata['arrtime']

    # categorize times
    cats_arrdep = [0] + list(np.arange(3, 28, 0.5))  # 0, 3, 3.5, ..., 27.5
    cats_dur = [0] + list(pd.Series([x/2 for x in range(1, 49)]))  # 0.5 to 24.0 by 0.5

    tourdata['arrtimecat'] = pd.cut(tourdata['arrtime'], bins=cats_arrdep, labels=False, include_lowest=True)
    tourdata['deptimecat'] = pd.cut(tourdata['deptime'], bins=cats_arrdep, labels=False, include_lowest=True)
    tourdata['durdestcat'] = pd.cut(tourdata['durdest'], bins=cats_dur, labels=False, include_lowest=True)

    if work_tours_only:
        # Work tours: pass parent's mode
        wrktours = tourdata[tourdata["pdpurp"] == 1][["hhno", "pno", "tour", "tourmode"]].copy(deep=True)
        wrktours.loc[wrktours["tourmode"] == 9, "tourmode"] = 3
        wrktours = wrktours.rename(columns={"tourmode": "parenttourmode", "tour": "parent"})

        wrkbasedtours = tourdata[tourdata["parent"] > 0].merge(wrktours, on=["hhno", "pno", "parent"], how="left")

        nonwrkbasedtours = tourdata[tourdata["parent"] == 0].copy(deep=True)
        nonwrkbasedtours["parenttourmode"] = 0

        wrkbasedtours = wrkbasedtours[nonwrkbasedtours.columns].copy(deep=True)
        wrkbasedtours = wrkbasedtours.loc[:, ~wrkbasedtours.columns.duplicated()]
        nonwrkbasedtours = nonwrkbasedtours.loc[:, ~nonwrkbasedtours.columns.duplicated()]
        tourdata = pd.concat([nonwrkbasedtours, wrkbasedtours], axis=0, ignore_index=True)

    return tourdata


def prep_modedata_NHTS(tourdata):
    tourdata["tourmode"] = 0
    mapping = {
        3: 1,  # Drive Alone
        4: 2,  # Shared Ride 2
        5: 3,  # Shared Ride 3+
        7: 4,  # Drive-Transit
        6: 5,  # Walk-Transit
        2: 6,  # Bike
        1: 7,  # Walk
        8: 8   # School Bus
    }
    tourdata["tourmode"] = tourdata["tmodetp"].map(mapping).fillna(tourdata["tourmode"])
    return tourdata


def prep_modedata_DaySim(tourdata: pd.DataFrame) -> pd.DataFrame:
    tourdata["tourmode"] = 0
    tourdata.loc[tourdata.tmodetp == 3, "tourmode"] = 1  # Drive Alone
    tourdata.loc[tourdata.tmodetp == 4, "tourmode"] = 2  # Shared Ride 2
    tourdata.loc[tourdata.tmodetp == 5, "tourmode"] = 3  # Shared Ride 3+
    tourdata.loc[(tourdata.tmodetp == 7) & (tourdata.tpathtp.isin([5, 6])), "tourmode"] = 4  # PNR
    tourdata.loc[(tourdata.tmodetp == 7) & (tourdata.tpathtp.isin([7, 8])), "tourmode"] = 5  # KNR
    tourdata.loc[tourdata.tmodetp == 6, "tourmode"] = 6  # Walk-Transit
    tourdata.loc[tourdata.tmodetp == 2, "tourmode"] = 7  # Bike
    tourdata.loc[tourdata.tmodetp == 1, "tourmode"] = 8  # Walk
    tourdata.loc[tourdata.tmodetp == 8, "tourmode"] = 9  # School Bus
    return tourdata


def prep_tripdata(tripdata: pd.DataFrame, 
                  perdata: pd.DataFrame, 
                  countycorr: pd.DataFrame, 
                  excludeChildren5=True,
                  max_distance_bin=90,  #(-inf,0], (0,1], (1,2], ... (88,89], (89,inf)
                  max_time_bin=90,  #(-inf,0], (0,1], (1,2], ... (88,89], (89,inf)
                  ) -> pd.DataFrame:
    
    tripdata = tripdata.merge(perdata, left_on=["hhno_", "pno"], right_on=["hhno", "pno"], 
                              how="left", suffixes=("", "_"))

    if excludeChildren5:
        tripdata = tripdata[tripdata["pptyp"] < 8].copy(deep=True)

    # Recode purposes
    tripdata.loc[tripdata["dpurp"] == 8, "dpurp"] = 7
    tripdata.loc[tripdata["dpurp"] == 9, "dpurp"] = 4
    tripdata.loc[tripdata["dpurp"] == 0, "dpurp"] = 8

    # County lookup
    tripdata["ocounty"] = tripdata["otaz"].map(dict(zip(countycorr["BKRCastTAZ"], countycorr["DistrictFlowID"])))
    tripdata["dcounty"] = tripdata["dtaz"].map(dict(zip(countycorr["BKRCastTAZ"], countycorr["DistrictFlowID"])))

    if tripdata["travdist"].sum(skipna=True) == 0:
        logging.error("Error!!! - Skims information missing.")
    
    distance_bins = np.arange(0, max_distance_bin)  # (-inf,0], (0,1], (1,2], ... (88,89], (89,inf)
    time_bins = np.arange(0, max_time_bin)  # (-inf,0], (0,1], (1,2], ... (88,89], (89,inf)
    tripdata["distcat"] = np.digitize(tripdata["travdist"], bins=distance_bins) 
    tripdata["timecat"] = np.digitize(tripdata["travtime"], bins=time_bins)

    # Worker type mapping
    tripdata["wrkrtyp"] = tripdata["pptyp"].map(WORKER_TYPE_MAP)

    # Clean negatives
    tripdata.loc[tripdata["travtime"] < 0, "travtime"] = np.nan
    tripdata.loc[tripdata["travdist"] < 0, "travdist"] = np.nan

    # Extract departure time components
    tripdata['dephr'] = np.trunc(tripdata['deptm'] / 100).astype(int)
    tripdata['depmin'] = tripdata['deptm'] - tripdata['dephr'] * 100

    if (tripdata['depmin'] > 60).any():
        tripdata['deptime'] = tripdata['deptm'] / 60
        tripdata['arrtime'] = tripdata['arrtm'] / 60
        tripdata['durdest'] = tripdata['endacttm'] - tripdata['arrtm']
    else:
        print('times are in HHMM format')
        tripdata['deptime'] = tripdata['dephr'] + tripdata['depmin'] / 60

        tripdata['arrhr'] = np.trunc(tripdata['arrtm'] / 100).astype(int)
        tripdata['arrmin'] = tripdata['arrtm'] - tripdata['arrhr'] * 100
        tripdata['arrtime'] = tripdata['arrhr'] + tripdata['arrmin'] / 60

        tripdata['durdest'] = (
            (np.trunc(tripdata['endacttm'] / 100) - np.trunc(tripdata['arrtm'] / 100)) * 60
            + (tripdata['endacttm'] - np.trunc(tripdata['endacttm'] / 100) * 100)
            - (tripdata['arrtm'] - np.trunc(tripdata['arrtm'] / 100) * 100)
        )

    # Adjust negatives (wrap-around overnight trips)
    tripdata.loc[tripdata['durdest'] < 0, 'durdest'] += 1440
    tripdata['durdest'] = tripdata['durdest'] / 60

    # Keep only rows with max tseg per (hhno, pno, tour, half)
    if 'half' in tripdata.columns:
        maxtrip = (
            tripdata.groupby(['hhno', 'pno', 'tour', 'half'])['tseg']
            .max()
            .reset_index()
            .rename(columns={'tseg': 'maxtripno'})
        )
        tripdata = tripdata.merge(maxtrip, on=['hhno', 'pno', 'tour', 'half'], how='left')

    # Binning
    cats_arrdep = [0] + list(np.arange(3, 27.5, 0.5))
    cats_dur = [0] + list(np.arange(0.5, 23.5, 0.5))

    tripdata['arrtimecat'] = np.searchsorted(cats_arrdep, tripdata['arrtime'], side='right')
    tripdata['deptimecat'] = np.searchsorted(cats_arrdep, tripdata['deptime'], side='right')
    tripdata['durdestcat'] = np.searchsorted(cats_dur, tripdata['durdest'], side='right')

    # Flags
    if 'half' in tripdata.columns:
        tripdata['arrflag'] = 0
        tripdata['depflag'] = 0
        tripdata['durflag'] = 0

        tripdata.loc[(tripdata['half'] == 1) & (tripdata['tseg'] != tripdata['maxtripno']), 'arrflag'] = 1
        tripdata.loc[(tripdata['half'] == 2) & (tripdata['tseg'] != 1), 'depflag'] = 1
        tripdata.loc[tripdata['tseg'] < tripdata['maxtripno'], 'durflag'] = 1

    return tripdata


def prep_trmode_DaySim(tripdata: pd.DataFrame) -> pd.DataFrame:
    tripdata['tripmode'] = 0
    tripdata.loc[tripdata['mode'] == 3, 'tripmode'] = 1   # Drive Alone
    tripdata.loc[tripdata['mode'] == 4, 'tripmode'] = 2   # Shared Ride 2
    tripdata.loc[tripdata['mode'] == 5, 'tripmode'] = 3   # Shared Ride 3+

    # Transit modes
    tripdata.loc[(tripdata['mode'] == 6) & (tripdata['pathtype'].isin([3, 5, 7])), 'tripmode'] = 4  # bus
    tripdata.loc[(tripdata['mode'] == 6) & (tripdata['pathtype'].isin([4, 6, 8])), 'tripmode'] = 5  # project/CR
    tripdata.loc[(tripdata['mode'] == 6) & (tripdata['pathtype'] > 9), 'tripmode'] = 6              # placeholder
    tripdata.loc[(tripdata['mode'] == 6) & (tripdata['pathtype'] > 9), 'tripmode'] = 7              # commuter rail
    tripdata.loc[(tripdata['mode'] == 6) & (tripdata['pathtype'] > 9), 'tripmode'] = 8              # ferry

    tripdata.loc[tripdata['mode'] == 8, 'tripmode'] = 9   # School Bus
    tripdata.loc[tripdata['mode'] == 2, 'tripmode'] = 10  # Bike
    tripdata.loc[tripdata['mode'] == 1, 'tripmode'] = 11  # Walk

    # Paid RideShare & AV
    tripdata.loc[(tripdata['mode'] == 9) & (tripdata['dorp'] == 11), 'tripmode'] = 12   # PRS 2
    tripdata.loc[(tripdata['mode'] == 9) & (tripdata['dorp'].isin([12, 13])), 'tripmode'] = 12  # PRS 3
    tripdata.loc[(tripdata['mode'] == 9) & (tripdata['dorp'] == 21), 'tripmode'] = 13   # AV drive alone
    tripdata.loc[(tripdata['mode'] == 9) & (tripdata['dorp'] == 22), 'tripmode'] = 13   # AV PRS 2
    tripdata.loc[(tripdata['mode'] == 9) & (tripdata['dorp'] == 23), 'tripmode'] = 13   # AV PRS 3

    return tripdata


def prep_trmode_NHTS(tripdata: pd.DataFrame) -> pd.DataFrame:
    tripdata['tripmode'] = 0
    tripdata.loc[tripdata['mode'] == 3, 'tripmode'] = 1   # Drive Alone
    tripdata.loc[tripdata['mode'] == 4, 'tripmode'] = 2   # Shared Ride 2
    tripdata.loc[tripdata['mode'] == 5, 'tripmode'] = 3   # Shared Ride 3+

    # Transit modes
    tripdata.loc[(tripdata['mode'] == 6) & (tripdata['pathtype'] == 3), 'tripmode'] = 4  # localbus
    tripdata.loc[(tripdata['mode'] == 6) & (tripdata['pathtype'] == 4), 'tripmode'] = 5  # lightrail
    tripdata.loc[(tripdata['mode'] == 6) & (tripdata['pathtype'] == 5), 'tripmode'] = 6  # premium bus
    tripdata.loc[(tripdata['mode'] == 6) & (tripdata['pathtype'] == 6), 'tripmode'] = 7  # commuter rail
    tripdata.loc[(tripdata['mode'] == 6) & (tripdata['pathtype'] == 7), 'tripmode'] = 8  # ferry

    tripdata.loc[tripdata['mode'] == 8, 'tripmode'] = 9   # School Bus
    tripdata.loc[tripdata['mode'] == 2, 'tripmode'] = 10  # Bike
    tripdata.loc[tripdata['mode'] == 1, 'tripmode'] = 11  # Walk

    # Paid RideShare & AV
    tripdata.loc[(tripdata['mode'] == 9) & (tripdata['dorp'] == 11), 'tripmode'] = 12
    tripdata.loc[(tripdata['mode'] == 9) & (tripdata['dorp'].isin([12, 13])), 'tripmode'] = 12
    tripdata.loc[(tripdata['mode'] == 9) & (tripdata['dorp'] == 21), 'tripmode'] = 13
    tripdata.loc[(tripdata['mode'] == 9) & (tripdata['dorp'] == 22), 'tripmode'] = 13
    tripdata.loc[(tripdata['mode'] == 9) & (tripdata['dorp'] == 23), 'tripmode'] = 13

    return tripdata


def merge_skims(tourdata, skimfiles):
    nm2 = tourdata.columns.tolist()

    # Define time periods
    tourdata["h1timp"] = np.searchsorted([360, 540, 930, 1110], tourdata["tardest"], side="right")
    tourdata.loc[tourdata["h1timp"] == 0, "h1timp"] = 4
    tourdata["h2timp"] = np.searchsorted([360, 540, 930, 1110], tourdata["tlvdest"], side="right")
    tourdata.loc[tourdata["h2timp"] == 0, "h2timp"] = 4

    for k, skimfile in enumerate(skimfiles, start=1):
        skims = pd.read_csv(skimfile, header=None, delim_whitespace=True)
        skims.columns = ["totaz", "tdtaz", "H1TIM", "H1DIS", "H1COST"]
        skims = skims[["totaz", "tdtaz", "H1TIM", "H1DIS"]]

        key = tourdata["totaz"].astype(str) + "-" + tourdata["tdtaz"].astype(str)
        skimkey = skims["totaz"].astype(str) + "-" + skims["tdtaz"].astype(str)

        if (tourdata["h1timp"] == k).any():
            tourdata.loc[tourdata["h1timp"] == k, "H1TIM"] = key.map(
                dict(zip(skimkey, skims["H1TIM"]))
            )
            tourdata.loc[tourdata["h1timp"] == k, "H1DIS"] = key.map(
                dict(zip(skimkey, skims["H1DIS"]))
            )

        skims.columns = ["totaz", "tdtaz", "H2TIM", "H2DIS"]
        skimkey = skims["totaz"].astype(str) + "-" + skims["tdtaz"].astype(str)

        if (tourdata["h2timp"] == k).any():
            tourdata.loc[tourdata["h2timp"] == k, "H2TIM"] = key.map(
                dict(zip(skimkey, skims["H2TIM"]))
            )
            tourdata.loc[tourdata["h2timp"] == k, "H2DIS"] = key.map(
                dict(zip(skimkey, skims["H2DIS"]))
            )

    tourdata["tautotime"] = tourdata["H1TIM"] + tourdata["H2TIM"]
    tourdata["tautodist"] = tourdata["H1DIS"] + tourdata["H2DIS"]

    return tourdata[nm2]