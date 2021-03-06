#!/usr/bin/env python

# Construct a Bitcoin transaction and submit it to the network.

import logging, argparse, json
from btclib import config, logger, get_unspent, get_bitcoin_price, lookup
from btclib import pluralize, broadcast, bitcoin_fee
from bitcoin import mktx, sign
from validate import validate_address


# validate miner fee argument
def valid_fee(arg):
    try:
        value = int(arg)
    except ValueError as err:
        raise argparse.ArgumentTypeError(str(err))

    if value < 0:
        message = 'Miner fee must be a positive integer (Satoshis per byte)'
        raise argparse.ArgumentTypeError(message)
    return arg


def main():

    # get current fast confirmation bitcoin fee
    best_fee = bitcoin_fee()

    # command line arguments
    parser = argparse.ArgumentParser(description='Create a Bitcoin transaction')
    parser.add_argument('-f', '--from', help='one of more from addresses', nargs='+', required=True)
    parser.add_argument('-t', '--to', help='address to send to', nargs=1, required=True)
    parser.add_argument('-m', '--fee', help='miner fee in Satoshis per byte', nargs=1, type=valid_fee, required=False, default=[best_fee])
    parser.add_argument('-b', '--bitcoin', help='amount to transfer in BTC', nargs=1, type=float, required=False)
    parser.add_argument('-u', '--usd', help='amount to transfer in USD', nargs=1, type=float, required=False)
    parser.add_argument('-o', '--override', help='override high fee sanity check', action='store_true', required=False)
    parser.add_argument('-e', '--envfriendly', help='spend small UXTO amounts first; results in higher fees, but reduces global UTXO DB size', action='store_true', required=False)
    parser.add_argument('-v', '--verbose', help='show verbose output', action='store_true', required=False)
    args = vars(parser.parse_args())

    if (args['verbose']):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


    # check which currency
    sweep = False
    btc_specified = (args['bitcoin'] is not None)
    usd_specified = (args['usd'] is not None)
    amount_satoshi = None

    if not (btc_specified or usd_specified):
        sweep = True
        logger.debug('SWEEP all funds')
    elif (btc_specified and usd_specified):
        logger.error('Specify the amount in Bitcoin or USD, but not both')
        exit(1)
    elif btc_specified:
        amount_btc = args['bitcoin'][0]
        amount_satoshi = int(round(amount_btc * 1e8))
        logger.info('AMOUNT {:,.8f} BTC = {:,.0f} Satoshi'.format(amount_btc, amount_satoshi))
    elif usd_specified:
        amount_usd = args['usd'][0]
        btc_price = get_bitcoin_price()
        amount_btc = amount_usd / btc_price
        amount_satoshi = int(round(amount_btc * 1e8))
        logger.info('AMOUNT {:,.2f} USD = {:,.8f} BTC = {:,.0f} Satoshi'.format(amount_usd, amount_btc, amount_satoshi))


    # substring search for destination address in wallet
    dest = None
    item = lookup(args['to'][0])
    if item is not None:
        dest = item['address']
        logger.debug('Found destination address {} {} in wallet'.format(item['name'], dest))
    else:
        dest = args['to'][0]
        logger.debug('Using destination address {}'.format(dest))

    if not validate_address(dest):
        logger.warning('Destination address "{}" is not a valid Bitcoin address'.format(dest))


    # gather UTXOs from inputs
    utxos = []
    privkeys = {}
    from_addrs = []
    for source in args['from']:

        entry = lookup(source)
        if (entry == None):
            logger.error('No source address found in wallet matching "{}"'.format(source))
            exit(1)

        name = entry['name']
        address = entry['address']
        privkey = entry['privkey']
        logger.debug('Found source address {} {} in wallet'.format(name, address))
        from_addrs.append(address)
        privkeys[address] = privkey

        # gather UTXOs
        unspent = get_unspent(address)
        logger.debug('Address {} has {} unspent{}'.format(address, len(unspent), pluralize(len(unspent))))
        has_utxos = False
        for tx in unspent:
            utxo = {}
            utxo['output'] = '{}:{}'.format(tx['id'], tx['vout'])
            utxo['address'] = address
            utxo['value'] = tx['amount']
            logger.debug('utxo["value"] = {}'.format(utxo['value']))
            utxos.append(utxo)
            has_utxos = True

        if not has_utxos:
            logger.warning('Address {} has no confirmed UTXOs'.format(address))

    # must have at least one UTXO
    nutxos = len(utxos)
    if nutxos == 0:
        logger.error('No confirmed UTXOs found')
        exit(1)

    # report UTXO summary
    naddr = len(args['from'])
    btc_price = get_bitcoin_price()
    avail_satoshi = sum([tx['value'] for tx in utxos])
    avail_usd = (avail_satoshi / 1e8) * btc_price
    addr_suffix = '' if naddr == 1 else 'es'
    logger.debug('UTXO Summary: {} address{} {} UTXO{} {:,.0f} Satoshi ${:,.2f} USD'.format(naddr, addr_suffix, nutxos, pluralize(nutxos), avail_satoshi, avail_usd))

    # build tx
    txins = []
    txouts = []
    fee_per_byte = int(args['fee'][0])
    logger.debug('Using fee of {} satoshis per byte'.format(fee_per_byte))

    # sweep all BTC
    if sweep:
        logger.warning('Sweeping entire {:,.0f} satoshi from all UTXOs'.format(avail_satoshi))
        est_length = config['len-base'] + (config['len-per-input'] * nutxos) + config['len-per-output']
        fee = est_length * fee_per_byte

        # inputs
        n = 0
        total = 0
        for utxo in utxos:
            total += utxo['value']
            logger.debug('Input {} UTXO {} Value {:,.0f} Total {:,.0f}'.format(n, utxo['output'], utxo['value'], total))
            txins.append(utxo)
            n += 1

        # output
        send_satoshi = avail_satoshi - fee
        txouts = [ {'value' : send_satoshi, 'address' : dest } ]
        logger.debug('OUTPUT 0 Address {} Value {:,.0f}'.format(dest, send_satoshi))


    # transfer specific amount
    else:
        change_address = None
        send_satoshi = amount_satoshi
        logger.debug('transferring {:,.0f} Satoshi'.format(send_satoshi))

        initial_fee = (config['len-base'] + (config['len-per-output'] * 2)) * fee_per_byte
        remaining = send_satoshi + initial_fee
        total_fees = initial_fee

        # Environmentally-friendly transfer spends smallest UTXOs
        # first. This reduces the size of UTXO database each full-node
        # must store, but results in a higher fee.
        reverse = True
        if args['envfriendly']:
            logger.warning('environmentally friendly mode active, higher fees apply')
            reverse = False
        ordered_utxos = sorted(utxos, key=lambda k: k['value'], reverse=reverse)

        # inputs
        n = 0
        total = 0
        change = 0
        for utxo in ordered_utxos:
            fee_inc = (config['len-per-input'] * fee_per_byte)
            remaining += fee_inc
            total_fees += fee_inc
            remaining -= utxo['value']
            total += utxo['value']
            logger.debug('Input {} UTXO {} Value {:,.0f} Total {:,.0f}'.format(n, utxo['output'], utxo['value'], total))
            txins.append(utxo)
            n += 1

            if remaining < 0:
                change = -remaining
                change_address = utxo['address']
                break

        # insufficient funds
        if (remaining > 0):
            note = ''
            if (remaining <= total_fees):
                note = 'after adding miner fees '
		logger.critical('Insufficient funds {}{:,.0f} > {:,.0f}'.format(note, send_satoshi + total_fees, avail_satoshi))
		exit(1)

        # outputs
        txouts = [ { 'address' : dest, 'value' : send_satoshi } ]
        logger.debug('OUTPUT 0 Address {} Value {:,.0f}'.format(dest, send_satoshi))


        if (change > 0):

            # trivial remainder condition: it costs more in fees to
            # use the UTXO than what actually remains there, so just
            # leave it for the miner and a take speed bonus.

            sweep_utxo_len = config['len-base'] + config['len-per-input'] + config['len-per-output']
            sweep_utxo_fee = sweep_utxo_len * best_fee
            if change < sweep_utxo_fee:
                change_usd = (change/1e8) * btc_price
                logger.warning('Trivial UTXO remainder released to miner {:,.0f} Satoshi ${:,.2f} USD'.format(change, change_usd))

            # return change
            else:

                # merge if change going to dest address
                if (change_address == dest):
                    merged_value = send_satoshi + change
                    logger.warning('Change address same as destination, merging output values {:,.0f}'.format(merged_value))
                    txouts = [ { 'address' : dest, 'value' : merged_value } ]

                # add extra output
                else:
                    txouts.append( { 'address' : change_address, 'value' : change } )
                    logger.debug('OUTPUT 1 Address {} Value {:,.0f}'.format(change_address, change))


    # sanity checks
    sum_ins = sum([x['value'] for x in txins])
    logger.debug('SUM(inputs) = {:,.0f}'.format(sum_ins))

    sum_outs = sum([x['value'] for x in txouts])
    logger.debug('SUM(outputs) = {:,.0f}'.format(sum_outs))

    fee_satoshi = (sum_ins - sum_outs)
    fee_btc = (fee_satoshi/1e8)
    fee_usd = btc_price * fee_btc
    logger.info('Paying miner fee of {:,.0f} Satoshi ${:,.2f} USD'.format(fee_satoshi, fee_usd))

    if (fee_usd < 0):
        logger.critical('Sanity check failed: sum of outputs {:,.0f} exceeds sum of inputs {:,.0f}'.format(sum_outs, sum_ins))
        exit(1)

    elif (fee_usd < 0.01):
        logger.critical('Bad transaction: miner fee too small: ${:,.6f}'.format(fee_usd))
        exit(1)

    if (fee_usd > config['insane-fee-usd']):
        msg = 'Sanity check failed: miner fee too large ${:,.2f} >= ${:,.2f}'.format(fee_usd, config['insane-fee-usd'])
        if args['override']:
            logger.warning(msg)
            logger.warning('Overriding sanity check')
        else:
            logger.error(msg)
            exit(1)


    # sign tx inputs
    tx = mktx(txins, txouts)
    for i in range(len(txins)):
        logger.debug('Signing input {}'.format(i))
        try:
            tx = sign(tx, i, privkeys[txins[i]['address']])
        except:
            logger.critical('Failed to sign UTXO {}'.format(txins[i]['output']))
            exit(1)

    # confirm
    send_btc = send_satoshi/1e8
    confirm  = 'Sending {:,.8f} BTC ${:,.2f} USD '.format(send_btc, send_btc * btc_price)
    confirm += 'from {} to {} '.format(from_addrs, [dest])
    confirm += 'using fee of {:,.8f} BTC ${:,.2f} USD'.format(fee_btc, fee_usd)
    logger.warning(confirm)
    raw_input('[ Press Enter to confirm ]')

    # submit
    tid = broadcast(tx)
    if tid is None:
        logger.critical('Failed to submit transaction to the network')
    else:
        logger.warning('Broadcasted TXID {}'.format(tid))


if __name__ == "__main__":
    main()
