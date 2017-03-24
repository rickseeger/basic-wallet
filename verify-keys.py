#!/usr/bin/env python

# Validate all the key pairs in the wallet


#import logging, argparse, json
#from btclib import config, logger, get_unspent, get_bitcoin_price, lookup
#from btclib import pluralize, broadcast, bitcoin_fee
from bitcoin import privtopub, pubkey_to_address
from btclib import logger, get_wallet


#from validate import validate_address

entries = get_wallet()
for entry in entries:
    address = entry['address']
    privkey = entry['privkey']
    name = entry['name']
    
    row = '{:35s} {:35s} '.format(name, address)
    if privkey is None:
        row += 'MISSING' # color yellow
    else:
        valid = False
        try:
            derived_address = pubkey_to_address(privtopub(privkey))
            if derived_address == address:
                valid = True
        except:
            pass

        row += 'VALID' if valid else 'INVALID'
    print row
    
