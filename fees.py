#!/usr/bin/env python


# Fetches best fee for quick confirm


import json
from btclib import url_get


response = url_get('https://bitcoinfees.21.co/api/v1/fees/recommended')
fees = json.loads(response)
best = fees['fastestFee']

print best
