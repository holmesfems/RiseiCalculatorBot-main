import yaml,datetime

with open("happybirthday/birthdayRev.yaml","rb") as f:
    birthdayRevDict = yaml.safe_load(f)

reflectDict = {
    "アステシア": "私",
    "アステジーニ": "エレナちゃん",
}

def reflectName(name:str):
    return reflectDict.get(name,name+"さん")

def mentionStr(reflectList):
    l = len(reflectList)
    if(l == 0): return ""
    elif(l == 1): return reflectList[0]
    else:
        return "、".join(reflectList[:-1]) + "と" + reflectList[-1]

def checkBirthday(now:datetime.datetime):
    nowstr = "{0}月{1}日".format(now.month,now.day)
    birthoperator = birthdayRevDict.get(nowstr,[])
    if(len(birthoperator) == 0): return
    else:
        title = ":birthday:お誕生日:birthday:おめでとう:tada:！！"
        msg = "今日は" + mentionStr([reflectName(x) for x in birthoperator]) + "の誕生日よ！みんなでお祝い:tada:しましょ！"
        return {"title":title,"msgList":[msg]}
