import pandas as pd
import numpy as np
import os, sys
import h5py
import getopt
from colorama import init, Fore
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import *
import data_wrangling
import input_configuration as input_config
import emme_configuration as emme_config

# 10/25/2021
# modified to be compatible with python 3

# 4/12/2024
# add rec bike assignment

def get_link_attribute(attr, network):
    ''' Return dataframe of link attribute and link ID'''
    link_dict = {}
    for i in network.links():
        link_dict[i.id] = i[attr]
    df = pd.DataFrame.from_dict({'link_id': list(link_dict.keys()), attr: list(link_dict.values())})
    print(df.head(4))
    return df

def bike_facility_weight(my_project, link_df):
    '''Compute perceived travel distance impacts from bike facilities
       In the geodatabase, bike facility of 2=bicycle track and 8=separated path
       These are redefined as "premium" facilities
       Striped bike lanes receive a 2nd tier designatinon of "standard"
       All other links remain unchanged'''

    network = my_project.current_scenario.get_network()

    # Load the extra attribute data for bike facility type 
    # and replace geodb typology with the 2-tier definition
    df = get_link_attribute('@bkfac', network)
    df = pd.merge(df, link_df, on = 'link_id', how = 'inner')
    #df = df.merge(link_df)
    df = df.replace(input_config.bike_facility_crosswalk)

    # Replace the facility ID with the estimated  marginal rate of substituion
    # value from Broach et al., 2012 (e.g., replace 'standard' with -0.108)
    df['facility_wt'] = df['@bkfac']
    df = df.replace(input_config.facility_dict)

    return df

def volume_weight(my_project, df):
    ''' For all links without bike lanes, apply a factor for the adjacent traffic (AADT).'''

    # Separate auto volume into bins
    df['volume_wt'] = pd.cut(df['@tveh'], bins = input_config.aadt_bins, labels = input_config.aadt_labels, right=False)
    df['volume_wt'] = df['volume_wt'].astype('int')
    df = df.replace(to_replace = input_config.aadt_dict)
    # remove volume weight value from premium facility.
    df.loc[df['@bkfac'] == 'premium', 'volume_wt'] = 0

    return df

def process_attributes(my_project):
    '''Import bike facilities and slope attributes for an Emme network'''
    network = my_project.current_scenario.get_network()

    for attr in ['@bkfac', '@upslp']:
        if attr not in my_project.current_scenario.attributes('LINK'):
            my_project.current_scenario.create_extra_attribute('LINK',attr)

    import_attributes = my_project.m.tool("inro.emme.data.network.import_attribute_values")
    filename = r'inputs/bikes/emme_attr.in'
    import_attributes(filename, 
                      scenario = my_project.current_scenario,
                      revert_on_error=False)

    copy_attribute = my_project.m.tool("inro.emme.data.network.copy_attribute")
    from_att = '@biketype'
    to_attr = '@bkfac'
    from_scen = my_project.current_scenario
    copy_attribute(from_scenario = from_scen, from_attribute_name = '@biketype', to_attribute_name = '@bkfac')
    print('@bkfac is updated')

def process_slope_weight(df, my_project):
    ''' Calcualte slope weights on an Emme network dataframe
        and merge with a bike attribute dataframe to get total perceived 
        biking distance from upslope, facilities, and traffic volume'''

    network = my_project.current_scenario.get_network()

    # load in the slope term from the Emme network
    upslope_df = get_link_attribute('@upslp', network)

    # Join slope df with the length df
    upslope_df = upslope_df.merge(df)

    # Separate the slope into bins with the penalties as indicator values
    upslope_df['slope_wt'] = pd.cut(upslope_df['@upslp'], bins = input_config.slope_bins, labels = input_config.slope_labels, right = False)
    upslope_df['slope_wt'] = upslope_df['slope_wt'].astype('float')
    upslope_df = upslope_df.replace(to_replace = input_config.slope_dict)

    return upslope_df

def write_generalized_time(df):
    ''' Export normalized link biking weights as Emme attribute file. '''

    # Rename total weight column for import as Emme attribute
    df['@bkwt'] = df['total_wt']

    # Reformat and save as a text file in Emme format
    df['inode'] = df['link_id'].str.split('-').str[0]
    df['jnode'] = df['link_id'].str.split('-').str[1]

    filename = r'inputs/bikes/bkwt.in'
    df[['inode','jnode', '@bkwt']].to_csv(filename, sep=' ', index=False)

    print("results written to inputs/bikes/bkwt.in")

def calc_bike_weight(my_project, link_df):
    ''' Calculate perceived travel time weight for bikes
        based on facility attributes, slope, and vehicle traffic.'''

    # Import link attributes for elevation gain and bike facilities
    process_attributes(my_project)

    # Calculate weight of bike facilities
    bike_fac_df = bike_facility_weight(my_project, link_df)

    # Calculate weight from daily traffic volumes
    vol_df = volume_weight(my_project, bike_fac_df)

    # Calculate weight from elevation gain (for all links)
    df = process_slope_weight(df=vol_df, my_project=my_project)

    # Calculate total weights
    # add inverse of premium bike coeffient to set baseline as a premium bike facility with no slope (removes all negative weights)
    # add 1 so this weight can be multiplied by original link travel time to produced "perceived travel time"
    df.loc[df['@bkfac'] == 'premium', 'total_wt'] = 1 - np.float(input_config.facility_dict['facility_wt']['premium']) + df['facility_wt']
    df.loc[df['@bkfac'] != 'premium', 'total_wt'] = 1 - np.float(input_config.facility_dict['facility_wt']['premium']) + df['facility_wt'] + df['slope_wt'] + df['volume_wt']
    #df['total_wt'] = 1 - np.float(facility_dict['facility_wt']['premium']) + df['facility_wt'] + df['slope_wt'] + df['volume_wt']

    # Write link data for analysis
    df.to_csv(r'outputs/bikes/bike_attr.csv')

    # export total link weight as an Emme attribute file ('@bkwt.in')
    write_generalized_time(df=df)

def bike_assignment(my_project, tod, increment_volume_flag):
    ''' Assign bike trips using links weights based on slope, traffic, and facility type, for a given TOD.'''

    my_project.change_active_database(tod)
    matrix_name_list = [matrix.name for matrix in my_project.bank.matrices()]
    # Create attributes for bike weights (inputs) and final bike link volumes (outputs)
    for attr in ['@bkwt', '@bvol']:
        if attr not in my_project.current_scenario.attributes('LINK'):
            my_project.current_scenario.create_extra_attribute('LINK',attr)   

    # Create matrices for bike assignment and skim results
    if 'bkpt' not in matrix_name_list:
        my_project.create_matrix('bkpt', 'bike percepted travel time', 'FULL')
    if 'bkat' not in matrix_name_list:
        my_project.create_matrix('bkat', 'bike actual travel time', 'FULL')

    # Load in bike weight link attributes
    import_attributes = my_project.m.tool("inro.emme.data.network.import_attribute_values")
    filename = r'inputs\bikes\bkwt.in'
    import_attributes(filename, 
                    scenario = my_project.current_scenario,
                    revert_on_error=False)

    # Invoke the Emme assignment tool
    extended_assign_transit = my_project.m.tool("inro.emme.transit_assignment.extended_transit_assignment")
    bike_spec = json.load(open(r'inputs\skim_params\bike_assignment.json'))
    extended_assign_transit(bike_spec, save_strategies = True, add_volumes = increment_volume_flag, class_name = emme_config.bike_mode_class_lookup['bike'])

    print('bike assignment complete, now skimming')

    skim_bike = my_project.m.tool("inro.emme.transit_assignment.extended.matrix_results")
    bike_skim_spec = json.load(open(r'inputs\skim_params\bike_skim_setup.json'))
    skim_bike(bike_skim_spec, class_name = emme_config.bike_mode_class_lookup['bike'])

    # Add bike volumes to bvol network attribute
    bike_network_vol = my_project.m.tool("inro.emme.transit_assignment.extended.network_results")

    # Skim for final bike assignment results
    bike_network_spec = json.load(open(r'inputs\skim_params\bike_network_setup.json'))
    bike_network_vol(bike_network_spec, class_name = emme_config.bike_mode_class_lookup['bike'])

    if input_config.include_rec_bike:
        print('Assign rec bike trips...')
        recbike_name = 'recbike'
        # load rec bike trip table into emme, if recbike trips is not in the matrix list.
        if recbike_name not in matrix_name_list:
            my_project.create_matrix('recbike', 'rec bike trip table', 'FULL') 
        recbike_trips = my_project.load_supplemental_trips('recb')
        my_project.matrix_to_emme(recbike_trips, 'recbike', 'rec bike trip table', 'FULL')                         

        # create @recbike overwrite if it exists
        my_project.create_extra_attribute('LINK', '@recbvol', 'rec bike volume', overwrite = True)
        
        recbike_spec = json.load(open(r'inputs\skim_params\rec_bike_assignment.json'))
        extended_assign_transit(recbike_spec, save_strategies = True, add_volumes = True, class_name = emme_config.bike_mode_class_lookup['recb'])

        # no need to calculate skims for recbike. Use skims for bike mode instead.
                
        recbike_network_spec = json.load(open(r'inputs\skim_params\rec_bike_network_setup.json'))
        bike_network_vol(recbike_network_spec, class_name = emme_config.bike_mode_class_lookup['recb'])
        
    # Export skims to h5
    for matrix in ["mfbkpt", "mfbkat"]:
        print('exporting skim: ' + str(matrix))
        export_skims(my_project, matrix_name=matrix, tod=tod)

    print("bike assignment complete")

def export_skims(my_project, matrix_name, tod):
    '''Write skim matrix to h5 container'''

    my_store = h5py.File(r'inputs/' + tod + '.h5', "r+")

    matrix_value = my_project.bank.matrix(matrix_name).get_numpy_data()

    # scale to store as integer
    matrix_value = matrix_value * input_config.bike_skim_mult
    matrix_value = matrix_value.astype('uint16')

    # Remove unreasonably high values, replace with max allowed by numpy
    max_value = np.iinfo('uint16').max
    matrix_value = np.where(matrix_value > max_value, max_value, matrix_value)

    if matrix_name in my_store['Skims'].keys():
        my_store["Skims"][matrix_name][:] = matrix_value
    else:
        try:
            my_store["Skims"].create_dataset(name=matrix_name, data=matrix_value, compression='gzip', dtype='uint16')
        except:
            'unable to export skim: ' + str(matrix_name)

    my_store.close()


def calc_total_vehicles(my_project):
     '''For a given time period, calculate link level volume, store as extra attribute on the link'''
    
     #medium trucks
     my_project.network_calculator("link_calculation", result = '@mveh', expression = '@metrk/1.5')
     
     #heavy trucks:
     my_project.network_calculator("link_calculation", result = '@hveh', expression = '@hvtrk/2.0')
     
     #busses:
     my_project.network_calculator("link_calculation", result = '@bveh', expression = '@trnv3/2.0')
     
     #calc total vehicles, store in @tveh 
     str_expression = '@svtl1 + @svtl2 + @svtl3 + @svnt1 +  @svnt2 + @svnt3 + @h2tl1 + @h2tl2 + @h2tl3 + @h2nt1 + @h2nt2 + @h2nt3 + @h3tl1\
                                + @h3tl2 + @h3tl3 + @h3nt1 + @h3nt2 + @h3nt3 + @lttrk + @mveh + @hveh + @bveh'
     my_project.network_calculator("link_calculation", result = '@tveh', expression = str_expression)


def get_aadt(my_project):
    '''Calculate link level daily total vehicles/volume, store in a DataFrame'''
    
    link_list = []

    for key, value in emme_config.sound_cast_net_dict.items():
        my_project.change_active_database(key)
        
        # Create extra attributes to store link volume data
        for name, desc in input_config.extra_attributes_dict.items():
            my_project.create_extra_attribute('LINK', name, desc, 'True')
        
        # Calculate total vehicles for each link
        my_project.calc_bus_pce()            
        my_project.calc_total_vehicles()
        
        # Loop through each link, store length and volume
        network = my_project.current_scenario.get_network()
        for link in network.links():
            link_list.append({'link_id' : link.id, '@tveh' : link['@tveh'], 'length' : link.length})
            
    df = pd.DataFrame(link_list, columns = link_list[0].keys())       
    
    grouped = df.groupby(['link_id'])
    
    df = grouped.agg({'@tveh':sum, 'length':min})
    
    df.reset_index(level=0, inplace=True)
    
    return df
    
        
   
def write_link_counts(my_project, tod):
    ''' Write bike link volumes to file for comparisons to counts
        We need to think about how to better export link volumes. If we want to generate a pre-selected of link list with bike volumes (and rec bike),
        we need to find a better way to generate the selected list that will be always consistent with current network.
        Probably code bike volumes in master network, then generate the list of links with bike counts.                     
    '''        
        

    my_project.change_active_database(tod)

    network = my_project.current_scenario.get_network()

    # Load bike count data from file
    bike_counts = pd.read_csv(input_config.bike_count_data)

    # Load edges file to join proper node IDs - don't need for BKR - nagendra.dhakar@rsginc.com
    #edges_df = pd.read_csv(edges_file)

    #df = bike_counts.merge(edges_df, on=['INode','JNode'])
    df = bike_counts # in place of the above line that is commented out - nagendra.dhakar@rsginc.com

    list_model_vols = []

    for row in df.index:
        i = df.iloc[row]['INode'] #modified NewINode to INode - nagendra.dhakar@rsginc.com
        j = df.loc[row]['JNode'] #modified NewJNode to JNode - nagendra.dhakar@rsginc.com
        link = network.link(i, j)
        x = {}
        x['EmmeINode'] = i
        x['EmmeJNode'] = j
        #x['gdbINode'] = df.iloc[row]['INode'] #commented out two lines - nagendra.dhakar@rsginc.com
        #x['gdbJNode'] = df.iloc[row]['JNode']
        if link != None:
            x['bvol' + tod] = link['@bvol']
            if input_config.include_rec_bike:            
                x['recbvol' + tod] = link['@recbvol']            
        else:
            x['bvol' + tod] = None
            if input_config.include_rec_bike:            
                x['recbvol' + tod] = None            
        list_model_vols.append(x)

    df_count =  pd.DataFrame(list_model_vols)

    if os.path.exists(input_config.bike_link_vol):
        '''append column to existing TOD results'''
        df = pd.read_csv(input_config.bike_link_vol)
        df['bvol'+tod] = df_count['bvol'+tod]
        df.to_csv(input_config.bike_link_vol,index=False) 
    else:
        df_count.to_csv(input_config.bike_link_vol,index=False) 

def help():
    init(autoreset = True)    
    print('Assign general bike trip tables (generated from the daysim model) and recreational bike trip tables (from supplemental module).')
    print('Calculate bike skims from general bike trips.  ')
    print('The bike assignment employs the extended transit assignment procedure, distinguishing between two classes: "bike" and "recbike".' )
    print('Users can opt to replace existing auxiliary transit volume with the new bike assignment. ') 
    print(f'{Fore.GREEN}If user wants to keep other transit strategy files in place, first run SkimsAndPaths.py with -t option (transit assignment and skims only).')
    print('then run bike_model.py without -n option.')    
    print('By default, the bike assignment is an increment of existing aux transit volume.')       
    print('')
    print('    python bike_model.py -h -n')   
    print('       where: ')             
    print('            -h: help')
    print('            -n: new volume to replace the existing aux transit volume')        
    
def main():

    increment_volume_flag = True
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hn') 
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-n':
            increment_volume_flag = False
        else:
            print('Invalid option: ' + opt)
            print('Use -h to display help.')
            exit(2)

    # Remove any existing results
    if os.path.exists(input_config.bike_link_vol):
        try:
            os.remove(input_config.bike_link_vol)
        except OSError:
            pass

    print('running bike model')
    filepath = f'projects/{emme_config.master_project}/{emme_config.master_project}.emp'
    print(filepath) #debug
    my_project = EmmeProject(filepath)

    # Extract AADT from daily bank
    link_df = get_aadt(my_project)

    # Calculate generalized biking travel time for each link
    calc_bike_weight(my_project, link_df)

    # Assign all AM trips (unable to assign trips without transit networks)
    for tod in input_config.bike_assignment_tod:
        print('assigning bike trips for: ' + str(tod))
        bike_assignment(my_project, tod, increment_volume_flag)

        # Write link volumes
        write_link_counts(my_project, tod)

    my_project.closeDesktop()
    
if __name__ == "__main__":
    main()
