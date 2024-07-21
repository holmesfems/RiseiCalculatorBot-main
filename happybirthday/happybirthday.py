import yaml,datetime
from typing import Dict,List
import sys
sys.path.append("../")
from charmaterials.charmaterials import OperatorCostsCalculator
from rcutils.rcReply import RCReply

__cnToJa = OperatorCostsCalculator.operatorInfo.cnNameToJaName

with open("happybirthday/birthdayRev.yaml","rb") as f:
    birthdayRevDict:Dict[str,List[str]] = yaml.safe_load(f)

reflectDict = {
    "アステシア": "私",
    "アステジーニ": "エレナ",
}

chanList = [
    "スズラン","ポプカル","シャマレ","バブル"
]

def reflectName(cnName:str):
    jaName = __cnToJa.get(cnName,cnName)
    reflect = reflectDict.get(jaName,None)
    if(reflect): return reflect
    chan = jaName in chanList
    if(chan): return jaName + "ちゃん"
    return jaName + "さん"

def mentionStr(reflectList):
    l = len(reflectList)
    if(l == 0): return ""
    elif(l == 1): return reflectList[0]
    else:
        return "、".join(reflectList[:-1]) + "と" + reflectList[-1]

def checkBirthday(now:datetime.datetime) -> RCReply | None:
    nowstr = "{0}月{1}日".format(now.month,now.day)
    birthoperator = birthdayRevDict.get(nowstr,[])
    if(len(birthoperator) == 0): return None
    else:
        title = ":birthday:お誕生日:birthday:おめでとう:tada:！！"
        msg = "今日は" + mentionStr([reflectName(x) for x in birthoperator]) + "の誕生日よ！みんなでお祝い:tada:しましょ！"
        return RCReply(embbedTitle=title,embbedContents=[msg])