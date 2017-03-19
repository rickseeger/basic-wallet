#!/usr/bin/env python


import json, logging
from btclib import logger, bitcoin_fee


logger.setLevel(logging.DEBUG)
logger.info('fastest fee: {} sat/byte'.format(bitcoin_fee()))
