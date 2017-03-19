#!/usr/bin/env python

import sys, os, json, unittest, logging
from mock import patch
from validate import validate_address
from btclib import config, logger, get_wallet, get_bitcoin_price, lookup
from btclib import get_cache_path, url_get, get_balance, get_unspent

logger.setLevel(100)  # suppress logging


class TestAddressValidation(unittest.TestCase):

    valid_addresses = [ '1PFzobFoKmEnUu2AKJ5JTKrXaR5vh5Ejp6',
                        '1447xMP8SWGEK88DTtQmH35Jn2U3fY6JAG',
                        '1LCcFfMVa4WnSDxngZhiVzpmCPcCvXMat5'
                        ]

    invalid_addresses = [ '',
                          'NotAnAddress'
                          '19ChmEKxFCMhQTDTniZ2BR7YRgvPz19tu8',
                          '9268FM3VGLR7uvbFEesydGYtCPmc1uDcpx',
                          '1J9MSBD4z62M2u654XzwavTgtaKdUbigGB'
                          ]
    
    def test_valid_bitcoin_adresses(self):
        for address in self.valid_addresses:
            self.assertTrue(validate_address(address), 'False negative')
 
    def test_invalid_bitcoin_addresses(self):
        for address in self.invalid_addresses:
            self.assertFalse(validate_address(address), 'False positive')


class TestGetWallet(unittest.TestCase):

    def test_skipping_invalid_records(self):
        config['wallet'] = [ { 'name' : 'alpha',
                               'INVALID_KEY' : '1HsNZvVHem7oSJRNWJ7dwfJ9YeYMwKWm9N',
                               'privkey' : '5KXu2kcSp6RNgSQNRcQ2zZKyWBA3DJDjZUCpQw8Hhze8qLPfAuN' },
                             { 'name' : 'beta',
                               'address' : '1JGrvwAK9c8yekEAmkDtVQ7YqtHD2zC5Wy',
                               'privkey' : '5KXu2kcSp6RNgSQNRcQ2zZKyWBA3DJDjZUCpQw8Hhze8qLPfAuN' },
                             { 'name' : 'gamma',
                               'address' : 'INVALID_ADDRESS',
                               'privkey' : '5KXu2kcSp6RNgSQNRcQ2zZKyWBA3DJDjZUCpQw8Hhze8qLPfAuN' } ]

        wallet = get_wallet()
        self.assertTrue(len(wallet) == 1)
        self.assertEqual(wallet[0]['name'], 'beta')


class TestAddressLookup(unittest.TestCase):

    def test_lookup(self):
        global config

        config['wallet'] = [ { 'name' : 'alpha',
                               'address' : '1HsNZvVHem7oSJRNWJ7dwfJ9YeYMwKWm9N',
                               'privkey' : '5KXu2kcSp6RNgSQNRcQ2zZKyWBA3DJDjZUCpQw8Hhze8qLPfAuN' },
                             { 'name' : 'beta',
                               'address' : '15bYG3AKp48NcBPZZZZQnASrBmgYZhiTxZ',
                               'privkey' : '5HraMsZ1tQsAnUmpzYjV6RtehyqkGadEPz6oRkEAw3kn63LvzX4' },
                             { 'name' : 'gamma',
                               'address' : '1LrcWfoypPW8paysq3ruY44Jhe1WgLVZ8Q',
                               'privkey' : '5K2yLG2VZyrxJ3TVkkm7Uk1EDXwuYbiexbQpLyrbHVJTnvvVaeT' } ]

        item = lookup('alpha')
        self.assertEqual(item['name'], 'alpha', 'search by name substring failed')

        item = lookup('ZZZZ')
        self.assertEqual(item['name'], 'beta', 'search by address substring failed')

        item = lookup('1LrcWfoypPW8paysq3ruY44Jhe1WgLVZ8Q')
        self.assertEqual(item['name'], 'gamma', 'search by exact address failed')
        

class TestCache(unittest.TestCase):
    
    def test_get_cache_path(self):
        global config
        config['cache-dir'] = '/tmp/cache'
        url = 'http://crypdex.io:3001/insight-api/addr/1GuC79vz3P17LF6KjRG9nC6i41y9b4RXPB/balance'
        path = get_cache_path(url)
        self.assertEqual(path, '/tmp/cache/crypdex-io-insight-api-addr-1GuC79vz3P17LF6KjRG9nC6i41y9b4RXPB-balance')

    def test_get_cache_path_invalid_url(self):
        url = 'this is a malformatted URL'
        path = get_cache_path(url)
        self.assertIsNone(path, 'get_cache_path should return None if passed an invalid URL')

    def test_url_get_with_network_on_cache_off(self):
        global config
        config['api-url'] = 'http://crypdex.io:3001/insight-api'
        config['networking-enabled'] = True
        config['cache-dir'] = None
        sentinel = '1PiNGDYSiV939f5GDwA7QJix1NZRgviP2H'
        url = '{}/addr/{}/utxo'.format(config['api-url'], sentinel)
        html = url_get(url)
        utxos = json.loads(html)
        self.assertEqual(len(utxos), 1)
        
    def test_url_get_with_network_off_cache_off(self):
        global config
        config['api-url'] = 'http://crypdex.io:3001/insight-api'
        config['networking-enabled'] = False
        config['cache-dir'] = None
        sentinel = '1PiNGDYSiV939f5GDwA7QJix1NZRgviP2H'
        url = '{}/addr/{}/balance'.format(config['api-url'], sentinel)
        html = url_get(url)
        self.assertIsNone(html, 'url_get() should return None when network and cache are both disabled')


    def test_url_get_cache_miss(self):
        global config
        config['api-url'] = 'http://crypdex.io:3001/insight-api'
        config['networking-enabled'] = True
        config['cache-dir'] = '/tmp/basic-wallet-test-cache/'
        sentinel = '1PiNGDYSiV939f5GDwA7QJix1NZRgviP2H'
        url = '{}/addr/{}/balance'.format(config['api-url'], sentinel)

        satoshi = int(url_get(url))
        self.assertEqual(satoshi, 123456)

        # verify directory was created
        self.assertTrue(os.path.isdir(config['cache-dir']))

        # verify cache file exists
        cache_file = get_cache_path(url)
        self.assertTrue(os.path.isfile(cache_file))


    def test_url_cache_hit(self):
        global config
        config['api-url'] = 'http://crypdex.io:3001/insight-api'
        config['cache-dir'] = '/tmp/basic-wallet-test-cache/'

        sentinel = '1PiNGDYSiV939f5GDwA7QJix1NZRgviP2H'

        url = '{}/addr/{}/balance'.format(config['api-url'], sentinel)
        balance = 123456
        
        # create cache file
        config['networking-enabled'] = True
        satoshi = int(url_get(url))
        self.assertEqual(satoshi, balance)

        # read from cache
        config['networking-enabled'] = False
        satoshi = int(url_get(url))
        self.assertEqual(satoshi, balance, 'cache read failed')
        

class TestGetBalance(unittest.TestCase):

    def test_get_sentinel_balance(self):
        sentinel = '1PiNGDYSiV939f5GDwA7QJix1NZRgviP2H'
        actual_balance = 123456
        fetched_balance = get_balance(sentinel)
        self.assertEqual(actual_balance, fetched_balance, 'get_balance("{}") is {} but should be {}'.format(sentinel, fetched_balance, actual_balance))

    def test_get_balance_invalid_address(self):
        bal = get_balance('1Nj4wdgAAxu3TP2WDZAWKefXbeD79WPiv')
        self.assertIsNone(bal, 'get_balance() returned {} instead of None when passed an invalid address'.format(bal))

        
class TestPriceFetch(unittest.TestCase):

    def test_get_bitcoin_price(self):
        price = get_bitcoin_price()
        self.assertTrue(isinstance(price, float), 'bitcoin price is {} not {}'.format(type(price), float))
        self.assertTrue(price > 0, 'bitcoin price is not positive')


class TestGetUnspent(unittest.TestCase):

    def test_get_sentinel_utxos(self):
        sentinel = '1PiNGDYSiV939f5GDwA7QJix1NZRgviP2H'
        actual_utxos = [{'amount': 123456, 'id': 'e18f8d62dedd0dafb68fb82c468ef1a2f14040d249738f42538e332f16829417', 'vout': 0}]
        fetched_utxos = get_unspent(sentinel)
        self.assertEqual(actual_utxos, fetched_utxos, 'get_unspent("{}") is {} but should be {}'.format(sentinel, fetched_utxos, actual_utxos))

    def test_get_utxos_invalid_address(self):
        bal = get_unspent('16YJG2tGrAhe4NPHeDfzwfmSkF16Mdzb2w')
        self.assertIsNone(bal, 'get_unspent() returned {} instead of None when passed an invalid address'.format(bal))

        
if __name__ == '__main__':
    unittest.main()
