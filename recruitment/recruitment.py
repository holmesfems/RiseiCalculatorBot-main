from __future__ import annotations
import yaml
import itertools
from typing import List,Tuple,Optional,Iterable,Dict,Set
from rcutils.rcReply import RCReply
from abc import ABC,abstractmethod
from pydantic import BaseModel,Field
from datetime import datetime,date
import sys
sys.path.append('../')
from rcutils.getnow import getnow,JST
import json

class RecruitTag(BaseModel,ABC):
    name:str
    tagType:str

    @abstractmethod
    def containedIn(operator:Operator)->bool:...

    def __repr__(self):
        return self.name
    
    def __str__(self):
        return self.name

class EliteTag(RecruitTag):
    def __init__(self,tagName:str):
        super().__init__(name=tagName,tagType="elite") 

    def containedIn(self,operator:Operator):
        stars = operator.stars
        if(stars == 5 and self.name == "エリート"):
            return True
        if(stars == 6 and self.name == "上級エリート"):
            return True
        return False
    
class JobTag(RecruitTag):
    def __init__(self,tagName:str):
        super().__init__(name=tagName,tagType="job")

    def containedIn(self,operator:Operator):
        if(operator.job == self.name):
            return True
        return False

class PositionAndOtherTag(RecruitTag):
    def __init__(self,tagName:str):
        super().__init__(name=tagName,tagType="other")
    
    def containedIn(self,operator:Operator):
        if(self.name in operator.tags):
            return True
        return False

class Operator(BaseModel):
    name:str
    job:str
    tags:List[str] = Field(default=[])
    stars:int
    beginFrom:float|None = None

    def __str__(self):
        return "★{0}".format(self.stars)+self.name

#近い将来実装予定のオペレーター
class FutureList(BaseModel):
    yyyymmdd: str
    opList: List[Operator] = Field(default=[])

#オペレーターデータ形式
class OperatorDB(BaseModel):
    main: List[Operator] = Field(default=[])
    new: List[Operator] = Field(default=[])
    future: List[FutureList] = Field(default=[])

def _parseDate(key:str) -> datetime:
    year = int(key[:4])
    month = int(key[4:6])
    day = int(key[6:8])
    return datetime(year,month,day,hour=16,tzinfo=JST)

with open("./recruitment/recruitmentOperators.json","rb") as file:
    operatorDB = yaml.safe_load(file)
    operatorDB = OperatorDB.model_validate(operatorDB)
    operators_JP = operatorDB.main
    operators_New = operatorDB.new
    operators_Future:list[Operator] = []
    futureList = operatorDB.future
    for futureItem in futureList:
        beginTime = _parseDate(futureItem.yyyymmdd).timestamp()
        for operator in futureItem.opList:
            operator.beginFrom = beginTime
            operators_Future.append(operator)

with open("./recruitment/tagList.json","rb") as file:
    tagList = yaml.safe_load(file)

jobTags:List[str] = tagList["jobTags"]
positionTags:List[str]  = tagList["positionTags"]
eliteTags:List[str]  = tagList["eliteTags"]
otherTags:List[str]  = tagList["otherTags"]

tagNameList:List[str] =  jobTags + positionTags + eliteTags + otherTags

def createTag(tagName):
    if tagName in tagList["eliteTags"]:
        return EliteTag(tagName)
    if tagName in tagList["jobTags"]:
        return JobTag(tagName)
    if tagName in tagList["positionTags"] + tagList["otherTags"]:
        return PositionAndOtherTag(tagName)
    return None

recruitTagDict = {name:createTag(name) for name in tagNameList}

def createTagList(nameList:List[str]):
    return [recruitTagDict[tagName] for tagName in nameList]

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

class OperatorList(BaseModel):
    operators:List[Operator] = Field(default=[])
    minStar:int = 0
    starSet:Set[int] = Field(default=set())
    nameList:List[str] = Field(default=[])
    def __init__(self,operators:List[Operator]):
        sortedByStar = sorted(operators,key=lambda x:x.stars,reverse=False)
        super().__init__(operators = sortedByStar)
        if(sortedByStar):
            self.minStar = minStar(sortedByStar)
            self.starSet = set(item.stars for item in sortedByStar)
            self.nameList = [item.name for item in sortedByStar]
    def showNameWithStar(self):
        return ",".join(toStrList(self.operators))
    def showName(self):
        return ", ".join([op.name for op in self.operators])
    def __add__(self,other:OperatorList):
        if(self.isEmpty()): return other
        if(other.isEmpty()): return self
        return OperatorList(operators=self.operators+other.operators)
    def getAvailableList(self,nowTimeStamp:float) ->OperatorList:
        return OperatorList([operator for operator in self.operators if operator.beginFrom == None or nowTimeStamp >= operator.beginFrom])
    def isEmpty(self):
        return len(self.operators)==0
    def filterByStar(self,star:int) -> OperatorList:
        return OperatorList([operator for operator in self.operators if operator.stars==star])
    def contains(self,name:str):
        return name in self.nameList

class TagToOperatorMap:
    def __init__(self,data:Dict[Tuple[str],OperatorList]):
        self.data = data

    def getOrEmpty(self,key:Tuple[str]):
        return self.data.get(key,OperatorList([]))

def satisfyTags(operator:Operator,tagClassList:Tuple[RecruitTag]):
    #星6は上級エリート必須
    needElite = (int(operator.stars) == 6)
    hasElite = False
    for tag in tagClassList:
        if(not tag.containedIn(operator)):
            return False
        if tag.tagType == "elite":
            hasElite = True
    if needElite and not hasElite:
        return False
    return True

def createTagMap(operators:List[Operator]):
    tagClasses = recruitTagDict.values()
    tagCombinations:List[Tuple[RecruitTag]] = list()
    for i in range(3):
        tagCombinations += createCombinations(tagClasses,i+1)
    searchMap:Dict[Tuple[str],OperatorList] = {}
    for combination in tagCombinations:
        satisfies = [operator for operator in operators if satisfyTags(operator,combination)]
        if(satisfies):
            tagNameCombine = tuple(item.name for item in combination)
            searchMap[tagNameCombine] = OperatorList(operators=satisfies)
    return TagToOperatorMap(searchMap)

def createCombinations(tagClassList:List[RecruitTag],number:int):
    return [tuple(x) for x in itertools.combinations(tagClassList,number)]

def createTagStrCombinations(tagStrList:Iterable[str]):
    ret:List[Tuple[str]] = []
    for i in range(3):
        ret += list(tuple(x) for x in itertools.combinations(tagStrList,i+1))
    return ret

GlobalTagMap = createTagMap(operators_JP)
MainlandTagMap = createTagMap(operators_New)
FutureTagMap  = createTagMap(operators_Future)

def isIndependent(key:tuple,keyList:List[tuple]):
    return all(not allAinBnotEq(item,key) for item in keyList)

def toStrList(list):
    return [str(x) for x in list]

def allAinBnotEq(a:tuple,b:tuple):
    if(len(a) >= len(b)):
        return False
    return all(item in b for item in a)

class TagMatchItem(BaseModel):
    combine:List[RecruitTag]
    operatorList:OperatorList
    containsPickup:bool=Field(default=False)
    pickupTarget:List[str]=Field(default=[])

class TagMatchResult(BaseModel):
    result:List[TagMatchItem]
    def isEmpty(self):
        return len(self.result) == 0
    def keys(self):
        return [x.combine for x in self.result]

#星〇確定タグの組み合わせリストを出力する
#equals: ジャスト星〇確定なのか
#showRobot: ロボット確定タグでオペレーターを表示する

def calculateTagMatchResult(tagList:Iterable[str],isGlobal:bool,minStar:int,equals = False,showRobot = False,pickupOperators:Optional[Iterable[str]]=None):
    tagClasses = createTagList(tagList)
    tagCombinations:List[Tuple[RecruitTag]] = []
    for i in range(3):
        tagCombinations += createCombinations(tagClasses,i+1)
    result: List[TagMatchItem]  = []
    nowTime = getnow().timestamp()
    for combine in tagCombinations:
        tagNameCombine = tuple((item.name for item in combine))
        operators = GlobalTagMap.getOrEmpty(tagNameCombine)
        if(not isGlobal): operators = operators + MainlandTagMap.getOrEmpty(tagNameCombine)
        future = FutureTagMap.getOrEmpty(tagNameCombine)
        if(not future.isEmpty()):
            if(isGlobal):
                operators = operators + future.getAvailableList(nowTime)
            else:
                operators = operators + future
        if(not operators.isEmpty()):
            if(not equals):
                if(pickupOperators!=None and len(puList:=[target for target in pickupOperators if operators.contains(target)])>0):
                    result.append(TagMatchItem(combine=combine,operatorList=operators,containsPickup=True,pickupTarget=puList))
                elif(operators.minStar == 1 and showRobot):
                    result.append(TagMatchItem(combine=combine,operatorList=operators))
                elif(operators.minStar >= minStar):
                    result.append(TagMatchItem(combine=combine,operatorList=operators))
            else:
                if(operators.minStar == minStar):
                    result.append(TagMatchItem(combine=combine,operatorList=operators.filterByStar(minStar)))
    return TagMatchResult(result=result)

def searchMapToStringChunks(tagMatchResult:TagMatchResult):
    if(tagMatchResult.isEmpty()):
        return ([],[])
    chunks = []
    toAIChunks = []
    keyLenSorted = sorted(tagMatchResult.result,key=lambda x:len(x.combine),reverse=True)
    valueLenSorted = sorted(keyLenSorted,key=lambda x:len(x.operatorList.operators))
    maxstarSorted = sorted(valueLenSorted,key=lambda x:max(x.operatorList.starSet),reverse=True)
    minstarSorted = sorted(maxstarSorted,key=lambda x:x.operatorList.minStar,reverse=True)
    hasContainsSorted = sorted(minstarSorted,key=lambda x:x.containsPickup,reverse=True)
    
    for matchItem in hasContainsSorted:
        keyStrList = toStrList(matchItem.combine)
        keyMsg = "+".join(keyStrList)
        valueMsg = matchItem.operatorList.showNameWithStar()
        chunk = keyMsg + " -> ★{0}".format(matchItem.operatorList.minStar) + "```\n" + valueMsg+"```\n"
        chunks.append(chunk)
        aiChunk = keyMsg + " ->★" + ",".join(["{0}".format(star) for star in matchItem.operatorList.starSet])
        if(matchItem.operatorList.minStar >= 5 or matchItem.operatorList.minStar == 1):
            aiChunk += f"\n{matchItem.operatorList.showName()}"
        elif(matchItem.containsPickup):
            puOperators = [item for item in matchItem.operatorList.operators if item.name in matchItem.pickupTarget]
            puStars = [item.stars for item in puOperators]
            otherTarget = [item.name for item in matchItem.operatorList.operators if item.stars in puStars and item.name not in matchItem.pickupTarget]
            aiChunk += f"\n{','.join(matchItem.pickupTarget+otherTarget)}"
        aiChunk += "\n"
        toAIChunks.append(aiChunk)
    return (chunks,toAIChunks)
            
def recruitDoProcess(inputTagList:Iterable[str],minStar:Optional[int]=None,isGlobal:bool=True,showTagLoss=False,pickupOperators:Optional[Iterable[str]]=None) -> RCReply:
    #OpenAIから呼び出す予定なし
    inputList = set(inputTagList)
    inputList = list(filter(lambda x:x is not None and x in tagNameList,inputList))
    inputList = sorted(inputList,key=lambda x:tagNameList.index(x))
    if(minStar is None): minStar = 1
    showRobot = False
    if(minStar == 4): showRobot = True
    tagMatchResult = calculateTagMatchResult(inputList,isGlobal,minStar,showRobot=showRobot,pickupOperators=pickupOperators)
    title = " ".join(inputList)
    if(not isGlobal): title += " (大陸版)"
    if(showTagLoss and len(inputList)<5): title+="(タグ不足)"
    if(showTagLoss and len(inputList)>5): title+="(タグ過多)"
    if(tagMatchResult.isEmpty()): 
        chunks = [f"★{minStar}以上になる組み合わせはありません"]
        return RCReply(embbedTitle=title,embbedContents=chunks,responseForAI=chunks[0])
    (chunks,aiChunks) = searchMapToStringChunks(tagMatchResult)
    return RCReply(embbedTitle=title,embbedContents=chunks,responseForAI="".join(aiChunks))

def compareTagKey(tag:str):
    return tagNameList.index(tag) if tag in tagNameList else -1

def compareTagTupleKey(tagTuple:Tuple):
    num = len(tagTuple)
    order = len(tagNameList)
    ret = 0
    for i in range(num):
        ret += compareTagKey(tagTuple[i]) * order**(2-i)
    return ret

def mapToMsgChunksHighStars(combineList:TagMatchResult):
    if(combineList.isEmpty()):
        return []
    chunks = []
    keySorted = sorted(combineList.result,key=lambda x:compareTagTupleKey(x.combine))
    for matchItem in keySorted:
        key,value = (matchItem.combine,matchItem.operatorList)
        keyStrList = toStrList(key)
        keyMsg = "+".join(keyStrList)
        valueStr = str(value.operators[0])
        chunk = keyMsg + " -> " + valueStr + "\n"
        chunks.append(chunk)
    return chunks

def clearSearchMap(matchResult:TagMatchResult):
    keys = matchResult.keys()
    return TagMatchResult(result=[item for item in matchResult.result if isIndependent(item.combine,keys)])

def showHighStars(minStar:int = 4,isGlobal:bool = True) -> RCReply:
    #最低の星が満たすやつを探す
    searchList = positionTags + jobTags + otherTags
    allCombineList = calculateTagMatchResult(searchList,isGlobal=isGlobal,minStar=minStar,showRobot=False,equals=True)
    clearedSearchMap = clearSearchMap(matchResult=allCombineList)
    chunks = mapToMsgChunksHighStars(clearedSearchMap)
    listForAI = [
        {
            "tags": str(matchItem.combine),
            "operators": matchItem.operatorList.showName()
        } for matchItem in allCombineList.result
    ]
    if(not chunks): chunks = [f"★{minStar}の確定タグはありません"]
    return RCReply(
        embbedTitle="★{0}確定タグ一覧".format(minStar),
        embbedContents=chunks,
        responseForAI=json.dumps(listForAI,ensure_ascii=False)
    )

    