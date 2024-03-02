#!/usr/bin/env python
# coding: utf-8

# Ei,j = sum_k(N j,k * Mj,k * EFi,j,k) [g]
# EFi,j,k - fuel consumption-specific emission factor of pollutant i for vehicle
            # category j and fuel k [g/kg]
# FCj,m - fuel consumption of vehicle category j using fuel m [kg]

# CO2 emission factors for different road transport fossil fuels
# em_facs_fuel = {'Petrol': 3.169, 'Diesel': 3.169}        # accept em_facs_fuel = 3.169
# CO2 emission factors from combustion of lubricant oil             em_facs_lub = 0.398
# em_facs_lub = {'Euro 3': 0.464, 'Euro 4': 0.398, 'Euro 5': 0.398, 
#                'Euro 6 a/b/c': 0.398, 'Euro 6 d-temp': 0.398, 'Euro 6 d': 0.398}

em_facs_fuel, em_facs_lub = 3.169, 0.398
em_fs = [em_facs_fuel, em_facs_lub]
# fuel consumption
fuel_cons = {'PC': {'Petrol': 0.07, 'Diesel': 0.06}, 'LCV': {'Diesel': 0.08}} # [kg/km]
lub_cons = {'PC': {'Petrol': 0.000145, 'Diesel': 0.000149}, 'LCV': {'Diesel': 0.000149}} # [kg/km]
cons = [fuel_cons, lub_cons]

def calc_co2(N, M, cons, em_fs, params=[30, 70]):
    '''
        Calculate CO2 emissions from fuel, lubricant combustion and additives
        Inputs: N - total number of vehicles, M total milage, cons - [fuel_cons, lub_cons]
                em_fs - emission factors
        Output: Total CO2 emission [kg]
    '''
    Npc = N * params[0] / 100          # total number of passenger cars
    Npc_p = Npc * params[1] / 100      # number of petrol PC
    Npc_d = Npc - Npc_p                # number of diesel PC
    Nlcv = N * (1 - params[0] / 100)   # number of light commercial vehicles
    
    M_veh = M / N    # average milage per vehicle
    work = [Npc_p * M_veh, Npc_d * M_veh, Nlcv * M_veh]   # total km_veh
    # print(work)
    # emission = []
    em = 0
    for i in range(len(cons)):
        j = 0
        for cat in cons[i]:
            # em = 0  # for selecting veh categories
            for fuel in cons[i][cat]:
                em += work[j] * em_fs[i] * cons[i][cat][fuel]
                j += 1
            # emission.append(round(em, 3))
    return round(em, 3)
    
# calc_CO2(100, 100, cons, em_fs, [30, 70])

# SO2 emissions
# SO2 and heavy metals originate directly from the fuel and lubricant combustion
# m - fuel
# k_s,m - weight related sulphur content in fuel of type m [g/g fuel]
# FCm - fuel consumption of fuel m [g].

# E_SO2 = 2 * k_s,m * FCm  - [g]

# TEST
# 21 * 3.169 * 0.07 + 9 * 3.169 * 0.06 + 70 * 3.169 * 0.08 + \
# 21 * 0.398 * 0.000145 + 9 * 0.398 * 0.000149 + 70 * 0.398 * 0.000149