import os
from typing import Any,List
from google.cloud import vision
from google.auth import api_key
import sys
sys.path.append('../')
from recruitment import recruitment
import yaml

#print(__tagList)
__eliteTagDict = {item:item for item in recruitment.eliteTags}

__otherTagDict = {item:item for item in recruitment.jobTags + recruitment.positionTags + recruitment.otherTags}
__otherTagDict["範囲攻"] = "範囲攻撃"

with open("recruitment/tagEnToJa.yaml","rb") as f:
    __enTagDict = yaml.safe_load(f)

def filterNotNone(_list:list) -> list:
    return list(filter(lambda x: x is not None,_list))

def matchEliteTag(result:List[str]) -> List[str]:
    ret = []
    for key,value in __eliteTagDict.items():
        if value in ret: continue
        if(key in result):
            ret.append(value)
    return ret

def matchOtherTag(result:List[str]) -> List[str]:
    ret = []
    for key,value in __otherTagDict.items():
        if value in ret: continue
        if(any((key in text) for text in result)):
            ret.append(value)
    return ret

def matchEnTag(result:List[str]) -> List[str]:
    ret = []
    for key,value in __enTagDict.items():
        if value in ret: continue
        if(key in result):
            ret.append(value)
    return ret

def matchTag(result:str) -> List[str]:
    listResult = result.split("\n")
    jpMatch = matchEliteTag(listResult) + matchOtherTag(listResult)
    if(len(jpMatch)>=5):return jpMatch
    enMatch = matchEnTag(listResult)
    if(len(enMatch) >= len(jpMatch)): return enMatch
    return jpMatch

def taglistFromImage(imageURI:str)->List[str]:
    API_KEY = os.environ["CLOUDVISION_API_KEY"]
    client = vision.ImageAnnotatorClient(credentials=api_key.Credentials(API_KEY))
    visionImage = vision.Image()
    visionImage.source.image_uri = imageURI

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
        print("warning:タグの数が想定と違います")
    return tagList