
from math import gcd
from functools import reduce

def gcd_list(lst):
    return reduce(gcd, lst)

def get_simplest_lot_ratio(qty_list):
    lot_sizes = [abs(int(q)) for q in qty_list]
    factor = gcd_list(lot_sizes)
    if factor == 0:
        return lot_sizes
    return [q // factor for q in lot_sizes]

def calculate_per_ratio_diff(legs, prices):
    """
    legs: list of dicts with 'side' and 'lots' keys
    prices: list of LTPs (floats), same order as legs
    """
    qtys = [abs(int(leg['lots'])) for leg in legs]
    ratio = get_simplest_lot_ratio(qtys)
    diff = 0
    for idx, leg in enumerate(legs):
        sign = 1 if leg['side'].upper() == "BUY" else -1
        diff += sign * prices[idx] * ratio[idx]
    return diff, ratio
