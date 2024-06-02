from typing import Dict,List,Any
import aiohttp
import asyncio
import nest_asyncio
nest_asyncio.apply()
def getUrlWithReq(url:str,AdditionalReq:Dict[str,str]={}) -> str:
    url += "?" + "&".join([f'{key}={value}' for key,value in AdditionalReq.items()])
    return url

def get_json_aio(urlList:List[str],headers = {}) -> List[Dict[str, Any]]:
    async def get_json_single(session:aiohttp.ClientSession, url:str) -> Dict[str, Any]:
        print("request:"+url)
        nowEpoch = 0
        MAXRETRY = 15
        while True:
            try:
                nowEpoch += 1
                async with session.get(url) as response:
                    ret:Dict[str,Any] = await response.json(encoding="utf-8",content_type=response.content_type)
                    print("recieved:"+url)
                    return ret
            except Exception as e:
                print(f"failed:{nowEpoch=}")
                if(nowEpoch >= MAXRETRY):
                    print("failed for all connection, please check the network status")
                    raise e
        
    async def mainProcess():
        async with aiohttp.ClientSession(headers=headers,timeout=aiohttp.ClientTimeout(10.0)) as session:
            tasks = [asyncio.ensure_future(get_json_single(session,url)) for url in urlList]
            return await asyncio.gather(*tasks)
    loop = asyncio.get_event_loop()
    ret = loop.run_until_complete(mainProcess())
    return ret

def get_json(url:str,AdditionalReq:Dict[str,str]={},headers:Dict[str,str] = {}) -> Dict[str, Any]:
    url = getUrlWithReq(url,AdditionalReq)
    return get_json_aio([url],headers)[0]