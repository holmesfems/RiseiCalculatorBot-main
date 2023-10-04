import os
import yaml
import itertools
from typing import Any,List
from google.cloud import vision
from google.auth import api_key

with open("./recruitment/tagList.json","rb") as file:
    __tagList = yaml.safe_load(file)
    __tagList = list(itertools.chain.from_iterable(__tagList.values()))

#print(__tagList)

__ocrDict = {item:item for item in __tagList}

def filterNotNone(_list:list) -> list:
    return list(filter(lambda x: x is not None,_list))

def matchTag(result:str) -> str:
    ret = []
    for key in __ocrDict.keys():
        if(key in result): ret.append(key)
    return ret

def taglistFromImage(image:Any)->List[str]:
    API_KEY = os.environ["CLOUDVISION_API_KEY"]
    client = vision.ImageAnnotatorClient(credentials=api_key.Credentials(API_KEY))
    visionImage = vision.Image()
    visionImage.source.image_uri = image
    result = client.document_text_detection(image=visionImage).text_annotations
    result = result[0].description
    print("OCR result:" + result)
    tagList = matchTag(result)
    print(tagList)
    if(len(tagList) != 5):
        print("warning:識別できていないタグがあります")
    return tagList