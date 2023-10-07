import urllib.request
import yaml
from typing import Dict

def get_json(url:str,AdditionalReq:Dict[str,str]=None,headers = {}) -> dict:
    if type(AdditionalReq) is dict:
        url += "?" + "&".join(['%s=%s'%(x,AdditionalReq[x]) for x in AdditionalReq])
    print("request:"+url)
    Err = None
    for i in range(5):
        try:
            req = urllib.request.Request(url, None,headers)
            with urllib.request.urlopen(req, timeout=10) as response: #謎に一回目だけTimeout なぜ
                #print(response)
                ret = yaml.safe_load(response.read().decode(),)
                print("recieved:"+url)
                return ret
        except Exception as e:
            Err = e
            print(f"failed (epoch: {i+1})")
    raise Err