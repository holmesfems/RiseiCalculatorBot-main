from http.server import HTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse
from urllib.parse import parse_qs
from recruitment import recruitment,recruitFromOCR

def executeHTTPFunction(path,params):
    if(path == "recruitment"):
        text = params["text"][0]
        matchTag = recruitFromOCR.matchTag(text)
        if(matchTag.isEmpty()): return "タグがありません"
        rcReply = recruitment.recruitDoProcess(matchTag,4,matchTag.isGlobal)
        return rcReply.getEmbbedText()
    else:
        return "エラー"
    
class CustomHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path.replace('/','')
        self.wfile.write(f'{executeHTTPFunction(path,params)}'.encode())

server_address = ('0.0.0.0',8080)

def startServer():
    httpd = HTTPServer(server_address,CustomHTTPRequestHandler)
    print("server_started")
    httpd.serve_forever()