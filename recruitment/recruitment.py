from __future__ import annotations
import yaml
import itertools
from typing import List,Tuple,Optional,Iterable
from rcutils.rcReply import RCReply
from abc import ABC,abstractmethod
import dataclasses
from datetime import datetime,date
import sys
sys.path.append('../')
from rcutils.getnow import getnow

class RecruitTag(ABC):
    def __init__(self,tagName):
        self.name = tagName
    
    @property
    @abstractmethod
    def type(self)->str:...

    @abstractmethod
    def containedIn(operator:Operator)->bool:...

    def __repr__(self):
        return self.name

class EliteTag(RecruitTag):
    def __init__(self,tagName):
        RecruitTag.__init__(self,tagName) 
    
    @property
    def type(self): return "elite"

    def containedIn(self,operator:Operator):
        stars = operator.stars
        if(stars == 5 and self.name == "エリート"):
            return True
        if(stars == 6 and self.name == "上級エリート"):
            return True
        return False
    
class JobTag(RecruitTag):
    def __init__(self,tagName):
        RecruitTag.__init__(self,tagName)
    
    @property
    def type(self): return "job"

    def containedIn(self,operator:Operator):
        if(operator.job == self.name):
            return True
        return False

class PositionAndOtherTag(RecruitTag):
    def __init__(self,tagName):
        RecruitTag.__init__(self,tagName)
    
    @property
    def type(self): return "other"
    
    def containedIn(self,operator:Operator):
        if(self.name in operator.tags):
            return True
        return False

@dataclasses.dataclass
class Operator:
    name:str
    job:str
    tags:List[str]
    stars:int

    def __repr__(self):
        return "★{0}".format(self.stars)+self.name

#近い将来実装予定のオペレーターを、先に書き込めるようにするためのコード
#"main","new"タグの他、"2024-08-08"などで、実装時間を指定できるようにする
@dataclasses.dataclass
class FutureOperatorSet:
    operators:List[Operator]
    beginTime:date
    
def _parseDate(key:str) -> date:
    year = int(key[:4])
    month = int(key[4:6])
    day = int(key[6:8])
    return date(year,month,day)

with open("./recruitment/recruitmentOperators.json","rb") as file:
    operatorDB = yaml.safe_load(file)
    operators_JP = [Operator(**item) for item in operatorDB["main"]]
    operators_New = [Operator(**item) for item in operatorDB["new"]]
    operators_Future = [FutureOperatorSet([Operator(**item) for item in operatorDB["future"][key]], _parseDate(key)) for key in operatorDB["future"]]

def get_operators(glob:bool) -> List[Operator]:
    ret = operators_JP.copy()
    if(glob):
        now = getnow()
        nowDate = now.date()
        nowTime = now.time()
        for operatorSet in operators_Future:
            if(nowDate > operatorSet.beginTime):
                ret += operatorSet.operators
            elif(nowDate == operatorSet.beginTime):
                #16時から実装する
                if(nowTime.hour >= 16):
                    ret += operatorSet.operators
    else:
        for operatorSet in operators_Future:
            ret += operatorSet.operators
        ret += operators_New
    return ret

with open("./recruitment/tagList.json","rb") as file:
    tagList = yaml.safe_load(file)

jobTags = tagList["jobTags"]
positionTags = tagList["positionTags"]
eliteTags = tagList["eliteTags"]
otherTags = tagList["otherTags"]

tagNameList:List[str] =  jobTags + positionTags + eliteTags + otherTags

MAX_TAGCOUNT = 5

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

def satisfyTags(operator:Operator,tagClassList:List[RecruitTag]):
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

def isIndependent(key:tuple,keyList:List[tuple]):
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
    robotTags = ["ロボット", "元素"]
    def containsRobotTag(nameList:List[str])->bool:
        return any([tag in nameList for tag in robotTags])
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
                elif(showRobot and containsRobotTag([tag.name for tag in combination]) and 1 in (operator.stars for operator in satisfies)):
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
            
def recruitDoProcess(inputTagList:Iterable[str],minStar:Optional[int]=None,isGlobal:bool=True) -> RCReply:
    #OpenAIから呼び出す予定なし
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
    return RCReply(embbedTitle=title,embbedContents=chunks)

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

def showHighStars(minStar:int = 4,isGlobal:bool = True) -> RCReply:
    #最低の星が満たすやつを探す
    searchList = positionTags + jobTags + otherTags
    allCombineList = createSearchMap(searchList,get_operators(glob=isGlobal),minStar,equals=True,clearRedundant=True)
    chunks = mapToMsgChunksHighStars(allCombineList)
    if(not chunks): chunks = [f"★{minStar}の確定タグはありません"]
    return RCReply(
        embbedTitle="★{0}確定タグ一覧".format(minStar),
        embbedContents=chunks
    )

    