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

class RecruitTag(ABC):
    def __init__(self,tagName:str):
        self.name = tagName
    
    @property
    @abstractmethod
    def type(self)->str:...

    @abstractmethod
    def containedIn(operator:Operator)->bool:...

    def __repr__(self):
        return self.name
    
    def __str__(self):
        return self.name

class EliteTag(RecruitTag):
    def __init__(self,tagName:str):
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
    def __init__(self,tagName:str):
        RecruitTag.__init__(self,tagName)
    
    @property
    def type(self): return "job"

    def containedIn(self,operator:Operator):
        if(operator.job == self.name):
            return True
        return False

class PositionAndOtherTag(RecruitTag):
    def __init__(self,tagName:str):
        RecruitTag.__init__(self,tagName)
    
    @property
    def type(self): return "other"
    
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
    def __init__(self,operators:List[Operator]):
        sortedByStar = sorted(operators,key=lambda x:x.stars,reverse=False)
        super().__init__(operators = sortedByStar)
        if(sortedByStar):
            self.minStar = minStar(sortedByStar)
            self.starSet = set(item.stars for item in sortedByStar)
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
        if tag.type == "elite":
            hasElite = True
    if needElite and not hasElite:
        return False
    return True

def createTagMap(tagList:List[str],operators:List[Operator]):
    tagClasses = recruitTagDict.values()
    tagCombinations:List[Tuple[RecruitTag]] = list()
    for i in range(3):
        tagCombinations += createCombinations(tagClasses,i+1)
    searchMap:Dict[Tuple[str],OperatorList] = {}
    for combination in tagCombinations:
        satisfies = [operator for operator in operators if satisfyTags(operator,combination)]
        if(satisfies):
            searchMap[combination] = OperatorList(operators=satisfies)
    return TagToOperatorMap(searchMap)

def createCombinations(tagClassList:List[RecruitTag],number:int):
    return [tuple(x) for x in itertools.combinations(tagClassList,number)]

def createTagStrCombinations(tagStrList:Iterable[str]):
    ret:List[Tuple[str]] = []
    for i in range(3):
        ret += list(tuple(x) for x in itertools.combinations(tagStrList,i+1))
    return ret

GlobalTagMap = createTagMap(tagNameList,operators_JP)
MainlandTagMap = createTagMap(tagNameList,operators_New)
FutureTagMap  = createTagMap(tagNameList,operators_Future)

def isIndependent(key:tuple,keyList:List[tuple]):
    return all(not allAinBnotEq(item,key) for item in keyList)



def toStrList(list):
    return [str(x) for x in list]

def allAinBnotEq(a:tuple,b:tuple):
    if(len(a) >= len(b)):
        return False
    return all(item in b for item in a)

class TagMatchResult:
    def __init__(self, result:List[Tuple[Tuple[RecruitTag],OperatorList]]):
        self.result = result
    def isEmpty(self):
        return len(self.result) == 0
    def keys(self):
        return [x[0] for x in self.result]

#星〇確定タグの組み合わせリストを出力する
#equals: ジャスト星〇確定なのか
#showRobot: ロボット確定タグでオペレーターを表示する

def calculateTagMatchResult(tagList:Iterable[str],isGlobal:bool,minStar:int,equals = False,showRobot = False):
    tagClasses = createTagList(tagList)
    tagCombinations:List[Tuple[RecruitTag]] = []
    for i in range(3):
        tagCombinations += createCombinations(tagClasses,i+1)
    result: List[Tuple[Tuple[RecruitTag],OperatorList]]  = []
    nowTime = getnow().timestamp()
    for combine in tagCombinations:
        operators = GlobalTagMap.getOrEmpty(combine)
        if(not isGlobal): operators = operators + MainlandTagMap.getOrEmpty(combine)
        future = FutureTagMap.getOrEmpty(combine)
        if(not future.isEmpty()):
            if(isGlobal):
                operators = operators + future.getAvailableList(nowTime)
            else:
                operators = operators + future
        if(not operators.isEmpty()):
            if(not equals):
                if(operators.minStar == 1 and showRobot):
                    result.append((combine,operators))
                elif(operators.minStar >= minStar):
                    result.append((combine,operators))
            else:
                if(operators.minStar == minStar):
                    result.append((combine,operators.filterByStar(minStar)))
    return TagMatchResult(result=result)

def searchMapToStringChunks(tagMatchResult:TagMatchResult):
    if(tagMatchResult.isEmpty()):
        return ([],[])
    chunks = []
    toAIChunks = []
    keyLenSorted = sorted(tagMatchResult.result,key=lambda x:len(x[0]),reverse=True)
    valueLenSorted = sorted(keyLenSorted,key=lambda x:len(x[1].operators))
    maxstarSorted = sorted(valueLenSorted,key=lambda x:max(x[1].starSet),reverse=True)
    minstarSorted = sorted(maxstarSorted,key=lambda x:x[1].minStar,reverse=True)
    for (key,value) in minstarSorted:
        keyStrList = toStrList(key)
        keyMsg = "+".join(keyStrList)
        valueMsg = value.showNameWithStar()
        chunk = keyMsg + " -> ★{0}".format(value.minStar) + "```\n" + valueMsg+"```\n"
        chunks.append(chunk)
        aiChunk = keyMsg + " -> " + ", ".join(["★{0}".format(star) for star in value.starSet])
        if(value.minStar >= 5 or value.minStar == 1):
            aiChunk += f"\n{value.showName()}"
        aiChunk += "\n"
        toAIChunks.append(aiChunk)
    return (chunks,toAIChunks)
            
def recruitDoProcess(inputTagList:Iterable[str],minStar:Optional[int]=None,isGlobal:bool=True) -> RCReply:
    #OpenAIから呼び出す予定なし
    inputList = set(inputTagList)
    inputList = list(filter(lambda x:x is not None and x in tagNameList,inputList))
    inputList = sorted(inputList,key=lambda x:tagNameList.index(x))
    if(minStar is None): minStar = 1
    showRobot = False
    if(minStar == 4): showRobot = True
    tagMatchResult = calculateTagMatchResult(inputList,isGlobal,minStar,showRobot=showRobot)
    title = " ".join(inputList)
    if(not isGlobal): title += " (大陸版)"
    if(tagMatchResult.isEmpty()): 
        chunks = [f"★{minStar}以上になる組み合わせはありません"]
        return RCReply(embbedTitle=title,embbedContents=chunks,responseForAI=chunks[0])
    (chunks,aiChunks) = searchMapToStringChunks(tagMatchResult)
    title = " ".join(inputList)
    if(not isGlobal): title += " (大陸版)"
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
    keySorted = sorted(combineList.result,key=lambda x:compareTagTupleKey(x[0]))
    for (key,value) in keySorted:
        keyStrList = toStrList(key)
        keyMsg = "+".join(keyStrList)
        valueStr = str(value.operators[0])
        chunk = keyMsg + " -> " + valueStr + "\n"
        chunks.append(chunk)
    return chunks

def clearSearchMap(matchResult:TagMatchResult):
    keys = matchResult.keys()
    return TagMatchResult([(key,value) for (key,value) in matchResult.result if isIndependent(key,keys)])

def showHighStars(minStar:int = 4,isGlobal:bool = True) -> RCReply:
    #最低の星が満たすやつを探す
    searchList = positionTags + jobTags + otherTags
    allCombineList = calculateTagMatchResult(searchList,isGlobal=isGlobal,minStar=minStar,showRobot=False,equals=True)
    clearedSearchMap = clearSearchMap(matchResult=allCombineList)
    chunks = mapToMsgChunksHighStars(clearedSearchMap)
    listForAI = [
        {
            "tags": str(key),
            "operators": value.showName()
        } for key,value in allCombineList.result
    ]
    if(not chunks): chunks = [f"★{minStar}の確定タグはありません"]
    return RCReply(
        embbedTitle="★{0}確定タグ一覧".format(minStar),
        embbedContents=chunks,
        responseForAI=json.dumps(listForAI,ensure_ascii=False)
    )

    