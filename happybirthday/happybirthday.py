import yaml,datetime
from rcutils.rcReply import RCReply

with open("happybirthday/birthdayRev.yaml","rb") as f:
    birthdayRevDict = yaml.safe_load(f)

reflectDict = {
    "アステシア": "私",
    "アステジーニ": "エレナちゃん",
}

chanList = [
    "スズラン","ポプカル","シャマレ","バブル"
]

def reflectName(name:str):
    reflect = reflectDict.get(name,None)
    if(reflect): return reflect
    chan = name in chanList
    if(chan): return name + "ちゃん"
    return name + "さん"

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