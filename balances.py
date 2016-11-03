#!/usr/bin/env python

# Fetches the balances for all wallet addresses

import sys, logging, argparse
from btclib import config, logger, get_raw_balance, get_bitcoin_price


# parse arguments
parser = argparse.ArgumentParser(description='Display Bitcoin balances')
parser.add_argument('-a', '--showall', help='Show zero balances', action='store_true', required=False)
parser.add_argument('-v', '--verbose', help='Show verbose output', action='store_true', required=False)
args = vars(parser.parse_args())

if (args['verbose']):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.WARNING)
    

# report formatting
fmt = '%-32s %-40s %12s %12s'
rpt = '\n' + fmt % ('Name', 'Address', 'BTC','USD') + '\n\n'


# fetch balances
total = 0.0
btc = get_bitcoin_price()

i = 0
for address in config['wallet']:
    i += 1

    try: 
        name = address['name']
        addr = address['address']
        pkey = address['privkey']

    except KeyError:
        logger.critical('Could not parse wallet address #{}, check config file'.format(i))
        exit(1)
    
    bal = float(get_raw_balance(addr)) / 1e8
    total += bal
    bal_disp = '{:,.8f}'.format(bal)
    usd_disp = '{:,.2f}'.format(bal*btc)

    if (bal > 0) or args['showall']:
        rpt += fmt % (name, addr, bal_disp, usd_disp) + '\n'


total_disp = '{:,.8f}'.format(total)
usd_total_disp = '{:,.2f}'.format(total*btc)
rpt += '\n\n' + fmt % ('', 'Total', total_disp, usd_total_disp) + '\n\n'

sys.stdout.write(rpt)
