import yaml,datetime,re
with open("happybirthday/birthdayRev.yaml","rb") as f:
    birthdayRevDict = yaml.safe_load(f)

def sortKeyScore(keystr):
    restr = r"([-+]?\d+)月([-+]?\d+)日"
    match = re.match(restr,keystr)
    month = int(match.groups()[0])
    date = int(match.groups()[1])
    score = month*31+date
    return score

sortedDict = dict(sorted(birthdayRevDict.items(),key=lambda x:sortKeyScore(x[0])))

with open("happybirthday/birthdayRev2.yaml","wb") as f:
    yaml.safe_dump(sortedDict,f,allow_unicode=True,encoding="utf-8",sort_keys=False)