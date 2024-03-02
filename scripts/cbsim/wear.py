# coding: utf-8

# INPUTS
pollutants = ['TSP', 'PM10', 'PM2_5', 'PM1', 'PM0_1']
categories = ['PC', 'LCV']
E_types = ['tyre', 'breaks', 'road']

# TSP_tyre
EF_TSP_t = [0.0107, 0.0169]
mass_fraction_t = [1.000, 0.600, 0.420, 0.060, 0.048]

# TSP_breaks
EF_TSP_b = [0.0122, 0.0122]
mass_fraction_b = [1.000, 0.980, 0.390, 0.100, 0.080]

# TSP_road
EF_TSP_r = [0.015, 0.015]
mass_fraction_r = [1.00, 0.50, 0.27, 0, 0]

# speed depending coeffs 
St, Sb, Sr = 1.39, 1.67, 1

EF_TSP = [[0.0107, 0.0169], [0.0122, 0.0122], [0.015, 0.015]]
MF = [[1.000, 0.600, 0.420, 0.060, 0.048], [1.00, 0.980, 0.390, 0.100, 0.080], [1.00, 0.50, 0.27, 0, 0]]
Sts = [1.39, 1.67, 1]


def calc_wear(N, M, EF, m_fs, pols, cats, params):
    # calculate tyre, breaks or road surface wear 
    # cats - veh_categories
    # params = [% PC, St]
    res = {}
    Npc = N * params[0] / 100
    Nlcv = N * (1 - params[0] / 100)
    M_veh = M / N
    work = [Npc * M_veh, Nlcv * M_veh]
    TE = 0
    for j in range(len(EF)):
        p = {}
        for i in range(len(m_fs)):
            TE = work[j] * EF[j] * m_fs[i] * params[1]
            p[pols[i]] = round(TE, 3)
        res[cats[j]] = p       
    return res

# E_tyre = calc_wear(100, 100, EF_TSP_t, mass_fraction_t, pollutants, categories, [30, St])
# E_breaks = calc_wear(100, 100, EF_TSP_b, mass_fraction_b, pollutants, categories, [30, Sb])
# E_road = calc_wear(100, 100, EF_TSP_r, mass_fraction_r, pollutants, categories, [30, Sr])
# print('E_tyre', E_tyre, '\nE_breaks', E_breaks, '\nE_road', E_road)

# Es = [E_tyre, E_breaks, E_road]

def calc_wear_total(Es, cats, pols):
    TE = {p: 0 for p in pols}
    for e in Es:
        for cat in cats:
            # print(cat, e[cat])
            for p in pols:
                TE[p] += e[cat][p]
    return TE

# calc_wear_total(Es, categories, pollutants)

# em = []
# for i in range(len(E_types)):
#     em.append(calc_wear(100, 100, EF_TSP[i], MF[i], pollutants, categories, [30, Sts[i]]))

# calc_wear_total(em, categories, pollutants)
