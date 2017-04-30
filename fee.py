#!/usr/bin/env python


import argparse, logging
from btclib import logger, bitcoin_fee


default_block_target = 2


# validate block target argument
def valid_target(arg):
    try:
        value = int(arg)
    except ValueError as err:
        raise argparse.ArgumentTypeError(str(err))

    if value < 1 or value > 24:
        message = 'Block target must be an integer in the range [1,24]'
        raise argparse.ArgumentTypeError(message)
    return arg


parser = argparse.ArgumentParser(description='Fetch the latest fast confirmation bitcoin fee')
parser.add_argument('-v', '--verbose', help='show verbose output', action='store_true', required=False)
parser.add_argument('-b', '--blocktarget', help='want confirmation in this many blocks', type=valid_target, required=False, default=default_block_target)
args = vars(parser.parse_args())


if (args['verbose']):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

blocks = args['blocktarget']
logger.debug('block target: {}'.format(blocks))
logger.info('fee for confirmation in {} blocks: {} sat/byte'.format(blocks, bitcoin_fee(blocks)))
