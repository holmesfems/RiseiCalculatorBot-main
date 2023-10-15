from typing import Dict,List,Any
import aiohttp
import asyncio
import aiohttp_retry
import yaml

def getUrlWithReq(url:str,AdditionalReq:Dict[str,str]=None) -> str:
    if AdditionalReq is not None:
        url += "?" + "&".join(['%s=%s'%(key,value) for key,value in AdditionalReq.items()])
    return url

def get_json_aio(urlList:List[str],headers = {}) -> tuple:
    async def get_json_single(session:aiohttp.ClientSession, url:str):
        retryClient = aiohttp_retry.client.RetryClient(session)
        retryOption = aiohttp_retry.retry_options.RetryOptionsBase(attempts=10)
        print("request:"+url)
        async with retryClient.get(url,retry_options=retryOption) as response:
            try:
                ret = await response.json(encoding="utf-8",content_type="text/plain")
            except Exception as _:
                ret = await response.json(encoding="utf-8")
            print("recieved:"+url)
            return ret
        
    async def mainProcess():
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(headers=headers,timeout =timeout) as session:
            tasks = [asyncio.ensure_future(get_json_single(session,url)) for url in urlList]
            return await asyncio.gather(*tasks)
    return tuple(asyncio.run(mainProcess()))

def get_json(url:str,AdditionalReq:Dict[str,str]=None,headers = {}) -> Any:
    url = getUrlWithReq(url,AdditionalReq)
    return get_json_aio([url],headers)[0]