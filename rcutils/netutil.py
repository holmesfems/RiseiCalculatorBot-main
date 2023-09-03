import urllib.request
import yaml
def get_json(s,AdditionalReq=None,headers = {}):
    if type(AdditionalReq) is dict:
        s += "?" + "&".join(['%s=%s'%(x,AdditionalReq[x]) for x in AdditionalReq])
    print("request:"+s)
    Err = None
    for _ in range(5):
        try:
            req = urllib.request.Request(s, None,headers)
            with urllib.request.urlopen(req, timeout=10) as response: #謎に一回目だけTimeout なぜ
                #print(response)
                #print(s)
                return yaml.safe_load(response.read().decode(),)
        except Exception as e:
            Err = e
    raise Err