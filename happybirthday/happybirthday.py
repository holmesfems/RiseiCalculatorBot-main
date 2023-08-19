import yaml,datetime

with open("happybirthday/birthdayRev.yaml","rb") as f:
    birthdayRevDict = yaml.safe_load(f)

def checkBirthday(now:datetime.datetime):
    nowstr = "{0}月{1}日".format(now.month,now.day)
    birthoperator = birthdayRevDict.get(nowstr,[])
    if(len(birthoperator) == 0): return
    else:
        title = ":birthday:お誕生日:birthday:おめでとう:tada:！！"
        msg = "今日は" + "、".join([(x+"さん") if x!="アステシア" else "私" for x in birthoperator])+"の誕生日です！みんなでお祝い:tada:しましょ！"
        return {"title":title,"msgList":[msg]}
