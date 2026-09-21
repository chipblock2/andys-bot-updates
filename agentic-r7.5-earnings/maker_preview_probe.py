#!/usr/bin/env python3
import json, sys, urllib.request
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
sys.path.insert(0,str(PARENT))
import coinbase_live_canary as live

def qdown(value, increment):
    inc=Decimal(str(increment))
    return format((Decimal(str(value))/inc).to_integral_value(rounding=ROUND_DOWN)*inc,'f')

with urllib.request.urlopen('http://127.0.0.1:8787/api/live',timeout=10) as r:
    payload=json.load(r)
asset=(payload.get('assets') or {}).get('ETH') or {}
book=asset.get('coinbase_orderbook') or {}
bid=float(book.get('best_bid') or 0)
ask=float(book.get('best_ask') or 0)
if bid<=0 or ask<=0:
    raise SystemExit('No ETH-GBP book available')

cfg=live._load(live.CONFIG_FILE)
client=live.SERVICE._client(cfg)
product=live.SERVICE._product(client,'ETH-GBP')
base_inc=str(product.get('base_increment') or '0.00000001')
quote_inc=str(product.get('quote_increment') or '0.01')
quote_size=4.00
base_size=qdown(quote_size/bid,base_inc)
limit_price=live._quantize(bid,quote_inc)
target=live._quantize(bid*1.04,quote_inc)
stop=live._quantize(bid*0.98,quote_inc)
order_payload={
    'product_id':'ETH-GBP',
    'side':'BUY',
    'order_configuration':{
        'limit_limit_gtc':{
            'base_size':base_size,
            'limit_price':limit_price,
            'post_only':True,
        }
    },
    'attached_order_configuration':{
        'trigger_bracket_gtc':{
            'limit_price':target,
            'stop_trigger_price':stop,
        }
    },
}
preview=live._as_dict(client.post('/api/v3/brokerage/orders/preview',data=order_payload))
out={
    'ok':bool(preview.get('preview_id')) and not bool(preview.get('errs')),
    'preview_id_present':bool(preview.get('preview_id')),
    'errs':preview.get('errs') or [],
    'commission_total':preview.get('commission_total'),
    'est_average_filled_price':preview.get('est_average_filled_price'),
    'product_id':'ETH-GBP',
    'quote_size_gbp_target':quote_size,
    'base_size':base_size,
    'limit_price':limit_price,
    'best_bid':bid,
    'best_ask':ask,
    'post_only':True,
    'attached_target':target,
    'attached_stop':stop,
    'submitted_order':False,
}
print(json.dumps(out,indent=2))