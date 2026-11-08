"""Explicit real-send probe; user supplies a DEMO_PHONES recipient. Never retries."""
import argparse
import json
import urllib.request


def send(phone, text, port=8787):
    body=json.dumps({'phone':phone,'text':text}).encode()
    req=urllib.request.Request(f'http://127.0.0.1:{port}/send',data=body,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phone',required=True);parser.add_argument('--text',required=True);args=parser.parse_args()
    result=send(args.phone,args.text)
    print(json.dumps({'status':result.get('status'),'message_id':result.get('message_id')}))
