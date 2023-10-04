from paddleocr import PaddleOCR, draw_ocr
import yaml
import itertools
from typing import Any,List

ocr = PaddleOCR(lang="japan")

with open("./recruitment/tagList.json","rb") as file:
    __tagList = yaml.safe_load(file)
    __tagList = list(itertools.chain.from_iterable(__tagList.values()))

print(__tagList)

__ocrDict = {item:item for item in __tagList}

def filterNotNone(_list:list) -> list:
    return list(filter(lambda x: x is not None,_list))

def matchTag(ocrtext:str) -> str:
    for key in __ocrDict.keys():
        if(key in ocrtext): return __ocrDict[key]
    return None

def taglistFromImage(image:Any)->List[str]:
    result = ocr.ocr(image)
    result = [line[1][0] for line in result]
    print(result)
    tagList = filterNotNone([matchTag(text) for text in result])
    print(tagList)
    if(len(tagList != 5)):
        print("warning:識別できていないタグがあります")
    return tagList
    
