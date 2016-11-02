

import os, time, logging, requests, string, json, re


# logging
logging.basicConfig(format='%(asctime)-15s %(levelname)s %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)


# config
networking_enabled = True
min_confirmations = 1
max_fee_usd = 5.00
default_fee_per_byte = 30
cache_dir = '/home/rseeger/cache'
key_file = '/home/rseeger/proj/blockchains/bitcoin/keys'
api_url = 'http://crypdex.io:3001/insight-api'


def pluralize(amount):
    return '' if (amount == 1) else 's'


# convert URL to a valid local filesystem path
def get_cache_path(url):
    match = re.match('^(.*:)//([A-Za-z0-9\-\.]+)(:[0-9]+)?(.*)$', url)

    if (match is None):
        logger.critical('Invalid URL: {}'.format(url))
        exit(1)

    g = match.groups()
    cache_file = g[1] + '-' + g[3]
    cache_file = re.sub('[=?/.]', '-', cache_file)
    cache_file = re.sub('-+', '-', cache_file)
    cache_path = cache_dir + '/' + cache_file

    return cache_path



def url_get(url):

    html = None
    cache_path = get_cache_path(url)
    if (networking_enabled):
        try:
            response = requests.get(url)
        except requests.exceptions.RequestException as e:
            logger.critical('Request to {} failed: {}'.format(url, e))
            exit(1)

        # cache responses
        html = response.text.strip()
        clean = filter(lambda x: x in string.printable, html)

        try:
            logger.debug('Caching data to {}'.format(cache_path))
            with open(cache_path, 'w') as cache:
                cache.write(clean)

        except Exception as e:
            logger.critical('Enable to write cache file: {}'.format(e))
            exit(1)
        
        status = response.status_code
        if (status != 200):
            logger.critical('{} responded with status code {}'.format(url, status))
            exit(1)

    # use local cache
    else:
        try:
            logger.debug('Loading cached data from {}'.format(cache_path))
            with open(cache_path) as cache:
                html = cache.read()
        except:
            logger.critical('Unable to read cache {}'.format(cache_path))
            exit(1)
            
    return html


# confirm transaction
def confirm_tx(tid):

    btc_price = get_bitcoin_price()
    dbconn = dbopen()
    dbcursor = dbconn.cursor()

    # mark confirmed
    s  = ' UPDATE transactions SET '
    s += ' status = "confirmed", '
    s += ' ended = now() '
    s += ' WHERE id = {}'.format(tid)
    sql(dbcursor, s)
    dbconn.commit()

    # get amount and currency name
    s  = ' SELECT (transactions.units * currencies.price_usd), '
    s += '        currencies.symbol, currencies.fullname '
    s += ' FROM transactions, currencies '
    s += ' WHERE transactions.symbol = currencies.symbol '
    s += ' AND transactions.id = {} '.format(tid)
    sql(dbcursor, s)
    f = dbcursor.fetchone()
    usd = float(f[0])
    symbol = str(f[1])
    name = str(f[2])
 
    # report transaction done
    btc = usd / btc_price
    if (symbol == 'BTC'):
        announcer.info('transferred {:,.2f} mBTC ${:,.2f} USD to cold storage'.format(1000.0*btc, usd))
    else:
        shortname = name.split()[0]
        announcer.info('converted {:,.2f} mBTC ${:,.2f} USD to {} #{}'.format(1000.0*btc, usd, symbol, shortname))

    dbcursor.close()
    dbconn.close()

    # return current balance for address in satoshis
def get_raw_balance(address):

    request = '{}/addr/{}/balance'.format(api_url, address)
    balance = url_get(request)

    try:
        balance = int(balance)
    except:
        logger.critical('Couldn\'t convert {} to integer'.format(balance))
        exit(1)

    logger.debug('Address {} has a raw balance of {:,.0f}'.format(address, balance))
    return balance


# broadcast a transaction to the Bitcoin network
def broadcast(tx_hex):

    url = '{}/tx/send'.format(api_url)
    payload = { 'rawtx' : tx_hex }
    logger.debug('{}  request: {}'.format(url, str(payload)))

    if (not networking_enabled):
        logger.info('Skipping pushtx because network disabled')
        return False

    response = requests.post(url, data=payload)
    html = response.text.strip()
    logger.debug('{} response: {}'.format(url, html))

    status = response.status_code
    if (status != 200):
        logger.error('{} responded with status code {}'.format(url, status))
        return False

    try:
        j = json.loads(html)
        tid = j['txid']

    except:
        logger.critical('Couldn\'t parse transaction JSON data {} '.format(html))
        exit(1)

    return tid


def get_bitcoin_price():

    # parse response
    html = url_get('{}/currency'.format(api_url))
    try:
        quote = json.loads(html)

    except:
        logger.critical('Couldn\'t parse JSON: {}'.format(html))
        exit(1)

    try:
        price = float(quote['data']['bitstamp'])

    except Exception as e:
        except_name = type(e).__name__
        logger.critical('{} {}'.format(except_name, e))
        exit(1)

    # todo: handle various statuses in response 
    # {
    #   "status": 200,
    #   "data": {
    #     "bitstamp": 691.93
    #     }
    #   }

    logger.info('Latest bitcoin price is ${:,.2f}'.format(price))
    return price



# returns confirmed UTXOs for an address
def get_unspent(address):

    result = []
    url = '{}/addr/{}/utxo'.format(api_url, address)
    html = url_get(url)

    try:
        utxo = json.loads(html)
    except:
        logger.critical('Couldn\'t parse transaction JSON data {} '.format(html))
        exit(1)

    try:
        for tx in utxo:
            txinfo = {}

            txid = str(tx['txid'])
            vout = int(tx['vout'])
            confs = int(tx['confirmations'])
            amount = int(tx['satoshis'])

            if (confs < min_confirmations):
                logger.debug('Ignoring UTXO {} on address {} ({} confirmation{})'.format(txid, address, confs, pluralize(confs)))
                continue

            txinfo['id'] = txid
            txinfo['vout'] = vout
            txinfo['amount'] = amount
            result.append(txinfo)

    except:
        logger.critical('Couldn\'t parse UTXO attributes: {}'.format(tx))
        exit(1)

    return result


"""Validate bitcoin/altcoin addresses
Copied from:
http://rosettacode.org/wiki/Bitcoin/address_validation#Python
"""

import string
from hashlib import sha256

digits58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def _bytes_to_long(bytestring, byteorder):
    """Convert a bytestring to a long

    For use in python version prior to 3.2
    """
    result = []
    if byteorder == 'little':
        result = (v << i * 8 for (i, v) in enumerate(bytestring))
    else:
        result = (v << i * 8 for (i, v) in enumerate(reversed(bytestring)))
    return sum(result)

def _long_to_bytes(n, length, byteorder):
    """Convert a long to a bytestring

    For use in python version prior to 3.2
    Source:
    http://bugs.python.org/issue16580#msg177208
    """
    if byteorder == 'little':
        indexes = range(length)
    else:
        indexes = reversed(range(length))
    return bytearray((n >> i * 8) & 0xff for i in indexes)

def decode_base58(bitcoin_address, length):
    """Decode a base58 encoded address

    This form of base58 decoding is bitcoind specific. Be careful outside of
    bitcoind context.
    """
    n = 0
    for char in bitcoin_address:
        try:
            n = n * 58 + digits58.index(char)
        except:
            msg = u"Character not part of Bitcoin's base58: '%s'"
            raise ValueError(msg % (char,))
    try:
        return n.to_bytes(length, 'big')
    except AttributeError:
        # Python version < 3.2
        return _long_to_bytes(n, length, 'big')

def encode_base58(bytestring):
    """Encode a bytestring to a base58 encoded string
    """
    # Count zero's
    zeros = 0
    for i in range(len(bytestring)):
        if bytestring[i] == 0:
            zeros += 1
        else:
            break
    try:
        n = int.from_bytes(bytestring, 'big')
    except AttributeError:
        # Python version < 3.2
        n = _bytes_to_long(bytestring, 'big')
    result = ''
    (n, rest) = divmod(n, 58)
    while n or rest:
        result += digits58[rest]
        (n, rest) = divmod(n, 58)
    return zeros * '1' + result[::-1]  # reverse string

def validate(bitcoin_address, magicbyte=0):
    """Check the integrity of a bitcoin address

    Returns False if the address is invalid.
    >>> validate('1AGNa15ZQXAZUgFiqJ2i7Z2DPU2J6hW62i')
    True
    >>> validate('')
    False
    """
    if isinstance(magicbyte, int):
        magicbyte = (magicbyte,)
    clen = len(bitcoin_address)
    if clen < 27 or clen > 35: # XXX or 34?
        return False
    allowed_first = tuple(string.digits)
    try:
        bcbytes = decode_base58(bitcoin_address, 25)
    except ValueError:
        return False
    # Check magic byte (for other altcoins, fix by Frederico Reiven)
    for mb in magicbyte:
        if bcbytes.startswith(chr(int(mb))):
            break
    else:
        return False
    # Compare checksum
    checksum = sha256(sha256(bcbytes[:-4]).digest()).digest()[:4]
    if bcbytes[-4:] != checksum:
        return False
    # Encoded bytestring should be equal to the original address,
    # for example '14oLvT2' has a valid checksum, but is not a valid btc
    # address
    return bitcoin_address == encode_base58(bcbytes)
