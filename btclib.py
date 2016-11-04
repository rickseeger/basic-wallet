

import os, yaml, logging, requests, string, json, re
from validate import validate_address

# logger
logging.basicConfig(format='%(asctime)-15s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


# load config
config = None
config_file = os.path.expanduser('~/.basic-wallet.conf')
try:
    with open(config_file, 'r') as stream:
        config = yaml.load(stream)
except:
    logger.critical('Unable to open config file: {}'.format(config_file))
    exit(1)


# retrieve and validate all wallet addresses
def get_wallet():
    n = 0
    wallet = []

    for item in config['wallet']:
        n += 1
        try:
            name = item['name']
            address = item['address']
            privkey = item['privkey']

        except KeyError:
            logger.error('Wallet address #{} is misconfigured'.format(n))
            continue

        if not validate_address(address):
            logger.error('{} address {} is not a valid Bitcoin address'.format(name, address))
            continue

        wallet.append( {'name' : name, 'address' : address, 'privkey' : privkey } )

    return sorted(wallet, key=lambda k: k['name'])


# find a wallet address by substring match
def lookup(search_string):
    wallet = get_wallet()
    for item in wallet:
        # return first match
        if search_string.lower() in item['name'].lower() or \
           search_string.lower() in item['address'].lower():
            return item
    return None


# convert URL to a unique local filesystem path
def get_cache_path(url):

    if 'cache-dir' not in config.keys() or \
       config['cache-dir'] is None or \
       len(config['cache-dir'].strip()) == 0:
        return None

    if not os.path.exists(config['cache-dir']):
        os.makedirs(config['cache-dir'])

    match = re.match('^(.*:)//([A-Za-z0-9\-\.]+)(:[0-9]+)?(.*)$', url)
    if (match is None):
        logger.error('Invalid URL: {}'.format(url))
        return None

    g = match.groups()
    cache_file = g[1] + '-' + g[3]
    cache_file = re.sub('[=?/.]', '-', cache_file)
    cache_file = re.sub('-+', '-', cache_file)
    cache_path = config['cache-dir'] + '/' + cache_file

    return cache_path


# return the response from a URL get or None
def url_get(url):

    html = None
    cache_path = get_cache_path(url)

    if (config['networking-enabled']):
        try:
            logger.debug('GET {}'.format(url))
            response = requests.get(url)
        except requests.exceptions.RequestException as e:
            logger.error('Request failed: {}'.format(e))
            return None

        html = response.text.strip()
        clean = filter(lambda x: x in string.printable, html)
        logger.debug('RESPONSE {}'.format(clean))

        if cache_path is not None:

            try:
                logger.debug('Caching data to {}'.format(cache_path))
                with open(cache_path, 'w') as cache:
                    cache.write(clean)

            except Exception as e:
                logger.error('Unable to write cache file: {}'.format(e))
        
            status = response.status_code
            if (status != 200):
                logger.error('{} responded with status code {}'.format(url, status))
                return None

    # use cache
    else:
        if cache_path is None:
            logger.error('URL get failed: networking disabled and cache unavailable')
            return None
        else:
            try:
                logger.debug('Loading cached data from {}'.format(cache_path))
                with open(cache_path) as cache:
                    html = cache.read()
            except:
                logger.error('Unable to read cache {}'.format(cache_path))
                return None
            
    return html


# return current balance for address in satoshis or None
def get_balance(address):

    request = '{}/addr/{}/balance'.format(config['api-url'], address)
    balance = url_get(request)

    try:
        balance = int(balance)
    except:
        logger.error('Couldn\'t convert {} to integer'.format(balance))
        return None

    logger.debug('Address {} has a balance of {:,.8f} BTC'.format(address, (balance/1e8)))
    return balance


# broadcast a transaction to the Bitcoin network, return TXID or None
def broadcast(tx_hex):

    url = '{}/tx/send'.format(config['api-url'])
    payload = { 'rawtx' : tx_hex }
    logger.debug('{}  request: {}'.format(url, str(payload)))

    if (not config['networking-enabled']):
        logger.info('Skipping pushtx because network disabled')
        return None

    logger.debug('POST {}'.format(url))
    logger.debug('PAYLOAD {}'.format(payload))
    response = requests.post(url, data=payload)
    html = response.text.strip()
    clean = filter(lambda x: x in string.printable, html)
    logger.debug('RESPONSE {}'.format(clean))

    status = response.status_code
    if (status != 200):
        logger.error('{} responded with status code {}'.format(url, status))
        return None

    try:
        j = json.loads(html)
        tid = j['txid']

    except:
        logger.error('Couldn\'t parse transaction JSON data {} '.format(html))
        return None

    return tid

# return latest BTC price in USD or None
def get_bitcoin_price():

    html = url_get('{}/currency'.format(config['api-url']))
    try:
        quote = json.loads(html)

    except:
        logger.error('Couldn\'t parse JSON: {}'.format(html))
        return None

    try:
        price = float(quote['data']['bitstamp'])

    except Exception as e:
        except_name = type(e).__name__
        logger.error('{} {}'.format(except_name, e))
        return None

    # todo: handle various statuses in response e.g.
    # {
    #   "status": 438,
    #   "error": "Too many requests"
    #   }

    logger.info('Latest bitcoin price is ${:,.2f}'.format(price))
    return price


# returns confirmed UTXOs for an address or None
def get_unspent(address):

    result = []
    url = '{}/addr/{}/utxo'.format(config['api-url'], address)
    html = url_get(url)

    try:
        utxo = json.loads(html)
    except:
        logger.error('Couldn\'t parse transaction JSON data {} '.format(html))
        return None

    try:
        for tx in utxo:
            txinfo = {}

            txid = str(tx['txid'])
            vout = int(tx['vout'])
            confs = int(tx['confirmations'])
            amount = int(tx['satoshis'])

            if (confs < config['min-confirmations']):
                logger.warning('Ignoring UTXO on address {} ({} confirmation{})'.format(address, confs, pluralize(confs)))
                continue

            txinfo['id'] = txid
            txinfo['vout'] = vout
            txinfo['amount'] = amount
            result.append(txinfo)

    except:
        logger.error('Couldn\'t parse UTXO attributes: {}'.format(tx))
        return None

    return result


def pluralize(amount):
    return '' if (amount == 1) else 's'



