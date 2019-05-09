#!/usr/bin/env python

# List transactions for one or more addresses

import argparse, logging
from btclib import logger, get_transactions, lookup, get_wallet


def main():

    # parse arguments
    parser = argparse.ArgumentParser(description='List transactions for one or more addresses')
    parser.add_argument('-f', '--from', help='fetch transactions from these addresses',  nargs='+', required=False)
    parser.add_argument('-v', '--verbose', help='show verbose output', action='store_true', required=False)
    args = vars(parser.parse_args())

    if (args['verbose']):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    addrs = None
    if args['from']:
        addrs = args['from']
    else:
        w = get_wallet()
        addrs = [x['address'] for x in w]
        logger.warning('fetching all transactions on all addresses')

    txs = []
    for name in addrs:
        txs.extend(get_transactions(lookup(name)['address']))

    if len(txs) == 0:
        logger.info('No transactions found')
        exit(0)

    width = max([len(x['memo']) for x in txs])
    for rec in txs:
        rec['memo'] += ' ' * (width - len(rec['memo']))

    report = []
    balance = 0.0
    for rec in sorted(txs, key=lambda k : k['date']):
        balance += rec['amount']
        id = rec['id'] if args['verbose'] else rec['id'][:16]
        line = '%s %s %4s %+13.8f %+13.8f' % (rec['date'], id, rec['memo'], rec['amount'], balance)
        report.append(line)

    n = len(report)
    for i in range(n):
        print '%3d' % i, report[i]


if __name__ == "__main__":
    main()
