#!/usr/bin/env python
# coding: utf-8

ta = [-2.3, -0.9, 3.3, 9.3, 14.1, 17.5, 19.5, 19.1, 14.4, 9.2, 4.3, -0.1]
# average temperature
t_a = sum(ta) / len(ta)
#    T      PC    LCV
# 20 - 35   14.6  22.2
# 10 - 25   7.8   12.7
#  0 - 15   5.7   9.3
# -10 - -5  4.0   6.5

EF_VOC = 5.7 # depending on the daily temperature [g/veh/day]

def e_voc(N, EF_VOC, params):
    # Calculate evaporative emissions VOC for PC with petrol engine
    Npc = N * params[0] / 100          # total number of passenger cars
    Npc_p = Npc * params[1] / 100      # number of petrol PC
    return Npc_p * EF_VOC

# E_VOC(100, EF_VOC, [30, 70])

