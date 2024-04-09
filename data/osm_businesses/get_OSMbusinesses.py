import csv
from OSMPythonTools.nominatim import Nominatim
nominatim = Nominatim()
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
overpass = Overpass()

# filter by tag
selectors = [
    '"tourism"="hotel"',
    '"tourism"="museum"',
    '"tourism"="hostel"',
    '"tourism"="apartment"',
    '"tourism"="guest_house"',
    '"tourism"="arts_centre"',
    '"amenity"="restaurant"',
    '"amenity"="cafe"',
    '"amenity"="fast_food"',
    '"amenity"="bar"',
    '"amenity"="nightclub"',
    '"amenity"="theater"',
    '"amenity"="place_of_worship"',
    '"amenity"="bank"',
    '"amenity"="school"',
    '"amenity"="university"',
    '"amenity"="kindergarten"',
    '"amenity"="library"',
    '"amenity"="dentist"',
    '"amenity"="pharmacy"',
    '"amenity"="post_office"',
    'shop',
    'office'
]

# OSM components, for retrieving points use 'node'
elementType = [
    'node',
#     'way',
#     'relation'
]

# tags: keys correspond to tags in query retrieved from the OSM
#       cols are the names of the resulting table fields
keys = ['name', 'amenity', 'shop', 'tourism', 'office', 'addr:postcode', 'addr:city', 'addr:street', 'addr:housenumber']
cols = ['NAME', 'AMENITY', 'SHOP', 'TOURISM', 'OFFICE', 'POSTCODE', 'CITY', 'STREET', 'HOUSENUMBER', 'X','Y']


def get_OSM_data(area, el_type, selectors, geometry=True, timeout=1000):
    ''' Retrieves objects from the defined as a polygon area from the OSM
    input -> area: list with coordinates of polygon  nodes, 
            el_type: list of OSM components to check, 
            selectors: list of selectors to find, 
            geometry: include geometry to output,
            timeout: set timeout for serching procedure (180 by default)
    output -> list of objects of type OverpassResult
    '''
    results = []
    for s in selectors:
        query = overpassQueryBuilder(bbox=area, elementType=el_type, selector=s, includeGeometry=geometry)
        results.append(overpass.query(query, timeout))
    return results

def form_OSM_output(overpass_res):
    '''Formats proper for csv file otput
    input-> list of OverpassResult objects
    ouput-> list of lists with elements corresponding to the columns 'cols' of the output table 
    '''
    output = []
    for res in overpass_res:
        res_elements = res.elements()
        for el in res_elements:
            row = []
            for k in keys:
                if k in el.tags():
                    row.append(el.tags()[k])
                else:
                    row.append(None)
            # if lat & lon == None -> take 1st coords from geometry: [lon, lat]
            if not el.lat() and not el.lon():
                coords = el.geometry()['coordinates']
                for i in range(len(coords)):
                    row.append(coords[- i - 1])
            else:
                row.append(el.lat())
                row.append(el.lon())
            output.append(row)
    return output

# customer types: 'L_B' - Lodging business, 'F_D' - Food and dining, 'C_S' - Convenience store,
#                 'V_S' - Various shops 'S_O' - Offices and Services, 'O' - Others + vacant
L_B = ["hotel", "hostel", "apartment"] # Lodging business
F_D = ["restaurant", 'cafe', 'fast-food', 'bar', 'nightclub'] # Food and dining
C_S = ['supermarket', 'convenience', 'greengroser'] # Convenience store
O_S = ['bank', 'cobbler', 'hairdresser', 'watchmaker', 'tattoo', 'beauty', 'copyshop',
       'optician', 'trophy', 'post_office', 'travel_agency', 'estate_agent', 'kiosk',
       'diplomatic', 'government', 'newspaper', 'association','architect', 'religion',
       'lawyer', 'financial', 'insurance', 'employment_agency', 'accountant', 'company',
       'newsagent', 'laundry', 'dentist', 'photo'] # Offices and Services
O = ['museum', 'place_of_worship', 'school', 'university', 'kindergarten', 'library', 'auction_house', 
     'religion', 'art', 'educational_institution ', 'research', 'ticket','lottery', 'vacant'] # Others + vacant

def write_nodes(outfile, out):
    '''Writes data of potential customers to either CSV or TXT file
    input -> output file name (in .txt or .csv format)
    output -> data on customers is written to output file, 
              in case of txt file - returns dictionary {customer_group: number}
    '''
    with open(outfile, 'w', newline='') as file:
        if outfile.endswith('.csv'):
            writer = csv.writer(file, delimiter='\t')
            writer.writerow(cols)
            for row in out:
                writer.writerow(row)
        elif outfile.endswith('.txt'):
            customers = {'L_B': 0, 'F_D': 0, 'C_S': 0, 'O_S': 0, 'O': 0, 'V_S': 0}
            count = 0
            for row in out:
                res = []
                count += 1
                res.append(str(count))
                if row[0] == None:
                    res.append("No name")
                else:
                    res.append(row[0])
                for i in range(1, 5):
                    if row[i] == None:
                        continue
                    # Lodging business
                    if row[i] in L_B:
                        res.append('L_B')
                        customers['L_B'] += 1
                    # Food and dining
                    elif row[i] in F_D:
                        res.append('F_D')
                        customers['F_D'] += 1
                    # Convenience store
                    elif row[i] in C_S:
                        res.append('C_S')
                        customers['C_S'] += 1
                    # Offices and Services
                    elif row[i] in O_S:
                        res.append('O_S')
                        customers['O_S'] += 1
                    # Others + vacant
                    elif row[i] in O:
                        res.append('O')
                        customers['O'] += 1
                    # Various shops
                    else:
                        res.append('V_S')
                        customers['V_S'] += 1
                res.append(str(row[-2]))
                res.append(str(row[-1]))
                file.write('\t'.join(res) + '\n')
            return customers

def get_clients(boundaries, outfile):
    results = get_OSM_data(boundaries, elementType, selectors)
    out = form_OSM_output(results)
    groups = write_nodes(outfile, out)
    return groups

