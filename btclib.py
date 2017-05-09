
import datetime, bsddb, os, yaml, logging, requests, string, json, re, sys
from validate import validate_address

# logger
logging.basicConfig(format='%(asctime)-15s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


# load config
config = None
config_file = os.path.expanduser('~/.basic-wallet.conf')
with open(config_file, 'r') as stream:
    config = yaml.load(stream)


# retrieve and validate all wallet addresses
def get_wallet():
    n = 0
    wallet = []

    for item in config['wallet']:
        n += 1
        name = None
        address = None
        privkey = None
        active = None

        try:
            name = item['name']
            address = item['address']

            # private key is optional
            if ('privkey' in item.keys()):
                privkey = item['privkey']

            # active flag is optional
            active = True
            if ('active' in item.keys()):
                active = item['active']

        except KeyError:
            logger.error('Wallet address #{} is misconfigured: {}'.format(n, str(item)))
            continue

        if not validate_address(address):
            logger.error('{} address {} is not a valid Bitcoin address'.format(name, address))
            continue

        wallet.append( {'name' : name, 'address' : address, 'privkey' : privkey, 'active' : active } )

    return sorted(wallet, key=lambda k: k['name'])


# find a wallet address by substring match
def lookup(search_string):
    hits = []
    wallet = get_wallet()

    for item in wallet:
        if search_string.lower() in item['name'].lower() or \
           search_string.lower() in item['address'].lower():
            hits.append(item)

    # there can be only one unique matching address
    n = len(hits)
    if n == 0:
        logger.warning('Search string "{}" did not match any wallet entries'.format(search_string))
        return None
    elif n == 1:
        return hits[0]
    else:
        count = 1
        msg = 'Search string "{}" matched multiple addresses:\n'.format(search_string)
        for hit in hits:
            msg += '{:2d} {:40s} {:35s}\n'.format(count, hit['name'], hit['address'])
            count += 1
        logger.error(msg.strip())
        exit(1)


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
def url_get(url, use_cache=False):

    html = None
    cache_path = get_cache_path(url)

    if (config['networking-enabled']) and (use_cache==False):
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
                logger.debug('CACHING data to {}'.format(cache_path))
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
def get_balance(address, use_cache=False):

    request = '{}/addr/{}/balance'.format(config['api-url'], address)
    balance = url_get(request, use_cache)
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


# returns transactions for an address or None
def get_transactions(address):

    txsum = {}
    txdt = {}
    results = []
    memos = load_memos()

    # load address names
    wallet = get_wallet()
    names = {}
    for item in wallet:
        names[item['address']] = item['name']

    # get all tx for this address
    url = '{}/addr/{}'.format(config['api-url'], address)
    html = url_get(url)
    addrinfo = json.loads(html)
    txs = addrinfo['transactions']

    # fetch details on each
    for tx in txs:
        url = '{}/tx/{}'.format(config['api-url'], tx)
        html = url_get(url)
        txinfo = json.loads(html)

        id = txinfo['txid']
        confs = txinfo['confirmations']
        if (confs < config['min-confirmations']):
            logger.warning('Ignoring TX {} ({} confirmation{})'.format(id, confs, pluralize(confs)))
            continue

        ts = int(txinfo['blocktime'])
        dt = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

        vins = txinfo['vin']
        for vin in vins:
            val = float(vin['value'])
            addr = vin['addr']
            if (addr == address):
                if id in txsum.keys():
                    txsum[id] -= val
                else:
                    txsum[id] = -val
                    txdt[id] = dt

        vouts = txinfo['vout']
        for vout in vouts:
            val = float(vout['value'])
            addrs = vout['scriptPubKey']['addresses']
            assert len(addrs) == 1
            if (addrs[0] == address):
                if id in txsum.keys():
                    txsum[id] += val
                else:
                    txsum[id] = val
                    txdt[id] = dt

    for id in sorted(txdt.keys(), key=lambda k: txdt[k]):
        txt = names[address]
        if id[:16] in memos.keys():
            txt = memos[id[:16]]
        rec = {}
        rec['id'] = id
        rec['date'] = txdt[id]
        rec['amount'] = txsum[id]
        rec['memo'] = txt
        results.append(rec)

    return results


def pluralize(amount):
    return '' if (amount == 1) else 's'


def load_memos():
    fname = os.path.expanduser(config['memo-file'])
    if not os.path.isfile(fname):
        logger.warning('creating new memo file {}'.format(fname))
        save_memos({})

    try:
        with open(fname, 'r') as mfile:
            memos = json.load(mfile)
            clipped = {}
            for k in memos.keys():
                clipped[k[:16]] = memos[k]
            logger.debug('loaded {} memo{} from {}'.format(len(memos), pluralize(len(memos)), fname))
            return clipped
    except:
        logger.critical('Unable to parse memo file {}'.format(fname))
        exit(1)


def save_memos(memos):
    fname = os.path.expanduser(config['memo-file'])
    try:
        with open(fname, 'w') as mfile:
            mfile.write(json.dumps(memos, indent=4))
            logger.debug('saved {} memo{} to {}'.format(len(memos), pluralize(len(memos)), fname))

    except:
        logger.critical('Unable to save memo file {} DUMP {}'.format(fname, memos))
        exit(1)


# returns latest fast confirmation fee as satoshi/byte
def bitcoin_fee(blockTarget=2):

    # 21.co
#    url =  'https://bitcoinfees.21.co/api/v1/fees/recommended'
#    response = url_get(url)
#    fees = json.loads(response)
#    return float(fees['fastestFee'])

    # bitgo
    url = 'https://www.bitgo.com/api/v1/tx/fee?numBlocks={}'.format(blockTarget)
    response = url_get(url)
    fees = json.loads(response)
    targets = fees['feeByBlockTarget']
    fee = targets[str(blockTarget)]
    return fee/1000.0

