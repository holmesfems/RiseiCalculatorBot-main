import os,sys,re
from typing import List,Set,Dict,Optional
from google.cloud import vision_v1 as vision
from google.auth import api_key
sys.path.append('../')
import yaml

#下二つと統一、日本版認識用
with open("recruitment/tagJaToJa.yaml","rb") as f:
    __jaTagDict = yaml.safe_load(f)
    #補正用データ
    __jaExtraDict = {
        r"範囲攻." : "範囲攻撃",
        r"範圍攻擊": "範囲攻撃",
        r"(?!上級)(..)?一下" : "エリート",
        r"医療...?": "医療",
        r"上級..一下": "上級エリート",
        r"補助...?": "補助",
        r"狙撃...?": "狙撃",
        r"COSTO": "COST回復",
        r"防御.": "防御"
    }

#英語版認識用
with open("recruitment/tagEnToJa.yaml","rb") as f:
    __enTagDict = yaml.safe_load(f)

#大陸版認識用
with open("recruitment/tagZhToJa.yaml","rb") as f:
    __zhTagDict = yaml.safe_load(f)

def filterNotNone(_list:list) -> list:
    return list(filter(lambda x: x is not None,_list))

def matchTagCoreProcess(result:List[str],baseDict:Dict[str,str],extraDict:Optional[Dict[str,str]]=None)->Set[str]:
    #Google-OCRの精度がかなり良いので、基本完全一致で探してもちゃんとタグを出してくれる
    #一回タグを分離できなかった事例があったので、in検索に切り替えてみる
    #https://discord.com/channels/915241738174627910/1141408003308925059/1170769419346133093
    #追記: in検索では「エリート」を「上級エリート」に含まれてしまうので、空欄split or 完全一致のハイブリッドに
    ret = set()
    for key,value in baseDict.items():
        if value in ret: continue
        if(any((key == text or key in text.split(" ")) for text in result)):
            ret.add(value)
    if(not extraDict): return ret
    #一部誤字するやつがあるので、in検索で結果を補正
    #上級エリート、エリートの識別に難があったので、より自由度の高い正規表現マッチングをする
    for key,value in extraDict.items():
        if len(ret)>=5: break
        if value in ret:continue
        if(any((re.match(key,text)) for text in result)):
            ret.add(value)
    return ret

def matchJaTag(result:List[str]) -> Set[str]:
    return matchTagCoreProcess(result,__jaTagDict,__jaExtraDict)

def matchEnTag(result:List[str]) -> Set[str]:
    return matchTagCoreProcess(result,__enTagDict)

def matchZhTag(result:List[str]) -> Set[str]:
    return matchTagCoreProcess(result,__zhTagDict)

class MatchTagResponseData:
    def __init__(self,matches:Set[str],isGlobal:bool):
        self.matches = matches
        self.isGlobal = isGlobal

    def isIllegal(self):
        return len(self.matches) != 5
    
    def __repr__(self) -> str:
        return f"{self.matches=}, {self.isGlobal=}"

def matchTag(result:str) -> MatchTagResponseData:
    clearRegex = r"[.,·・´`‧]"
    listResult = result.split("\n")
    listResult = [re.sub(clearRegex,"",item).replace('ブ',"プ").strip() for item in listResult] #塵の影響を除去..?

    #localeの判断は当てにならないので(大体undになる)、順番にマッチを試す
    #そこまでコストの高い計算でもないので、現状これでいいでしょう
    jpMatch = matchJaTag(listResult)
    if(len(jpMatch)>=5): return MatchTagResponseData(jpMatch,isGlobal=True)
    #日本語ではない、英語マッチを試す
    enMatch = matchEnTag(listResult)
    if(len(enMatch)>=5): return MatchTagResponseData(enMatch,isGlobal=True)
    #英語でなければ中国語マッチを試す
    zhMatch = matchZhTag(listResult)
    if(len(zhMatch)>=5): return MatchTagResponseData(zhMatch,isGlobal=False)
    #万が一のマッチミス、日本語と中国語のマッチ結果を結合してみる
    jpzhMatch = jpMatch.union(zhMatch)
    if(len(jpzhMatch)>=len(enMatch)): return MatchTagResponseData(jpzhMatch,isGlobal=len(jpMatch)>=len(zhMatch))
    return MatchTagResponseData(enMatch,isGlobal=True)

#入力: 画像のURI
#出力: 検出されたタグが含まれるリスト 画像によっては6個以上になってしまうこともある
def taglistFromImage(imageURI:str)->MatchTagResponseData:
    API_KEY = os.environ["CLOUDVISION_API_KEY"]
    client = vision.ImageAnnotatorClient(credentials=api_key.Credentials(API_KEY))
    visionImage = vision.Image()
    visionImage.source.image_uri = imageURI

    #メモ
    #text_detectionとdocument_text_detectionの違いがよくわからない
    #料金節約のために、ランダムでどちらかを使うという手もある
    #今は一旦前者のみを使う
    result = client.text_detection(image=visionImage).text_annotations
    print(f"{result=}")
    result = result[0].description
    
    print("OCR result:" + result)
    matches = matchTag(result)
    print(matches)
    if(matches.isIllegal()):
        print("warning:タグの数が想定と違います")
    return matches
