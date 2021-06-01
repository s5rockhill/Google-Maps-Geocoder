#Author: Sarah Rockhill
#Questions: rockhills@michigan.gov
#Latest version: https://github.com/s5rockhill/Google-Maps-Geocoder

import sys
sys.path.append('C:\\Python27\\ArcGIS10.7\\Lib\\site-packages')
#Geocode addresses using Google Maps API
#Documentation at https://developers.google.com/maps/documentation/geocoding/

#import the modules you will need to run this script
import googlemaps
import requests
import pandas as pd
import logging
import os
import re

logger = logging.getLogger("root")
logger.setLevel(logging.DEBUG)
# create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

#-----------------    Configuration     -----------------

#Provide Google Maps API the Key for Your Request
g_api_key = raw_input("Type your Google API key: ") #set your api key
print

#Indicate the name and location of your input/output files
infile=raw_input("Indicate the path and name of your address file: ")
print

outfile_name = raw_input("The output file must be in csv format. Save output file as: ") #raw_input("The output file must be in csv format. Save output file as: ")
print

outfile= os.path.join(os.path.dirname(os.path.abspath(infile)), outfile_name) 
print

# Return Full Google Results? If True, full JSON results from Google are included in output
RETURN_FULL_RESULTS = False

#-----------------    Load Data     ------------------

#Read the data to a Pandas Dataframe
data = pd.read_csv(infile, keep_default_na=False)

#Indicate the name of the field in your dataset that contains addresses and verify address field is in input dataset
while True:
    try:
        address_field= raw_input("Type the name of the field which contains addresses:  ")
    except ValueError:
        print('Invalid input')
        continue
    if address_field not in data.columns:
        print("Address field not found")
        continue
    else:
        break

#Pass address data to a list for geocoding
address_list = data[address_field].tolist()

#Remove all non-utf-8 characters and Suite/#/apt/etc. from address_list
new_list = []
for line in address_list:
	line = line.decode('utf-8', 'ignore').encode('utf-8')
	line = re.sub("( Suite| Ste | #| Room| Unit| Apt).*?,", ",", line)
	new_list.append(line)


#-----------------    Define Function     ------------------
def get_google_results(address, api_key=None, return_full_response=False):
    # Set up your Geocoding url
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json?address={}".format(address)
    if api_key is not None:
        geocode_url = geocode_url + "&key={}".format(api_key)
    # Ping google for the reuslts:
    results = requests.get(geocode_url)
    # Results will be in JSON format - convert to dict using requests functionality
    results = results.json()
    
    # if there's no results or an error, return empty results.
    if len(results['results']) == 0:
        output = {
            "latitude": None,
            "longitude": None,
            "accuracy": None,
            "google_place_id": None,
            "type": None
        }
    else:    
        answer = results['results'][0]
        output = {
            "latitude": answer.get('geometry').get('location').get('lat'),
            "longitude": answer.get('geometry').get('location').get('lng'),
            "accuracy": answer.get('geometry').get('location_type'),
            "google_place_id": answer.get("place_id"),
            "type": ",".join(answer.get('types'))
        }
        
    # Append some other details:    
    output['number_of_results'] = len(results['results'])
    output['status'] = results.get('status')
    if return_full_response is True:
        output['response'] = results
    
    return output


#------------------ PROCESSING LOOP -----------------------------

results = []
for address in new_list:
    #While the address geocoding is not finished
    geocoded = False
    while geocoded is not True:
        try:
            geocode_result = get_google_results(address, g_api_key, return_full_response=RETURN_FULL_RESULTS)
        except Exception as e:
            logger.exception(e)
            logger.error("Error in {}".format(address))
            logger.error("Skipping")
            geocoded = True
        if geocode_result['status'] == 'OVER_QUERY_LIMIT':
            logger.info("You have reached your daily maximum queries")
            geocoded = False
        else:
            if geocode_result['status'] != 'OK':
                logger.warning("Error geocoding {}: {}".format(address, geocode_result['status']))
                results.append(geocode_result)           
                geocoded = True
            if geocode_result['status'] == 'OK':
                logger.debug("Geocoded: {}: {}".format(address, geocode_result['status']))
                results.append(geocode_result)           
                geocoded = True
            
    # Every 500 addresses, save progress to file(in case of a failure so you have something!)
    if len(results) % 50 == 0:
        pd.concat([data, pd.DataFrame(results)], axis=1).to_csv("{}_bak".format(outfile), index=False)

#Merge results back into original data frame and output to outfile location
pd.concat([data, pd.DataFrame(results)], axis=1).to_csv(outfile, index=False)


print
print
#Count number of records sucessfully geocoded
successes = [r for r in results if r['status'] == 'OK']
logger.info("Completed geocoding for {} of {} address".format(len(successes), len(address_list)))

