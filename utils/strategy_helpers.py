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

def calculate_per_ratio_diff(legs, prices, lot_sizes):
    if len(legs) != len(prices) or len(legs) != len(lot_sizes):
        return 0.0 

    total_buy_value = 0.0
    total_sell_value = 0.0
    total_buy_quantity = 0

    for i, leg in enumerate(legs):
        price = prices[i]
        lot_size = lot_sizes[i]
        lots = int(leg.get('lots', 0))
        
        if price is None or price <= 0 or lot_size is None or lot_size <= 0 or lots <= 0:
            continue 

        total_quantity = abs(lots) * lot_size
        value = total_quantity * price

        if leg.get('side', '').upper() == "BUY":
            total_buy_value += value
            total_buy_quantity += total_quantity
        else: # SELL
            total_sell_value += value

    if total_buy_quantity > 0:
        net = (total_buy_value - total_sell_value) / total_buy_quantity
        return net
    
    return 0.0