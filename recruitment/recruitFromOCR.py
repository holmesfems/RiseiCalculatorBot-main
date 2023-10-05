import os
from typing import Any,List
from google.cloud import vision
from google.auth import api_key
import sys
sys.path.append('../')
from recruitment import recruitment

#print(__tagList)
__eliteTagDict = {item:item for item in recruitment.eliteTags}

__otherTagDict = {item:item for item in recruitment.jobTags + recruitment.positionTags + recruitment.otherTags}
__otherTagDict["範囲攻"] = "範囲攻撃"

def filterNotNone(_list:list) -> list:
    return list(filter(lambda x: x is not None,_list))

def matchEliteTag(result:List[str]) -> List[str]:
    ret = []
    for key,value in __eliteTagDict.items():
        if(key in result):
            ret.append(value)
    return ret

def matchOtherTag(result:List[str]) -> List[str]:
    ret = []
    for key,value in __otherTagDict.items():
        if(any((key in text) for text in result)):
            ret.append(value)
    return ret

def matchTag(result:str) -> List[str]:
    listResult = result.split("\n")
    return matchEliteTag(listResult) + matchOtherTag(listResult)

def taglistFromImage(image:Any)->List[str]:
    API_KEY = os.environ["CLOUDVISION_API_KEY"]
    client = vision.ImageAnnotatorClient(credentials=api_key.Credentials(API_KEY))
    visionImage = vision.Image()
    visionImage.source.image_uri = image

    #メモ
    #text_detectionとdocument_text_detectionの違いがよくわからない
    #料金節約のために、ランダムでどちらかを使うという手もある
    #今は一旦前者のみを使う
    result = client.text_detection(image=visionImage).text_annotations
    result = result[0].description
    print("OCR result:" + result)
    tagList = matchTag(result)
    print(tagList)
    if(len(tagList) != 5):
        print("warning:識別できていないタグがあります")
    return tagList