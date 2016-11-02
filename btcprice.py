#!/usr/bin/env python


import sys
from btclib import get_bitcoin_price


usd = None
if (len(sys.argv) > 1):
    usd = float(sys.argv[1])

p = get_bitcoin_price()

if usd is None:
    usd = p
    btc = 1.0
else:
    btc = usd / p
    
sys.stdout.write('${:,.2f} = {:.8f} BTC\n'.format(usd, btc))

