"""Native Spectrum webhook signature verification. No raw secrets or message bodies logged."""
import hashlib
import hmac
import json
import os
import re
import threading
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def verify(raw: bytes, headers, secret: str, now=None) -> bool:
    headers = {k.lower(): v for k,v in headers.items()}
    stamp = headers.get('x-spectrum-timestamp','')
    signature = headers.get('x-spectrum-signature','')
    if not secret or not re.fullmatch(r'\d{1,12}',stamp) or not re.fullmatch(r'v0=[0-9a-f]{64}',signature):
        return False
    if abs((time.time() if now is None else now)-int(stamp))>300:
        return False
    expected = 'v0='+hmac.new(secret.encode(),b'v0:'+stamp.encode()+b':'+raw,hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected,signature)


class Inbox:
    """Process-local bounded dedupe for a spike; replace with persistent inbox in production."""
    def __init__(self):
        self.seen = OrderedDict()
        self.lock = threading.Lock()

    def accept(self, raw, headers, secret, now=None):
        if not verify(raw,headers,secret,now): raise PermissionError('Invalid signature or timestamp')
        lower = {k.lower():v for k,v in headers.items()}
        payload = json.loads(raw)
        message = payload.get('message',{})
        event = payload.get('event')
        if not isinstance(message,dict) or not isinstance(message.get('id'),str) or not message['id'] or not isinstance(event,str):
            raise ValueError('Expected native Spectrum envelope')
        if lower.get('x-spectrum-event')!=event: raise ValueError('Event header does not match signed payload')
        webhook_id = lower.get('x-spectrum-webhook-id','')
        if not webhook_id: raise ValueError('Missing webhook delivery id')
        # Deduplicate either repeated delivery IDs or the same logical message/event in another delivery.
        keys = [('delivery',webhook_id),('message',event,message['id'])]
        with self.lock:
            current = time.time() if now is None else now
            for key,until in list(self.seen.items()):
                if until<current:self.seen.pop(key,None)
            duplicate = any(key in self.seen for key in keys)
            for key in keys:self.seen[key]=current+600
            while len(self.seen)>10000:self.seen.popitem(last=False)
        return {'ok':True,'duplicate':duplicate,'event':event,'message_id':message['id'],'content_type':message.get('content',{}).get('type') if isinstance(message.get('content'),dict) else None}


def handler(secret, inbox):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            if self.path!='/health':self.send_error(404);return
            self.send_response(200);self.end_headers();self.wfile.write(b'{"ok":true}')
        def do_POST(self):
            if self.path!='/api/webhooks/photon':self.send_error(404);return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<=0 or size>1048576:raise ValueError('Body size invalid')
                raw=self.rfile.read(size)
                result=inbox.accept(raw,dict(self.headers),secret)
                print(json.dumps(result),flush=True)
                code=200
            except PermissionError: code,result=401,{'error':'Invalid webhook signature or expired timestamp'}
            except (ValueError,TypeError,AttributeError): code,result=400,{'error':'Invalid native webhook envelope'}
            self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(result).encode())
    return Handler


if __name__=='__main__':
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2]/'.env')
    secret=os.environ.get('SPECTRUM_WEBHOOK_SECRET','')
    if not secret:raise SystemExit('Set SPECTRUM_WEBHOOK_SECRET securely before starting webhook receiver')
    print('Verified webhook receiver on loopback port 8788',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8788),handler(secret,Inbox())).serve_forever()
