
## Install

```
$ git clone https://github.com/rickseeger/basic-wallet.git
$ cd basic-wallet
$ cp sample-basic-wallet.conf ~/.basic-wallet.conf
$ chmod 600 ~/basic-wallet.conf
```

Edit `basic-wallet.conf` as necessary. It contains private keys so make sure it is secure.


## Run tests

```
$ sudo pip install mock
$ ./tests.py
```

## balance.py - fetch balances

```
$ ./balance.py -h

usage: balance.py [-h] [-a] [-s SEARCH] [-v]

Displays Bitcoin balances

optional arguments:
  -h, --help            show this help message and exit
  -a, --showall         show zero balances
  -s SEARCH, --search SEARCH
                        show balance for single address
  -v, --verbose         show verbose output

$ ./balance.py -a

Name                 Address                                           BTC          USD
Fake Example01       14CNnSKK6g8BEcQpfRfe7r888WJ4rnYuJC         0.00000000         0.00
Fake Example02       1VLTg6joM28eVzpRFd7xodHd55XMJbDYB          0.00000000         0.00
Fake Example03       1DA3ykQxaQtkUDwJbnoBY5p8CttwDywwBy         0.00000000         0.00
Genesis Address      1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa        16.53393273    11,422.47
Satoshi Nakamoto     12c6DSiU4Rq3P4ZxziKxzrL5LmMBrzjrJX         0.04329407        29.91
                     Total                                     16.57722680    11,452.38

$ ./balance.py -s example02 -v
2016-11-04 11:31:27,103 DEBUG GET http://crypdex.io:3001/insight-api/currency
2016-11-04 11:31:27,268 DEBUG RESPONSE {"status":200,"data":{"bitstamp":693}}
2016-11-04 11:31:27,268 DEBUG Caching data to /tmp/basic-wallet-cache/crypdex-io-insight-api-currency
2016-11-04 11:31:27,269 INFO Latest bitcoin price is $693.00
2016-11-04 11:31:27,271 DEBUG GET http://crypdex.io:3001/insight-api/addr/1VLTg6joM28eVzpRFd7xodHd55XMJbDYB/balance
2016-11-04 11:31:27,512 DEBUG RESPONSE 0
2016-11-04 11:31:27,512 DEBUG Caching data to /tmp/basic-wallet-cache/crypdex-io-insight-api-addr-1VLTg6joM28eVzpRFd7xodHd55XMJbDYB-balance
2016-11-04 11:31:27,513 DEBUG Address 1VLTg6joM28eVzpRFd7xodHd55XMJbDYB has a balance of 0.00000000 BTC

Name                 Address                                           BTC          USD
Fake Example02       1VLTg6joM28eVzpRFd7xodHd55XMJbDYB          0.00000000         0.00
```

## sendbtc.py - make bitcoin transaction and submit to network

```
$ ./sendbtc.py -h

usage: sendbtc.py [-h] -f FROM [FROM ...] -t TO [-m FEE] [-a AMOUNT] [-v]

Create a Bitcoin transaction

optional arguments:
  -h, --help            show this help message and exit
  -f FROM [FROM ...], --from FROM [FROM ...]
                        one of more from addresses
  -t TO, --to TO        address to send to
  -m FEE, --fee FEE     miner fee in Satoshis per byte
  -a AMOUNT, --amount AMOUNT
                        amount to transfer in BTC
  -v, --verbose         show verbose output

$ ./sendbtc.py -f temp01 -t checking -a 0.001
2016-11-04 10:17:46,374 WARNING Sending 0.00100000 BTC $0.69 USD from ['13Q5m15CNtxrDtBuWdqWuqDjFZYYLbthxr'] to ['1Antvsp2tAsMFrWvDKAtMPJimryDFmJA2u'] using fee of 0.00005160 BTC $0.04 USD
[ Press Enter to confirm ]
2016-11-04 10:18:29,618 WARNING Broadcasted TXID d6733b54ff9b8816872ff0a639aa3885d2eeb445fa5c961237a0cdc03d9a5815

$ # UTXOs without enough confirmations will be ignored
$ ./sendbtc.py -f temp01 -t checking -a 0.0001 -m 20
2016-11-04 10:37:45,159 WARNING Ignoring UTXO on address 1F2VytN357pngbpWPS9b1VLoq95N72QL7a (0 confirmations)
2016-11-04 10:37:45,281 CRITICAL Insufficient funds 11,560 > 0

$ # sweep multiple addresses into one balance with verbose logging
$ ./sendbtc.py -f bitwage miningpool -t checking -v

2016-11-04 10:40:21,994 DEBUG Found destination address BTC Checking 1GT2eXn1ww6feHUUhSAzMU5sNwzkzETLY3 in wallet
2016-11-04 10:40:21,995 DEBUG Found source address Bitwage 1CwJ12eDPfVMd6jAZVJGbWQWeVFyNwhFLL in wallet
2016-11-04 10:40:21,995 DEBUG Found source address Mining Pool 1KvbFkaB6uxxZprQNWZuFtHa9PfqrfSUZ3 in wallet
2016-11-04 10:40:21,995 DEBUG GET http://crypdex.io:3001/insight-api/addr/1CwJ12eDPfVMd6jAZVJGbWQWeVFyNwhFLL/utxo
2016-11-04 10:40:22,200 DEBUG RESPONSE [{"address":"1CwJ12eDPfVMd6jAZVJGbWQWeVFyNwhFLL","txid":"83418bf5129ff55d9778ba50e7563cefebf072dfa2404b05d3ff1665aee3","vout":1,"scriptPubKey":"76a914807f70d72f6cd80fb8bfb09e4ae7c932b60d88ac","amount":0.05360954,"satoshis":5360954,"height":437296,"confirmations":48}]
2016-11-04 10:40:22,201 DEBUG Caching data to /tmp/basic-wallet-cache/crypdex-io-insight-api-addr-1CwJ12eDPfVMd6jAZVJGbWQWeVFyNwhFLL-utxo
2016-11-04 10:40:22,201 DEBUG utxo["value"] = 5360954
2016-11-04 10:40:22,202 DEBUG GET http://crypdex.io:3001/insight-api/currency
2016-11-04 10:40:22,289 DEBUG RESPONSE {"status":200,"data":{"bitstamp":690.12}}
2016-11-04 10:40:22,289 DEBUG Caching data to /tmp/basic-wallet-cache/crypdex-io-insight-api-currency
2016-11-04 10:40:22,290 INFO Latest bitcoin price is $690.12
2016-11-04 10:40:22,290 INFO UTXO summary 1 address 1 UTXO 5,360,954 Satoshi $37.00 USD
2016-11-04 10:40:22,290 DEBUG Using fee of 25 satoshis per byte
2016-11-04 10:40:22,290 WARNING Sweeping entire 5,360,954 satoshi from all UTXOs
2016-11-04 10:40:22,290 INFO Input 0 UTXO 83418bf5129f55d9778ba50e763cefebf020dfa22404b05d3ff1665aee3:1 Value 5,260,954 Total 5,260,954
2016-11-04 10:40:22,290 INFO Input 1 UTXO 40ef3438c1437451b54c7c4b720afc7e0ee633772238bf89c6f70735295:1 Value 100,000 Total 5,360,954
2016-11-04 10:40:22,291 INFO OUTPUT 0 Address 1GT2eXn1ww6feHUUhSAzMU5sNwzkzETLY3 Value 5,355,354
2016-11-04 10:40:22,291 DEBUG SUM(inputs) = 5,360,954
2016-11-04 10:40:22,291 DEBUG SUM(outputs) = 5,355,354
2016-11-04 10:40:22,291 INFO Paying miner fee of 5,600 Satoshi $0.04 USD
2016-11-04 10:40:22,292 DEBUG Signing input 0
2016-11-04 10:40:22,319 WARNING Sending 0.05355354 BTC $36.96 USD from ['1CwJ12eDPfVMd6jAZVJGbWQWeVFyNwhFLL'] to ['1GT2eXn1ww6feHUUhSAzMU5sNwzkzETLY3'] using fee of 0.00005600 BTC $0.04 USD
```

## price.py - gets latest Bitcoin price

```
$ ./price.py -h

usage: price [-h] [-u USD] [-v]

Fetch latest Bitcoin price

optional arguments:
  -h, --help         show this help message and exit
  -u USD, --USD USD  convert a USD dollar amount to BTC
  -v, --verbose      show verbose output

$ ./price.py
$690.85 = 1 BTC

$ ./price.py -u 100
$100.00 = 0.14474922 BTC

```
