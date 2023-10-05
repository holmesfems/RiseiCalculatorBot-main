import urllib.request
import yaml
from typing import Dict,Any,List,Tuple
from concurrent.futures import ThreadPoolExecutor
from itertools import zip_longest

def get_json(url:str,additionalReq:Dict[str,str]=None,header:Dict[str,str] = None) -> Any:
    if type(additionalReq) is dict:
        url += "?" + "&".join(['%s=%s'%(x,additionalReq[x]) for x in additionalReq])
    if not header: header = {}
    print("request:"+url)
    Err = None
    for _ in range(5):
        try:
            req = urllib.request.Request(url, None,header)
            with urllib.request.urlopen(req, timeout=10) as response: #謎に一回目だけTimeout なぜ
                #print(response)
                #print(s)
                print("receieved:"+url)
                return yaml.safe_load(response.read().decode(),)
        except Exception as e:
            Err = e
    raise Err

def __get_json(tupleItem:Tuple[str,Dict[str,str],Dict[str,str]]):
    url = tupleItem[0]
    additionalReq = tupleItem[1]
    headers = tupleItem[2]
    return get_json(url,additionalReq,headers)

def get_json_multiThread(urls:List[str],additionalReqs:List[Dict[str,str]] = [], headers: List[Dict[str,str]] = []):
    tupleItemList = zip_longest(urls,additionalReqs,headers,fillvalue=None)
    length = len(urls)
    with ThreadPoolExecutor(length) as executor:
        results = list(executor.map(__get_json,tupleItemList))
    return results
