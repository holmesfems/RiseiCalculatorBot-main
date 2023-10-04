import easyocr
import yaml
import itertools
from typing import Any,List
reader = easyocr.Reader(['ja'],gpu=False)
with open("./recruitment/tagList.json","rb") as file:
    __tagList = yaml.safe_load(file)
    __tagList = list(itertools.chain.from_iterable(__tagList.values()))

print(__tagList)

__ocrDict = {item:item for item in __tagList}
__ocrDict['近亜離'] = '近距離'
__ocrDict['遠亜離'] = '遠距離'
__ocrDict['回復']   = 'COST回復'

def filterNotNone(_list:list) -> list:
    return list(filter(lambda x: x is not None,_list))

def matchTag(ocrtext:str) -> str:
    for key in __ocrDict.keys():
        if(key in ocrtext): return __ocrDict[key]
    return None

def taglistFromImage(image:Any)->List[str]:
    result = reader.readtext(image,detail=0)
    print(result)
    tagList = filterNotNone([matchTag(text) for text in result])
    print(tagList)
    if(len(tagList != 5)):
        print("warning:識別できていないタグがあります")
    return tagList
    
