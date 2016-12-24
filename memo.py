#!/usr/bin/env python

# Fetches balance for a single address or entire wallet

import sys, argparse, logging
from btclib import config, logger, get_balance, get_bitcoin_price, get_wallet, lookup
from btclib import load_memos, save_memos


def main():

    # parse arguments
    parser = argparse.ArgumentParser(description='Add a memo to a transaction')
    parser.add_argument('-t', '--txid', help='transaction id',  nargs=1, required=True)
    parser.add_argument('-m', '--memo', help='up to 64 chars of memo text', nargs=1, required=True)
    parser.add_argument('-v', '--verbose', help='show verbose output', action='store_true', required=False)
    args = vars(parser.parse_args())

    if (args['verbose']):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    txid = args['txid'][0]
    memo = args['memo'][0]
    m = load_memos()
    m[txid] = memo
    save_memos(m)
    

if __name__ == "__main__":
    main()
