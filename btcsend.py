#!/usr/bin/env python


import argparse, json
from btclib import logger, get_unspent, get_bitcoin_price, pluralize, validate, broadcast
from btclib import key_file, max_fee_usd, default_fee_per_byte
from bitcoin import mktx, sign


# lookup source address by search string return (name, address, privkey) or None
def lookup(s):
    with open (key_file, 'r') as keyfile:
        lines = keyfile.readlines()
    for line in lines:
        if (line.startswith('#') or len(line.strip()) == 0):
            continue
        if s.lower() in line.lower():
            f = line.replace('\n','').split(',')
            return (f[0], f[1], f[2])
    return None
    

# verify miner fee argument
def valid_fee(arg):
    min_fee = 0
    max_fee = 100

    try:
        value = int(arg)
    except ValueError as err:
        raise argparse.ArgumentTypeError(str(err))
    
    if value < min_fee or value > max_fee:
        message = 'Miner fee must be between {} and {} Satoshis per byte'.format(min_fee, max_fee)
        raise argparse.ArgumentTypeError(message)
    return arg


# command line arguments
parser = argparse.ArgumentParser(description='Transfer bitcoin')
parser.add_argument('-f', '--from', help='One of more from addresses', nargs='+', required=True)
parser.add_argument('-t', '--to', help='Address to send to', nargs=1, required=True)
parser.add_argument('-m', '--fee', help='Miner fee as Satoshis per byte', nargs=1, type=valid_fee, required=False, default=[default_fee_per_byte])
parser.add_argument('-a', '--amount', help='Amount to transfer', nargs=1, type=float, required=False)
args = vars(parser.parse_args())


# validate destination address
dest = args['to'][0]
if not validate(dest):
    logger.critical('Destination address "{}" is not a valid Bitcoin address'.format(dest))
    exit(1)


# each source address
utxos = []
privkeys = {}
for source in args['from']:

    # lookup address
    entry = lookup(source)
    if (entry == None):
        logger.critical('No source address found with substring "{}"'.format(source))
        exit(1)
    name, address, privkey = entry
    privkeys[address] = privkey

    # gather UTXOs
    unspent = get_unspent(address)
    for tx in unspent:
        utxo = {}
        utxo['output'] = '{}:{}'.format(tx['id'], tx['vout'])
        utxo['address'] = address
        utxo['value'] = tx['amount']
        utxos.append(utxo)


# UTXO stats
naddr = len(args['from'])
addr_suffix = '' if naddr == 1 else 'es'
nutxos = len(utxos)
btc_price = get_bitcoin_price()
avail_satoshi = sum([tx['value'] for tx in utxos])
avail_usd = (avail_satoshi / 1e8) * btc_price
logger.info('Unspent: {} address{} {} UTXO{} {:,.0f} Satoshi ${:,.2f} USD'.format(naddr, addr_suffix, nutxos, pluralize(nutxos), avail_satoshi, avail_usd))


txins = []
txouts = []
fee_per_byte = int(args['fee'][0])
logger.debug('using fee of {} satoshis per byte'.format(fee_per_byte))


# sweep
if args['amount'] == None:
    logger.warning('Sweeping {:,.0f} satoshi from all UTXOs'.format(avail_satoshi))
    # estimated transaction length = 10 + (180 * num_inputs) + (34 * num_outputs)
    fee = (10 + (180 * nutxos) + 34) * fee_per_byte

    # inputs
    n = 0
    total = 0
    for utxo in utxos:
        total += utxo['value']
        logger.info('Input {} UTXO {} Value {:,.0f} Total {:,.0f}'.format(n, utxo['output'], utxo['value'], total))
        txins.append(utxo)
        n += 1

    # outputs
    send = avail_satoshi - fee
    txouts = [ {'value' : send, 'address' : dest } ]
    logger.info('OUTPUT 0 Address {} Value {:,.0f}'.format(dest, send))
    

# transfer specific amount
else:
    change_address = None
    xfer = int(float(args['amount'][0])*1e8)
    logger.info('transferring {:,.0f} Satoshi'.format(xfer))
    # estimated transaction length = 10 + (180 * num_inputs) + (34 * num_outputs)
    initial_fee = (10 + (34 * 2)) * fee_per_byte
    remaining = xfer + initial_fee
    total_fees = initial_fee

    # inputs
    n = 0
    total = 0
    for utxo in utxos:
        fee_inc = (180 * fee_per_byte)
        remaining += fee_inc
        total_fees += fee_inc
        remaining -= utxo['value']
        total += utxo['value']
        logger.info('Input {} UTXO {} Value {:,.0f} Total {:,.0f}'.format(n, utxo['output'], utxo['value'], total))
        txins.append(utxo)
        n += 1

        if remaining <= 0:
            change = -remaining
            change_address = utxo['address']
            break


    # insufficient funds
    if (remaining > 0):
        note = ''
        if (remaining <= total_fees):
            note = 'after adding miner fees '
        logger.critical('Insufficient funds {}{:,.0f} > {:,.0f}'.format(note, xfer + total_fees, avail_satoshi))
        exit(1)

        
    # outputs
    txouts = [ { 'address' : dest, 'value' : xfer } ]
    logger.info('OUTPUT 0 Address {} Value {:,.0f}'.format(dest, xfer))

    # trivial remainder: costs more in fees to use than what remains, give to miner for speed bonus
    if change < ((10 + 180 + (34 *2)) * default_fee_per_byte):
        change_usd = (change/1e8) * btc_price
        logger.warning('Miner bonus of +{:,.0f} Satoshi +${:,.2f} USD'.format(change, change_usd))

    # return change
    else:

        # change going to same place?
        if (change_address == dest):
            merged_value = xfer + change
            logger.warning('Change address same as destination, merging output values {:,.0f}'.format(merged_value))
            txouts = [ { 'address' : dest, 'value' : merged_value } ]

        # extra output
        else:
            txouts.append( { 'address' : change_address, 'value' : change } )
            logger.info('OUTPUT 1 Address {} Value {:,.0f}'.format(change_address, change))


# sanity checks
sum_ins = sum([x['value'] for x in txins])
logger.debug('SUM(inputs) = {:,.0f}'.format(sum_ins))

sum_outs = sum([x['value'] for x in txouts])
logger.debug('SUM(outputs) = {:,.0f}'.format(sum_outs))

fee_satoshi = (sum_ins - sum_outs)
fee_usd = btc_price * (fee_satoshi/1e8)
logger.info('Paying miner fee of {:,.0f} Satoshi ${:,.2f} USD'.format(fee_satoshi, fee_usd))

if (fee_usd < 0):
    logger.critical('Sanity check failed: sum of outputs {:,.0f} exceeds sum of inputs {:,.0f}'.format(sum_outs, sum_ins))
    exit(1)

elif (fee_usd < 0.01):
    logger.critical('Bad transaction: miner fee too small: ${:,.6f}'.format(fee_usd))
    exit(1)

if (fee_usd > max_fee_usd):
    logger.error('Sanity check failed: miner fee too large ${:,.2f} >= ${:,.2f}'.format(fee_usd, max_fee_usd))
    exit(1)

    
# sign tx inputs
tx = mktx(txins, txouts)
for i in range(len(txins)):
    logger.debug('Signing input {}'.format(i))
    tx = sign(tx, i, privkeys[txins[i]['address']])
logger.debug('Created transaction: {}'.format(tx))


# user confirmation
raw_input('[ Press Enter to confirm ]')


# submit tx
tid = broadcast(tx)
logger.info('Transaction {} submitted to the network'.format(tid))
