#!/usr/bin/env python

# spill excess bitcoin

import os, yaml, logging
from btclib import logger, get_balance, validate_address
from pprint import pprint
from validate import validate_address

logger.setLevel(logging.INFO)


# load spill config
config = None
config_file = os.path.expanduser('~/.spill.conf')
try:
    with open(config_file, 'r') as stream:
        config = yaml.load(stream)
except:
    logger.critical('unable to open config file: {}'.format(config_file))
    exit(1)


# fetch balances and index by address label
idx = {}
for rec in config['spill']:
    
    if 'label' not in rec.keys():
        logger.critical('config file entry is missing a label')
        exit(1)
        
    if 'address' not in rec.keys():
        logger.critical('{} has no public address configured'.format(rec['label']))
        exit(1)
        
    address = rec['address']
    balance = get_balance(address)
    if balance is None:
        logger.critical('couldn\'t obtain balance for {}'.format(address))
        exit(1)

    rec['balance'] = balance
    label = str(rec['label'])
    del rec['label']
    idx[label] = rec

    
# validate config
destinations = set()
for k in idx.keys():
    rec = idx[k]

    # spill config
    if 'spillto' in rec.keys():
        pct = 0.0
        spill = rec['spillto']
        for dest in spill:
            logger.debug('DEST {}'.format(dest))
            destinations.add(dest['label'])
            if ('percent' not in dest.keys()) and len(spill) == 1:
                dest['percent'] = 100.0
            pct += dest['percent']
        logger.debug('{} spill percentage total is {}'.format(k, pct))
        if (pct != 100.0):
            logger.critical('spill percentages for {} do not sum to 100.0'.format(k))
            exit(1)

    # limits
    if 'limit' in rec.keys():
        try:
            limit = int(rec['limit'])
        except:
            logger.critical('limit for {} is not an integer ({})'.format(k, rec['limit']))
            exit(1)
        if (limit < 0):
            logger.critical('{} has a negative limit specification ({})'.format(k, limit))
            exit(1)

# validate spill destinations
labels = idx.keys()
for dest in destinations:
    if dest not in labels:
        logger.critical('spill destination {} not found'.format(dest))
        exit(1)

# execute spills with breadth-first search
for k in idx.keys():
    spilling = False
    spill_amount = None
    balance = idx[k]['balance']
    limit = None

    logger.info('KEY {} BALANCE {} FIELDS {}'.format(k, balance, idx[k].keys()))
    
    if (balance > 0) and ('spillto' in idx[k].keys()):

        # no balance limit
        if (not 'limit' in idx[k].keys()):
            logger.info('didn\'t find limit in keys')
            spilling = True
            spill_amount = balance  # sweep

        # handle spillover
        else:
            logger.info('found limit in keys')
            limit = idx[k]['limit']
            logger.info('LIMIT {} > BALANCE {}?'.format(limit, balance));
            if (limit > balance):
                spilling = True
                spill_amount = limit - balance

        # stopped here: logical error: convert to USD or commit to BTC units
        if spilling: 
            logger.debug('OK I want to spill {} from {}'.format(spill_amount, k))


# build single tx


###
# check for cycles (during tx build)
# enforce min transfer amount
# flapping prevention: only transfer when off my $X where x is about $20
# if no limit set then spill does a sweep of everything
# encryption at rest for the privkeys
# python test suite

