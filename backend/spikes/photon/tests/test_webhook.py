import hashlib
import hmac
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from webhook import verify, Inbox
NOW=2000000000
SECRET='dummy-test-secret'
RAW=json.dumps({'event':'message.received','message':{'id':'m-1','space':{'id':'s-1'},'content':{'type':'image','url':'https://example.com/photo.jpg'}}}).encode()
def headers(raw=RAW,stamp=NOW,delivery='w-1'):
    return {'X-Spectrum-Timestamp':str(stamp),'X-Spectrum-Signature':'v0='+hmac.new(SECRET.encode(),b'v0:'+str(stamp).encode()+b':'+raw,hashlib.sha256).hexdigest(),'X-Spectrum-Webhook-Id':delivery,'X-Spectrum-Event':'message.received'}
class Verification(unittest.TestCase):
    def test_valid(self):self.assertTrue(verify(RAW,headers(),SECRET,NOW))
    def test_wrong_secret(self):self.assertFalse(verify(RAW,headers(),'wrong',NOW))
    def test_modified_body(self):self.assertFalse(verify(RAW+b' ',headers(),SECRET,NOW))
    def test_expired(self):self.assertFalse(verify(RAW,headers(stamp=NOW-301),SECRET,NOW))
    def test_future(self):self.assertFalse(verify(RAW,headers(stamp=NOW+301),SECRET,NOW))
    def test_missing(self):self.assertFalse(verify(RAW,{},SECRET,NOW))
    def test_malformed(self):self.assertFalse(verify(RAW,headers()|{'X-Spectrum-Timestamp':'nan'},SECRET,NOW))
    def test_case_insensitive(self):self.assertTrue(verify(RAW,{k.lower():v for k,v in headers().items()},SECRET,NOW))
    def test_duplicate_delivery_and_message(self):
        box=Inbox();self.assertFalse(box.accept(RAW,headers(),SECRET,NOW)['duplicate']);self.assertTrue(box.accept(RAW,headers(),SECRET,NOW)['duplicate']);self.assertTrue(box.accept(RAW,headers(delivery='other'),SECRET,NOW)['duplicate'])
    def test_event_mismatch(self):
        with self.assertRaises(ValueError):Inbox().accept(RAW,headers()|{'X-Spectrum-Event':'other'},SECRET,NOW)
    def test_bad_payload_not_marked_seen(self):
        box=Inbox();raw=b'{}'
        with self.assertRaises(ValueError):box.accept(raw,headers(raw),SECRET,NOW)
        self.assertEqual(len(box.seen),0)
    def test_photo_metadata(self):
        self.assertEqual(Inbox().accept(RAW,headers(),SECRET,NOW)['content_type'],'image')
if __name__=='__main__':unittest.main()
