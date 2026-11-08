import json
import subprocess
import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from send import send
from webhook import handler, Inbox
from test_webhook import RAW, SECRET, headers

class Transport(unittest.TestCase):
    def test_python_calls_node_bridge_over_loopback(self):
        cwd=Path(__file__).resolve().parents[1]
        process=subprocess.Popen(['node','--import','tsx','tests/fixture_bridge.ts'],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        try:
            port=int(process.stdout.readline().strip())
            result=send('+12145550100','fixture only',port)
            self.assertEqual(result,{'status':'accepted','message_id':'fixture-message'})
        finally:
            process.terminate();process.wait(timeout=5);process.stdout.close()

    def test_signed_photo_http_and_duplicate(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(SECRET,Inbox()))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            import time
            signed=headers(stamp=int(time.time()))
            for duplicate in (False,True):
                request=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/webhooks/photon',data=RAW,headers=signed)
                with urllib.request.urlopen(request,timeout=5) as response:result=json.load(response)
                self.assertEqual(result['duplicate'],duplicate)
                self.assertEqual(result['content_type'],'image')
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)
