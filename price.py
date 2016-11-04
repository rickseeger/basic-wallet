#!/usr/bin/env python

# Retrieve the latest Bitcoin price and optionally convert a US dollar
# amount to a BTC amount.

import sys, argparse, logging
from btclib import logger, get_bitcoin_price


def main():

    # parse arguments
    parser = argparse.ArgumentParser(description='Fetch latest Bitcoin price')
    parser.add_argument('-u', '--USD', help='convert a USD dollar amount to BTC', nargs=1, type=float, required=False)
    parser.add_argument('-v', '--verbose', help='show verbose output', action='store_true', required=False)
    args = vars(parser.parse_args())

    if (args['verbose']):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)


    price = get_bitcoin_price()
    if price is None:
        logger.critical('Could not obtain latest BTC price')
        exit(1)

    if args['USD'] is None:
        sys.stdout.write('${:,.2f} = 1 BTC\n'.format(price))

    else:
        usd = args['USD'][0]
        btc = usd / price
        sys.stdout.write('${:,.2f} = {:,.8f} BTC\n'.format(usd, btc))


if __name__ == "__main__":
    main()
