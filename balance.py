#!/usr/bin/env python

# Fetches balance for a single address or entire wallet

import sys, argparse, logging
from btclib import config, logger, get_balance, get_bitcoin_price, get_wallet, lookup


def main():

    # parse arguments
    parser = argparse.ArgumentParser(description='Displays Bitcoin balances')
    parser.add_argument('-a', '--showall', help='show zero balances', action='store_true', required=False)
    parser.add_argument('-f', '--from', help='get balances from just these addresses', nargs='+', required=False)
    parser.add_argument('-v', '--verbose', help='show verbose output', action='store_true', required=False)
    args = vars(parser.parse_args())

    if (args['verbose']):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)


    # report column format
    fmt = '%-32s %-40s %12s %12s'
    rpt = '\n' + fmt % ('Name', 'Address', 'BTC','USD') + '\n\n'

    # fetch balances
    total = 0.0
    btc = get_bitcoin_price()
    single_address = None
    entries = []

    # all balances
    if args['from'] is None:
        single_address = False
        entries = get_wallet()

    # single balance
    else:
        single_address = True
        found = lookup(args['from'][0])
        if found is None:
            logger.error('No address found matching "{}"'.format(args['from'][0]))
            exit(1)
        else:
            entries = [ found ]


    # create report
    for item in entries:

        name = item['name']
        addr = item['address']

        # only get balances for addresses you own
        if (item['privkey'] is not None) or args['showall'] or single_address:
            satoshi = get_balance(addr)
            if satoshi is None:
                logger.critical('unable to fetch balances')
                exit(1)
            bal = float(satoshi) / 1e8
            total += bal
            bal_disp = '{:,.8f}'.format(bal)
            usd_disp = '{:,.2f}'.format(bal*btc)

            if (bal > 0) or args['showall'] or single_address:
                rpt += fmt % (name, addr, bal_disp, usd_disp) + '\n'

    # totals
    if not single_address:
        total_disp = '{:,.8f}'.format(total)
        usd_total_disp = '{:,.2f}'.format(total*btc)
        rpt += '\n' + fmt % ('', 'Total', total_disp, usd_total_disp) + '\n'

    rpt += '\n'
    sys.stdout.write(rpt)


if __name__ == "__main__":
    main()
