import array as _array
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import json
import numpy as np
import pandas as pd
import os,sys
import h5py
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import * 
import truck_configuration as truck_config
import emme_configuration as emme_config
import input_configuration as bkr_config

'''
10/20/2022
   Truck model is revised in Oct 2022 to incorporate truck model implementaion of Soundcast. Input files are also updated to satisfy BKRCast specifications.

'''          
def network_importer(my_project):
    for scenario in list(my_project.bank.scenarios()):
           my_project.bank.delete_scenario(scenario)
    
    #create scenario
    s1002 = my_project.bank.create_scenario(1002)
    my_project.change_scenario(s1002)
    my_project.delete_links()
    my_project.delete_nodes()
    my_project.process_modes('inputs/networks/modes.txt')
    my_project.process_base_network('inputs/networks/' + truck_config.truck_base_net_name)  

def json_to_dictionary(dict_name):
    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/trucks/',dict_name+'.txt').replace("\\","/")
    my_dictionary = json.load(open(input_filename))
    return(my_dictionary)

def write_truck_trips(EmmeProject):
    truck_od_matrices = ['medtrk', 'hvytrk','deltrk']
  
    # if h5 exists, delete it and re-write
    try:
        os.remove(truck_config.truck_trips_h5_filename)
    except OSError:
        pass

    my_store = h5py.File(truck_config.truck_trips_h5_filename, 'w')
    for tod in emme_config.tod_networks:
        my_store.create_group(tod)
        for name in truck_od_matrices:
            matrix_name = 'mf' + tod +'_'+ name + '_trips'      
            matrix_id = EmmeProject.bank.matrix(matrix_name).id
            matrix = EmmeProject.bank.matrix(matrix_id)
            matrix_value = np.matrix(matrix.raw_data)
            my_store[tod].create_dataset(matrix_name, data=matrix_value.astype('float32'),compression='gzip')
            matrix_value = None
                    
    my_store.close()

def create_matrices(my_project, truck_matrix_df):

    for matrix_type in ['scalar','origin','destination','full']:
        df = truck_matrix_df[truck_matrix_df['matrix_type'] == matrix_type]
        for index, row in df.iterrows():
            my_project.create_matrix(row['matrix_name'], row['description'],matrix_type.upper())

def load_data_to_emme(balanced_prod_att, my_project, zones):
    """ Populate Emme matrices with medium and heavy truck productions and attractions. """

    for truck_type in ['m','h','d']:    # Loop through medium (m) and heavy (h) trucks
        for datatype in ['pro', 'att']:
            col_values = np.zeros(len(zones))
            numpy_data = balanced_prod_att[truck_type + 'tk' + datatype].values
            col_values[:len(numpy_data)] = numpy_data
            mat_name = 'mo' + truck_type + 't' + datatype
            matrix_id = my_project.bank.matrix(str(mat_name)).id
            my_project.bank.matrix(matrix_id).set_numpy_data(col_values, my_project.current_scenario)

            # Transpose Attractions (Destination Matrices are populated)
            if datatype == 'att':
                my_project.matrix_calculator(result = 'md' + truck_type + 'tatt', 
                                             expression = 'mo' + truck_type + 'tatt' + "'")

    ###
    ### FIXME: add this back in later, confirm it's not already applied in generation
    ###
    ## Apply land use restriction for heavy trucks to zones w/ no industrial parcels
    #my_project.matrix_calculator(result = 'mohtpro', expression = 'mohtpro * motruck')

    # Need to refactor etc?
    ### FIX ME:

    # Add operating costs as scalar matrices
    # Calculate operating costs for model year
    op_cost_df = pd.read_csv(r"inputs/trucks/truck_inputs.csv")
    op_cost_df = op_cost_df.loc[op_cost_df['data_type'] == 'operating_costs']

    data_year = int(op_cost_df['year'][0])
    if data_year < int(bkr_config.model_year):
        growth_rate = (1 + (truck_config.operating_cost_rate * (int(bkr_config.model_year) - data_year)))
        op_cost_df['cents_per_mile'] = op_cost_df['value'] * growth_rate

    # Note: Using medium truck coefficients for delivery trucks
    for mat_name, truck_type  in {'msmedop':'medium', 'mshvyop':'heavy', 'msdelop':'medium'}.items():
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        print(truck_type)
        print(mat_name)
        op_cost = op_cost_df[op_cost_df['truck_type'] == truck_type]['cents_per_mile'].astype('float').values[0]
        print(op_cost)
        matrix_id = my_project.bank.matrix(str(mat_name)).id
        print(matrix_id)
        my_project.bank.matrix(matrix_id).set_numpy_data(op_cost, my_project.current_scenario)

def import_skims(my_project, input_skims, zones, zonesDim):
    
    # Open GC skims from H5 container, average am/pm, import to emme:
    np_gc_skims = {}
    np_bidir_gc_skims = {}
    for tod in truck_config.truck_generalized_cost_tod.keys():
        hdf_file = h5py.File('inputs/' + tod + '.h5', "r")
        for item in input_skims.values():
            #gc
            skim_name = item['gc_name']
            h5_skim = hdf_file['Skims'][skim_name]
            np_skim = np.matrix(h5_skim)
            np_gc_skims[skim_name + '_' + truck_config.truck_generalized_cost_tod[tod]] = np_skim
        
            #distance
            skim_name = item['dist_name']
            h5_skim = hdf_file['Skims'][skim_name]
            np_skim = np.matrix(h5_skim)
            np_gc_skims[skim_name + '_' + truck_config.truck_generalized_cost_tod[tod]] = np_skim

    #zones = my_project.current_scenario.zone_numbers
    #zonesDim = len(my_project.current_scenario.zone_numbers)

    for truck_type in input_skims.values():
        #gc:
        am_skim_name = truck_type['gc_name'] + '_am'
        pm_skim_name = truck_type['gc_name'] + '_pm'
        bidir_skim_name = truck_type['gc_bidir_name']
        bi_dir_skim = np_gc_skims[am_skim_name] + np_gc_skims[pm_skim_name]
        bi_dir_skim = np.asarray(bi_dir_skim)
        #have sum, now get average
        bi_dir_skim *= .5
        bi_dir_skim = bi_dir_skim[0:zonesDim, 0:zonesDim]
        np_bidir_gc_skims[bidir_skim_name] = bi_dir_skim
   
        #distance
        am_skim_name = truck_type['dist_name'] + '_am'
        pm_skim_name = truck_type['dist_name'] + '_pm'
        bidir_skim_name = truck_type['dist_bidir_name']
        #distance skims are multiplied by 100 when exported by SkimsAndPaths, so we devide by 100
        bi_dir_skim = (np_gc_skims[am_skim_name] + np_gc_skims[pm_skim_name])/100.0
        bi_dir_skim = np.asarray(bi_dir_skim)
        #have sum, now get average
        bi_dir_skim *= .5
        bi_dir_skim = bi_dir_skim[0:zonesDim, 0:zonesDim]
        np_bidir_gc_skims[bidir_skim_name] = bi_dir_skim

    #import bi-directional skims to emmebank
    for mat_name, matrix in np_bidir_gc_skims.items():
        matrix_id = my_project.bank.matrix(str(mat_name)).id
        emme_matrix = ematrix.MatrixData(indices=[zones,zones],type='f')
        emme_matrix.raw_data=[_array.array('f',row) for row in matrix]
        my_project.bank.matrix(matrix_id).set_data(emme_matrix,my_project.current_scenario)

def balance_attractions(my_project):

    #Balance Medium Truck Attractions to productions:
    my_project.matrix_calculator(result = 'msmtprof', expression = 'momtpro', aggregation_origins = '+')
    my_project.matrix_calculator(result = 'msmtattf', expression = 'mdmtatt', aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'msmtatfe', expression = 'mdmtatt', 
                                 constraint_by_zone_destinations = str(truck_config.LOW_STATION) + '-' + str(truck_config.HIGH_STATION),
                                 aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'mdmtatt', 
                                 expression = 'mdmtatt * ((msmtprof - msmtatfe)/(msmtattf-msmtatfe))')

    #Balance Heavy Truck Attractions to productions:
    my_project.matrix_calculator(result = 'mshtprof', expression = 'mohtpro', aggregation_origins = '+')
    my_project.matrix_calculator(result = 'mshtattf', expression = 'mdhtatt', aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'mshtatfe', expression = 'mdhtatt', 
                                 constraint_by_zone_destinations = str(truck_config.LOW_STATION) + '-' + str(truck_config.HIGH_STATION),
                                 aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'mdhtatt',
                                     expression = 'mdhtatt * ((mshtprof - mshtatfe)/(mshtattf-mshtatfe))')

    #Balance Delivery Attractions to productions:
    my_project.matrix_calculator(result = 'msdtprof', expression = 'modtpro', aggregation_origins = '+')
    my_project.matrix_calculator(result = 'msdtattf', expression = 'mddtatt', aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'msdtatfe', expression = 'mddtatt', 
                                 constraint_by_zone_destinations = str(truck_config.LOW_STATION) + '-' + str(truck_config.HIGH_STATION),
                                 aggregation_destinations = '+')
    my_project.matrix_calculator(result = 'mddtatt',
                                     expression = 'mddtatt * ((msdtprof - msdtatfe)/(msdtattf-msdtatfe))')

def float_to_string(val):
    """ Return string with fixed precision, removes scientific notation for small floats."""

    return ("{:.6f}".format(val))

def calculate_impedance(my_project):
    
    truck_inputs_df = pd.read_csv(r'inputs/trucks/truck_inputs.csv') 
    coeff_df = truck_inputs_df.loc[truck_inputs_df['data_type'] == 'distribution_coeff']

    med_coeff = float_to_string(coeff_df[coeff_df['truck_type'] == 'medium']['value'].values[0])
    hvy_coeff = float_to_string(coeff_df[coeff_df['truck_type'] == 'heavy']['value'].values[0])
    # Using medium truck coefficients for delivery trucks
    del_coeff = float_to_string(coeff_df[coeff_df['truck_type'] == 'medium']['value'].values[0])

    vot_df = truck_inputs_df.loc[truck_inputs_df['data_type'] == 'vot']
    med_vot = float_to_string(vot_df[vot_df['truck_type'] == 'medium']['value'].values[0])
    hvy_vot = float_to_string(vot_df[vot_df['truck_type'] == 'heavy']['value'].values[0])
    # Using medium truck coefficients for delivery trucks
    del_vot = float_to_string(vot_df[vot_df['truck_type'] == 'medium']['value'].values[0])

    # Load friction factor and value of time coefficients

    # set flag to 0 for external-external OD paris and all others equal to 1
    my_project.matrix_calculator(result = 'mfintflg', expression = '1')
    my_project.matrix_calculator(result = 'mfintflg', expression = '0', 
                                 constraint_by_zone_destinations = truck_config.EXTERNAL_DISTRICT, 
                                 constraint_by_zone_origins = truck_config.EXTERNAL_DISTRICT)

    # calculate medium truck impedances:
    my_project.matrix_calculator(result = 'mfmedimp', 
                                 expression = 'exp('+med_coeff+'*(mfbmedcs+(mfbmedds*msmedop*'+med_vot+')))*mfintflg', 
                                 constraint_by_zone_destinations = '1-' + str(truck_config.HIGH_STATION), 
                                 constraint_by_zone_origins = '1-' + str(truck_config.HIGH_STATION))

    # calculate heavy truck impedances:
    my_project.matrix_calculator(result = 'mfhvyimp', 
                                 expression = 'exp('+hvy_coeff+'*(mfbhvycs+(mfbhvyds*mshvyop*'+hvy_vot+')))*mfintflg', 
                                 constraint_by_zone_destinations = '1-' + str(truck_config.HIGH_STATION), 
                                 constraint_by_zone_origins = '1-' + str(truck_config.HIGH_STATION))

    # calculate delivery truck impedances:
    my_project.matrix_calculator(result = 'mfdelimp', 
                                 expression = 'exp('+del_coeff+'*(mfbdelcs+(mfbdelds*msdelop*'+del_vot+')))*mfintflg', 
                                 constraint_by_zone_destinations = '1-' + str(truck_config.HIGH_STATION), 
                                 constraint_by_zone_origins = '1-' + str(truck_config.HIGH_STATION))

def balance_matrices(my_project):

    # Balance Medium Trucks
    my_project.matrix_balancing(results_od_balanced_values = 'mfmeddis', 
                                od_values_to_balance = 'mfmedimp', 
                                origin_totals = 'momtpro', 
                                destination_totals = 'mdmtatt', 
                                constraint_by_zone_destinations = '1-' + str(truck_config.HIGH_STATION), 
                                constraint_by_zone_origins = '1-' + str(truck_config.HIGH_STATION))
    # Balance Heavy Trucks
    my_project.matrix_balancing(results_od_balanced_values = 'mfhvydis', 
                                od_values_to_balance = 'mfhvyimp', 
                                origin_totals = 'mohtpro', 
                                destination_totals = 'mdhtatt', 
                                constraint_by_zone_destinations = '1-' + str(truck_config.HIGH_STATION), 
                                constraint_by_zone_origins = '1-' + str(truck_config.HIGH_STATION))

    # Balance Delivery Trucks
    my_project.matrix_balancing(results_od_balanced_values = 'mfdeldis', 
                                od_values_to_balance = 'mfdelimp', 
                                origin_totals = 'modtpro', 
                                destination_totals = 'mddtatt', 
                                constraint_by_zone_destinations = '1-' + str(truck_config.HIGH_STATION), 
                                constraint_by_zone_origins = '1-' + str(truck_config.HIGH_STATION))

def calculate_daily_trips(my_project):
    #Calculate Daily OD trips:
    #The distribution matrices (e.g. 'mfmeddis') are in PA format. Need to convert to OD format by transposing
    my_project.matrix_calculator(result = 'mfmedod', expression = '0.5*mfmeddis + 0.5*mfmeddis'+ "'")
    my_project.matrix_calculator(result = 'mfhvyod', expression = '0.5*mfhvydis + 0.5*mfhvydis'+ "'")
    my_project.matrix_calculator(result = 'mfdelod', expression = '0.5*mfdeldis + 0.5*mfdeldis'+ "'")
    

    # convert annual external medium truck trips to daily and add to medium od
    my_project.matrix_calculator(result = 'mfmedod', 
                                 expression = 'mfmedod + (mfmedee + mfmedei + mfmedie)/264')

    #convert annual external heavy truck trips to daily and add to heavy od:
    my_project.matrix_calculator(result = 'mfhvyod', 
                                 expression = 'mfhvyod + (mfhvyee + mfhvyei + mfhvyie)/264')


    #convert annual external delivery truck trips to daily and add to heavy od:
    my_project.matrix_calculator(result = 'mfdelod', 
                                 expression = 'mfdelod + (mfdelee + mfdelei + mfdelie)/264')



    #apply vehicle-equivalency factors to medium and heavy trucks:
    my_project.matrix_calculator(result = 'mfmedod', expression = 'mfmedod * 1.5')
    my_project.matrix_calculator(result = 'mfhvyod', expression = 'mfhvyod * 2')
    my_project.matrix_calculator(result = 'mfdelod', expression = 'mfdelod * 1.5')

    #apply time of day factors:

    ### FIXME: calculate these on the fly or add to the db
    
    df_tod_factors = pd.read_csv(r'inputs/trucks/truck_time_of_day_factors_bkr.csv')

    for tod in df_tod_factors['time_period'].unique():
        for truck_type, matrix_name in {'medtrk': 'medod', 'hvytrk': 'hvyod', 'deltrk': 'delod'}.items():
            df = df_tod_factors[(df_tod_factors['time_period'] == tod) & (df_tod_factors['truck_type'] == truck_type)]
            my_project.matrix_calculator(result = 'mf' + tod + '_' + truck_type + '_trips', 
                                         expression = 'mf' + matrix_name + '*' + str(df['value'].values[0]))

def write_summary(my_project):
    # Write production and attraction totals
    truck_pa = {'prod': {}, 'attr': {}}

    for truck_type in ['mt','ht','dt']:
        truck_pa['prod'][truck_type] = my_project.bank.matrix('mo' + truck_type + 'pro').get_numpy_data().sum()
        truck_pa['attr'][truck_type] = my_project.bank.matrix('md' + truck_type + 'att').get_numpy_data().sum()

    truck_pa_df = pd.DataFrame.from_dict(truck_pa)
    truck_pa_df.index.name = 'truck_type'
    truck_pa_df.to_csv(r'outputs/trucks/trucks_summary.csv')

def main():

    my_project = EmmeProject(truck_config.truck_model_project)
    #zones = my_project.current_scenario.zone_numbers

    input_skims = json_to_dictionary('input_skims')
    truck_matrix_list = pd.read_csv(r'inputs/trucks/truck_matrices.csv')
    
    balanced_prod_att = pd.read_csv(r'outputs/supplemental/7_balance_trip_ends.csv')

    network_importer(my_project)
    zones = my_project.current_scenario.zone_numbers
    zonesDim = len(zones)

    # BKRCastTAZ field in 7_balance_trip_ends.csv is not consecutive numbers, while zone system in emme requires consecutive numbers.
    zones_df = pd.DataFrame(zones, columns = {'BKRCastTAZ'})
    balanced_prod_att = pd.merge(zones_df, balanced_prod_att, on = 'BKRCastTAZ', how = 'left')
    balanced_prod_att.fillna(0, inplace = True)

    #  
    #     # Load zone partitions (used to identify external zones)
    my_project.initialize_zone_partition('ga')
    my_project.process_zone_partition('inputs/trucks/' + truck_config.districts_file)
    
    my_project.delete_matrices("ALL")
    create_matrices(my_project, truck_matrix_list)
    load_data_to_emme(balanced_prod_att, my_project, zones)
    import_skims(my_project, input_skims, zones, zonesDim)
    balance_attractions(my_project)
    calculate_impedance(my_project)
    balance_matrices(my_project)
    calculate_daily_trips(my_project)
    write_truck_trips(my_project)
    write_summary(my_project)

    my_project.closeDesktop()

if __name__ == "__main__":
    main()






