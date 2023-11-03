import yaml
import itertools
from typing import List,Tuple,Optional

class RecruitTag:
    def __init__(self,tagName):
        self.name = tagName
        self.type = ...

    def containedIn(operator):...

    def __repr__(self):
        return self.name

class EliteTag(RecruitTag):
    def __init__(self,tagName):
        RecruitTag.__init__(self,tagName)
        self.type = "elite"

    def containedIn(self,operator):
        stars = operator.stars
        if(stars == 5 and self.name == "エリート"):
            return True
        if(stars == 6 and self.name == "上級エリート"):
            return True
        return False
    
class JobTag(RecruitTag):
    def __init__(self,tagName):
        RecruitTag.__init__(self,tagName)
        self.type = "job"
    
    def containedIn(self,operator):
        if(operator.job == self.name):
            return True
        return False

class PositionAndOtherTag(RecruitTag):
    def __init__(self,tagName):
        RecruitTag.__init__(self,tagName)
        self.type = "other"
    
    def containedIn(self,operator):
        if(self.name in operator.tags):
            return True
        return False

class Operator:
    def __init__(self,operatorJson):
        self.name = operatorJson["name"]
        self.job = operatorJson["job"]
        self.tags = operatorJson["tags"]
        self.stars = int(operatorJson["stars"])

    def __repr__(self):
        return "★{0}".format(self.stars)+self.name

with open("./recruitment/recruitmentOperators.json","rb") as file:
    operatorDB = yaml.safe_load(file)
    operators_JP = [Operator(item) for item in operatorDB["main"]]
    operators_New = [Operator(item) for item in operatorDB["new"]]

def get_operators(glob:bool) -> List[Operator]:
    return operators_JP if glob else operators_JP + operators_New

with open("./recruitment/tagList.json","rb") as file:
    tagList = yaml.safe_load(file)

jobTags = tagList["jobTags"]
positionTags = tagList["positionTags"]
eliteTags = tagList["eliteTags"]
otherTags = tagList["otherTags"]

tagNameList:List[str] =  jobTags + positionTags + eliteTags + otherTags

def createTag(tagName):
    if tagName in tagList["eliteTags"]:
        return EliteTag(tagName)
    if tagName in tagList["jobTags"]:
        return JobTag(tagName)
    if tagName in tagList["positionTags"] + tagList["otherTags"]:
        return PositionAndOtherTag(tagName)
    return None

def createTagList(tagNameList):
    ret = list()
    for tagName in tagNameList:
        tagClass = createTag(tagName)
        if(tagClass is not None): ret.append(tagClass)
    return ret

def createCombinations(tagClassList:List[RecruitTag],number:int):
    return list(itertools.combinations(tagClassList,number))

def satisfyTags(operator,tagClassList:List[RecruitTag]):
    #星6は上級エリート必須
    needElite = (int(operator.stars) == 6)
    hasElite = False
    for tag in tagClassList:
        if(not tag.containedIn(operator)):
            return False
        if tag.type == "elite":
            hasElite = True
    if needElite and not hasElite:
        return False
    return True

def maxStar(operatorList:List[Operator]):
    starList = [operator.stars for operator in operatorList]
    if(starList): return max(starList)
    return 0

#オペレーターリストの一番低い星を返す
#一番高い星が3以下であれば、一番高い星を返す
def minStar(operatorList:List[Operator]):
    least = 3
    allstarSet = set([operator.stars for operator in operatorList])
    starList = [x for x in allstarSet if x>=least]
    restList = [x for x in allstarSet if x not in starList]
    if(starList):
        return min(starList)
    if(restList):
        return max(restList)
    return 0

def isIndependent(key,keyList):
    return all(not allAinBnotEq(item,key) for item in keyList)

def clearSearchMap(redundantMap:dict):
    return {key:value for (key,value) in redundantMap.items() if isIndependent(key,redundantMap.keys())}

#星〇確定タグの組み合わせリストを出力する
#equals: ジャスト星〇確定なのか
#clearRedundant: 冗長タグを消すか(例： 先鋒+治療→星4なので、先鋒+治療+cost回復は要らないよね)
#showRobot: ロボットタグがあるときのみ、星1オペレーターを表示する
def createSearchMap(tagNameList:List[str],targetOperatorList:List[Operator],minStarToShow:int,equals = False,clearRedundant = False,showRobot = False):
    tagClasses = createTagList(tagNameList)
    tagCombinations:List[Tuple[RecruitTag]] = list()
    for i in range(3):
        tagCombinations += createCombinations(tagClasses,i+1)
    searchMap = {}
    for combination in tagCombinations:
        satisfies = [operator for operator in targetOperatorList if satisfyTags(operator,combination)]
        _minStar = minStar(satisfies)
        if(satisfies):
            if(not equals):
                if(_minStar>=minStarToShow):
                    searchMap[combination] = satisfies
                elif(showRobot and "ロボット" in [tag.name for tag in combination] and 1 in (operator.stars for operator in satisfies)):
                    searchMap[combination] = satisfies
            elif(_minStar==minStarToShow):
                searchMap[combination] = [x for x in satisfies if x.stars == minStarToShow]
    if(clearRedundant):
        return clearSearchMap(searchMap)
    else:
        return searchMap

def toStrList(list):
    return [str(x) for x in list]

def allAinBnotEq(a:tuple,b:tuple):
    if(len(a) >= len(b)):
        return False
    return all(item in b for item in a)

def searchMapToStringChunks(searchMap):
    if(not searchMap):
        return []
    chunks = []
    keyLenSorted = sorted(searchMap.items(),key=lambda x:len(x[0]),reverse=True)
    valueLenSorted = sorted(keyLenSorted,key=lambda x:len(x[1]))
    maxstarSorted = sorted(valueLenSorted,key=lambda x:maxStar(x[1]),reverse=True)
    minstarSorted = sorted(maxstarSorted,key=lambda x:minStar(x[1]),reverse=True)
    for (key,value) in minstarSorted:
        valueSortedByStar = sorted(value,key=lambda x:x.stars,reverse=True)
        minStarValue = minStar(valueSortedByStar)
        keyStrList = toStrList(key)
        valueStrList = toStrList(valueSortedByStar)
        keyMsg = "+".join(keyStrList)
        valueMsg = ",".join(valueStrList)
        chunk = keyMsg + " -> ★{0}".format(minStarValue) + "```\n" + valueMsg+"```\n"
        chunks.append(chunk)
    return chunks
            
def recruitDoProcess(inputTagList:List[str],minStar:Optional[int]=None,isGlobal:bool=True):
    inputList = set(inputTagList)
    inputList = list(filter(lambda x:x is not None and x in tagNameList,inputList))
    inputList = sorted(inputList,key=lambda x:tagNameList.index(x))
    if(minStar is None): minStar = 1
    showRobot = False
    if(minStar == 4): showRobot = True
    searchMap = createSearchMap(inputList,get_operators(glob=isGlobal),minStar,showRobot=showRobot)
    chunks = searchMapToStringChunks(searchMap)
    if(not chunks): chunks = [f"★{minStar}以上になる組み合わせはありません"]
    title = " ".join(inputList)
    if(not isGlobal): title += "(大陸版)"
    return {"title":title,"msgList":chunks}

def compareTagKey(tag:str):
    return tagNameList.index(tag) if tag in tagNameList else -1

def compareTagTupleKey(tagTuple:tuple):
    num = len(tagTuple)
    order = len(tagNameList)
    ret = 0
    for i in range(num):
        ret += compareTagKey(tagTuple[i]) * order**(2-i)
    return ret

def mapToMsgChunksHighStars(combineList:dict):
    if(not combineList):
        return []
    chunks = []
    keySorted = sorted(combineList.items(),key=lambda x:compareTagTupleKey(x[0]))
    for (key,value) in keySorted:
        keyStrList = toStrList(key)
        keyMsg = "+".join(keyStrList)
        valueStr = str(value[0])
        chunk = keyMsg + " -> " + valueStr + "\n"
        chunks.append(chunk)
    return chunks

def showHighStars(minStar:int = 4,isGlobal:bool = True):
    #最低の星が満たすやつを探す
    searchList = jobTags + otherTags
    allCombineList = createSearchMap(searchList,get_operators(glob=isGlobal),minStar,equals=True,clearRedundant=True)
    chunks = mapToMsgChunksHighStars(allCombineList)
    if(not chunks): chunks = [f"★{minStar}の確定タグはありません"]
    return {
        "title":"★{0}確定タグ一覧".format(minStar),
        "msgList":chunks
    }

    