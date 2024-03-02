#!/usr/bin/env python
# coding: utf-8

import numpy as np
import pandas as pd

# INPUTS
file = "1.A.3.b.i-iv_emission_factors_22.xlsx"
sheet = "HOT_EMISSIONS_PARAMETERS"

# Fields
veh_cat = ['Passenger Cars', 'Light Commercial Vehicles']
fuel = ['Petrol', 'Diesel']
segment = ['Medium', 'N1-I']
standard = ['Euro 3', 'Euro 4', 'Euro 5', 'Euro 6 a/b/c', 'Euro 6 d-temp', 'Euro 6 d']
technology = ['PFI', 'DPF']
coeffs = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zita', 'Hta', 'Reduction Factor [%]']
pollutants = ['CO', 'NOx', 'VOC']

parameters = [veh_cat, fuel, segment, standard, technology, coeffs, pollutants]

# Cold emissions inputs
# average speed, trip length
V, l_trip = 20, 12.4
# average temteratures for Krakow
ta = [-2.3, -0.9, 3.3, 9.3, 14.1, 17.5, 19.5, 19.1, 14.4, 9.2, 4.3, -0.1]
# average temperature
t_a = sum(ta) / len(ta)
# Cold mileage percentage
beta = 0.6474 - 0.02545 * l_trip - (0.00974 - 0.000385 * l_trip) * t_a


def read_coeffs(file, sheet):
    # Read data from the excel sheet with emission coefficients
    # Input:  file - xsls file with calc coefficients, sheet for hot emissions
    df = pd.read_excel(file, sheet)
    return df


# calculate emission factors for HOT exhaust emissions
def calc_hot_em_factor(df, params):
    '''
        Calculate emission factors for HOT exhaust emissions
        Input:  file - xsls file with calc coefficients, sheet for hot emissions
                params: [0] - vehicle category (passenger cars, LCV), [1] - fuel (petrol / diesel),
                        [2] - segment (medium / N1-I), [3] - Euro standard, technology ('PFI', 'DPF'),
                        [4] - technology [5] - coeficient names, [6] - pollutants (CO, NOx, VOC)
                        [7] - average speed
        Output: dictionary, with structure: {'pollutant': {'cat': {'fuel': [em_factor]}}}
    '''          
    # Emission factor for Tier 3 methodology
    # EF = (Alpha * V**2 + Beta * V + Gamma + Delta / V) / (Epsilon * V**2 + Zeta * V + Eta) * (1 - RF)
    # speed = 20
    def emission_factor(coeffs, speed=20):
        # Calculate emission factors using Tier 3 methodology
        return (coeffs[0] * speed**2 + coeffs[1] * speed + coeffs[2] + coeffs[3] / speed) /                (coeffs[4] * speed**2 + coeffs[5] * speed + coeffs[6]) * (1 - coeffs[7])

    em_factor = {}
    pols = {}
   
    for pol in params[6]:
        cats = {}
        for cat in params[0]:
            fuels = {}
            if cat == 'Passenger Cars':
                seg = 'Medium'     
            else:
                seg = 'N1-I'
            for f in params[1]:
                res = []
                if f == 'Diesel':
                    tech = 'DPF'
                else:
                    if cat == 'Light Commercial Vehicles':
                        continue
                    else:
                        tech = 'PFI'
                for st in params[3]:
                    cs = []                      
                    for coef in coeffs:
                        cs.append(df.loc[(df['Category'] == cat) & (df['Fuel'] == f)
                                                      & (df['Segment'] == seg) 
                                                      & (df['Euro Standard'] == st)
                                                      & (df['Technology'] == tech)
                                                      & (df['Pollutant'] == pol)][coef])

                    res.append(float(emission_factor(cs)))
                fuels[f] = res
            cats[cat] = fuels
        pols[pol] = cats
    em_factor = pols
    return em_factor


# Helper functions

def select_ABC_coeffs(fuel, cat, stand, temp, speed):
    # Read coefficients A, B, C to calculate e_hot / e_cold
    ABC_CO, ABC_NOx, ABC_VOC = {}, {}, {}
    if fuel == "Petrol":    
        # Euro 6...
        if stand == 'Euro 6 a/b/c' or stand == 'Euro 6 d-temp' or stand == 'Euro 6 d':
            if  5 < speed < 45 and temp < 0:
                ABC_CO = {'CO': [-0.235, -0.306, 19.882]}
                ABC_NOx = {'NOx': [0.097, -0.181, 5.651]}
                ABC_VOC = {'VOC': [0.317, -3.612, 38.115]}
            else:
                ABC_CO = {'CO': [-0.11, 0.0, 17.461]}
                ABC_NOx = {'NOx': [0.089, 0.0, 7.257]}
                ABC_VOC = {'VOC': [0.166, 0.0, 43.859]}
        # Euro 1 to 5
        else:    
            if  5 < speed < 25 and -20 < temp < 15:
                if cat == 'Passenger Cars':
                    ABC_CO = {'CO': [0.121, -0.146, 3.766]}
                    ABC_NOx = {'NOx': [0.0458, 0.00747, 0.764]}
                    ABC_VOC = {'VOC': [0.157, -0.207, 7.009]}
                else:
                    ABC_CO = {'CO': [0.0782, -0.105, 3.116]}
                    ABC_NOx = {'NOx': [0.0343, 0.00566, 0.827]}
                    ABC_VOC = {'VOC': [0.0814, -0.165, 6.464]}
            elif 26 < speed < 45 and -20 < temp < 15:
                if cat == 'Passenger Cars':
                    ABC_CO = {'CO': [0.299, -0.286, -0.58]}
                    ABC_NOx = {'NOx': [0.0484, 0.0228, 0.685]}
                    ABC_VOC = {'VOC': [0.282, -0.338, 4.098]}
                else:
                    ABC_CO = {'CO': [0.193, -0.194, 0.305]}
                    ABC_NOx = {'NOx': [0.0375, 0.0172, 0.728]}
                    ABC_VOC = {'VOC': [0.116, -0.229, 5.739]}
    # Diesel
    else:
        if temp < 0:
            if stand == 'Euro 6 a/b/c':
                ABC_CO = {'CO': [0.504, -4.197, 7.588]}
                ABC_NOx = {'NOx': [0.015, -0.236, 2.264]}
                ABC_VOC = {'VOC': [-0.545, -0.97, 22.28]}
            elif stand == 'Euro d-temp':
                ABC_CO = {'CO': [0.820, -9.184, 21.879]}
                ABC_NOx = {'NOx': [0.121, -1.948, 11.415]}
                ABC_VOC = {'VOC': [-0.545, -0.97, 22.28]}
            elif stand == 'Euro 6 d':
                ABC_CO = {'CO': [0.897, -10.045, 23.836]}
                ABC_NOx = {'NOx': [0.151, -2.435, 14.019]}
                ABC_VOC = {'VOC': [-0.545, -0.97, 22.28]}
        else:
            if stand == 'Euro 6 a/b/c':
                ABC_CO = {'CO': [0.091, 0.000, 11.477]}
                ABC_NOx = {'NOx': [0.005, 0.000, 2.327]}
                ABC_VOC = {'VOC': [-0.286, 0.0, 18.445]}
            elif stand == 'Euro d-temp':
                ABC_CO = {'CO': [0.147, 0.000, 25.089]}
                ABC_NOx = {'NOx': [0.038, 0.000, 11.929]}
                ABC_VOC = {'VOC': [-0.286, 0.0, 18.445]}
            elif stand == 'Euro 6 d':
                ABC_CO = {'CO': [0.161, 0.000, 27.347]}
                ABC_NOx = {'NOx': [0.048, 0.000, 14.661]}
                ABC_VOC = {'VOC': [-0.286, 0.0, 18.445]}
    return ABC_CO, ABC_NOx, ABC_VOC

def e_hot_e_cold(pols, fuel, cat, stand, t_a, V=20):
    '''Calculates the ratio e_cold/e_hot for vehicles
        e_cold/e_hot = A × V + B × ta + C
    Input: ambient temperature ta (for practical reasons the average monthly temperature can be used)
        params: [ABC_CO, ABC_NOx, ABC_VOC]: average speed, coeffs for Euro 3 to 6 vehicles
    Output: {'CO': e_h/e_c, 'NOx': e_h/e_c, 'VOC': e_h/e_c}      
    '''
    params = select_ABC_coeffs(fuel, cat, stand, t_a, V)
    res = {}
    e_ratio = 0
    if fuel == 'Petrol':
        for i in range(len(pols)):
            # print(params[i][pols[i]])
            e_ratio = params[i][pols[i]][0] * V + params[i][pols[i]][1] * t_a + params[i][pols[i]][2]
            if e_ratio < 1:
                e_ratio = 1
            res[pols[i]] = round(e_ratio, 3)
    else:
        res[pols[0]] = 1.9 - 0.03 * t_a
        res[pols[1]] = 1.3 - 0.013 * t_a
        res[pols[2]] = 3.1 - 0.09 * t_a
    return res


# hot_coeffs = read_coeffs(file, sheet)
# hot_em_factors = calc_hot_em_factor(hot_coeffs, parameters)

# INPUT
# Selected coefficients e_hot / e_cold
eh_ec_coeffs = {'CO': {'Passenger Cars': {'Petrol': [3.74, 3.74, 3.74, 15.261, 15.261, 15.261],
                                           'Diesel': [1.6315, 1.6315, 1.6315, 1.6315, 1.6315, 1.6315]},
                       'Light Commercial Vehicles': {'Diesel': [1.6315, 1.6315, 1.6315, 1.6315, 1.6315, 1.6315]}},
                'NOx': {'Passenger Cars': {'Petrol': [1.564, 1.564, 1.564, 9.037, 9.037, 9.037],
                                           'Diesel': [1.18365, 1.18365, 1.18365, 1.18365, 1.18365, 1.18365]},
                       'Light Commercial Vehicles': {'Diesel': [1.18365, 1.18365, 1.18365, 1.18365, 1.18365, 1.18365]}},
                'VOC': {'Passenger Cars': {'Petrol': [6.615, 6.615, 6.615, 47.179, 47.179, 47.179],
                                           'Diesel': [2.2945, 2.2945, 2.2945, 2.2945, 2.2945, 2.2945]},
                       'Light Commercial Vehicles': {'Diesel': [2.2945, 2.2945, 2.2945, 2.2945, 2.2945, 2.2945]}}}
       

def calc_exhaust_emissions(N, M, h_em_fs, params):
    '''
        Calculate total EXHAUST (HOT and COLD) emissions of pollutants CO, NOx, VOC
        Inputs: N - total number of vehicles entering study area
                M - total distance for all vehicles
                em_fs - emission factors,
                params - list with indicators for N:
                        [0] - Npc% - % of the passenger cars, [1] - % of petrol among Npc
                        [2] - %[Euro 3, Euro 4, Euro 5, Euro 6 a/b/c, Euro 6 d-temp, Euro 6 d]
                        [3] - beta - fraction of the distance travelled during the cold-start
                        [4] - coeffs ehot/ecold
        Output: {pol_i: [res_PCp, res_PCd, res_LCVd]}
    '''  
    res = {}
    # pollutors
    pols = list(h_em_fs.keys())
 
    Npc = N * params[0] / 100          # total number of passenger cars
    Npc_p = Npc * params[1] / 100      # number of petrol PC
    Npc_d = Npc - Npc_p                # number of diesel PC
    Nlcv = N * (1 - params[0] / 100)   # number of light commercial vehicles
    
    M_veh = M / N    # average milage per vehicle
    work = [Npc_p * M_veh, Npc_d * M_veh, Nlcv * M_veh]   # total km_veh
    
    # pollutants
    for pol in pols:    
        # category
        res_pol = []
        j = 0
        for cat in h_em_fs[pol]:
            # fuel
            for fuel in h_em_fs[pol][cat]:
                emission = 0
                for e in range(len(h_em_fs[pol][cat][fuel])):
                    # e_hot + e_cold
                    emission +=  work[j] * h_em_fs[pol][cat][fuel][e] * params[2][e] / 100 +         params[3] * work[j] * h_em_fs[pol][cat][fuel][e] * params[4][pol][cat][fuel][e] * params[2][e] / 100
                res_pol.append(round(emission, 3))
                j += 1
            res[pol] = res_pol    
    return res

# calc_exhaust_emissions(100, 300, hot_em_factors, [30, 70, [50, 30, 9, 6, 4, 1], beta, eh_ec_coeffs])
