#!/usr/bin/env python


# Validate all the key pairs in the wallet


import argparse, logging
from bitcoin import privtopub, pubkey_to_address
from btclib import logger, config
from validate import validate_address


parser = argparse.ArgumentParser(description='Check for invalid key pairs in the wallet')
parser.add_argument('-v', '--verbose', help='show status of all key pairs', action='store_true', required=False)
args = vars(parser.parse_args())


if (args['verbose']):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


clean = True
for entry in config['wallet']:
    valid = True
    name = None
    address = None
    privkey = None

    # verify name and address are present
    if 'name' not in entry.keys():
        logger.error('a wallet entry is MISSING a name');
        valid = False
    else:
        name = entry['name']
    if 'address' not in entry.keys():
        logger.error('{} is MISSING an address'.format(name))
        valid = False
    else:
        address = entry['address']


    if valid:

        # private key is optional
        if 'privkey' in entry.keys():
            privkey = entry['privkey']

        # validate public address
        if not validate_address(address):
            logger.error('{} has an INVALID bitcoin address'.format(name))
            valid = False

        # validate private key
        else:

            # OK - not present
            if privkey is None:
                logger.debug('{} is MISSING a private key'.format(name))
            else:
                try:
                    # check if public key corresponds to private key
                    derived = pubkey_to_address(privtopub(privkey))
                    if derived != address:
                        logger.error('{} derived address and given address are MISMATCHED'.format(name))
                        valid = False

                    # success
                    else:
                        logger.debug('{} has VALID keypairs'.format(name))
                except:

                    # validate private key
                    logger.error('{} has an INVALID private key'.format(name))
                    valid = False

    if not valid:
        clean = False

if clean:
    logger.info('all key pairs are VALID')
