#!/usr/bin/env python

import sys
from btclib import get_raw_balance, key_file, get_bitcoin_price


with open (key_file, "r") as keyfile:
    lines = keyfile.readlines()

total = 0.0
btc = get_bitcoin_price()
fmt = '%-32s %-40s %10s %10s'

rpt = '\n'
rpt += fmt % ('Name', 'Address', 'BTC','USD')
rpt += '\n\n'

for line in lines:
    if (line.startswith('#') or len(line.strip()) == 0):
        continue
    f = line.replace('\n','').split(',')
    name = f[0]
    addr = f[1]

    bal = float(get_raw_balance(addr)) / 1e8
    total += bal
    bal_disp = '{:,.8f}'.format(bal)
    usd_disp = '{:,.2f}'.format(bal*btc)
    if (bal > 0):
        rpt += fmt % (name, addr, bal_disp, usd_disp)
        rpt += '\n'

rpt += '\n\n'
total_disp = '{:,.8f}'.format(total)
usd_total_disp = '{:,.2f}'.format(total*btc)
rpt += fmt % ('', 'Total', total_disp, usd_total_disp)
rpt += '\n\n'

sys.stdout.write(rpt)
