from typing import Dict,List,Any
import aiohttp
import asyncio
import aiohttp_retry
import nest_asyncio
nest_asyncio.apply()
def getUrlWithReq(url:str,AdditionalReq:Dict[str,str]=None) -> str:
    if AdditionalReq is not None:
        url += "?" + "&".join([f'{key}={value}' for key,value in AdditionalReq.items()])
    return url

def get_json_aio(urlList:List[str],headers = {}) -> tuple:
    async def get_json_single(session:aiohttp.ClientSession, url:str):
        retryClient = aiohttp_retry.RetryClient(session)
        retryOption = aiohttp_retry.ExponentialRetry(attempts=10,start_timeout=5,max_timeout=10,factor=1.1)
        print("request:"+url)
        async with retryClient.get(url,retry_options=retryOption) as response:
            ret = await response.json(encoding="utf-8",content_type=response.content_type)
            print("recieved:"+url)
            return ret
        
    async def mainProcess():
        async with aiohttp.ClientSession(headers=headers) as session:
            tasks = [asyncio.ensure_future(get_json_single(session,url)) for url in urlList]
            return await asyncio.gather(*tasks)
    loop = asyncio.get_event_loop()
    ret = loop.run_until_complete(mainProcess())
    return ret

def get_json(url:str,AdditionalReq:Dict[str,str]=None,headers = {}) -> Any:
    url = getUrlWithReq(url,AdditionalReq)
    return get_json_aio([url],headers)[0]