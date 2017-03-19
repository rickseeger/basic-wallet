#!/usr/bin/env python


import argparse, logging
from btclib import logger, bitcoin_fee


parser = argparse.ArgumentParser(description='Fetch the latest fast confirmation bitcoin fee')
parser.add_argument('-v', '--verbose', help='show verbose output', action='store_true', required=False)
args = vars(parser.parse_args())


if (args['verbose']):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


logger.info('fastest fee: {} sat/byte'.format(bitcoin_fee()))
