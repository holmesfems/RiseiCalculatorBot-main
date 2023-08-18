import yaml
import itertools

class RecruitTag:
    def __init__(self,tagName):
        self.name = tagName

    def containedIn(operator):
        pass

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

class OtherTag(RecruitTag):
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
    operatorDB = yaml.safe_load(file)["main"]
    operatorDB = [Operator(item) for item in operatorDB]

with open("./recruitment/tagList.json","rb") as file:
    tagList = yaml.safe_load(file)

eliteTags = tagList["eliteTags"]
jobTags = tagList["jobTags"]
otherTags = tagList["positionTags"]+tagList["otherTags"]

tagNameList = eliteTags + jobTags + otherTags

def createTag(tagName):
    if tagName in tagList["eliteTags"]:
        return EliteTag(tagName)
    if tagName in tagList["jobTags"]:
        return JobTag(tagName)
    if tagName in tagList["positionTags"] + tagList["otherTags"]:
        return OtherTag(tagName)
    return None

def createTagList(tagNameList):
    ret = list()
    for tagName in tagNameList:
        tagClass = createTag(tagName)
        if(tagClass != None): ret.append(tagClass)
    return ret

def createCombinations(tagClassList,number):
    return list(itertools.combinations(tagClassList,number))

def satisfyTags(operator,tagClassList):
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

def maxStar(operatorList):
    starList = [operator.stars for operator in operatorList]
    if(starList): return max(starList)
    return 0

def minStar(operatorList,least:int = 3):
    allstarList = list(dict.fromkeys([operator.stars for operator in operatorList]))
    starList = [x for x in allstarList if x>=least]
    restList = [x for x in allstarList if x not in starList]
    if(starList):
        return min(starList)
    if(restList):
        return max(restList)
    return 0

def operatorListStarsMEThan(stars):
    return [operator for operator in operatorDB if operator.stars >= stars]

def createSearchMap(tagNameList,targetOperatorList,minStarToShow,equals = False):
    tagClasses = createTagList(tagNameList)
    tagCombinations = list()
    for i in range(3):
        tagCombinations += createCombinations(tagClasses,i+1)
    searchMap = {}
    for combination in tagCombinations:
        satisfies = [operator for operator in targetOperatorList if satisfyTags(operator,combination)]
        _minStar = minStar(satisfies,3)
        if(satisfies):
            if(not equals):
                if(_minStar>=minStarToShow):
                    searchMap[combination] = satisfies
            elif(_minStar==minStarToShow):
                searchMap[combination] = [x for x in satisfies if x.stars == minStarToShow]
    return searchMap

def toStrList(list):
    return [str(x) for x in list]

def allAinBnotEq(a:tuple,b:tuple):
    if(len(a) >= len(b)):
        return False
    for item in a:
        if item not in b:
            return False
    return True

def isIndependent(key,keyList):
    for item in keyList:
        if allAinBnotEq(item,key):
            return False
    return True

def clearSearchMap(redundantMap):
    return {key:value for key,value in redundantMap if isIndependent(key,redundantMap.keys())}

def searchMapToStringChunks(searchMap):
    if(not searchMap):
        return ["条件を満たす組み合わせはありません"]
    chunks = []
    smartMap = clearSearchMap(searchMap)
    keyLenSorted = sorted(smartMap.items(),key=lambda x:len(x[0]),reverse=True)
    valueLenSorted = sorted(keyLenSorted,key=lambda x:len(x[1]))
    maxstarSorted = sorted(valueLenSorted,key=lambda x:maxStar(x[1]),reverse=True)
    minstarSorted = sorted(maxstarSorted,key=lambda x:minStar(x[1],3),reverse=True)
    for (key,value) in minstarSorted:
        valueSortedByStar = sorted(value,key=lambda x:x.stars,reverse=True)
        minStarValue = minStar(valueSortedByStar,3)
        keyStrList = toStrList(key)
        valueStrList = toStrList(valueSortedByStar)
        keyMsg = "+".join(keyStrList)
        valueMsg = ",".join(valueStrList)
        chunk = keyMsg+" -> ★{0}".format(minStarValue)+ "```"+valueMsg+"```\n"
        chunks.append(chunk)
    return chunks
            
def recruitDoProcess(inputTagList,minStar):
    inputList = list(filter(lambda x:x is not None and x in tagNameList,inputTagList))
    inputList = sorted(inputList,key=lambda x:tagNameList.index(x))
    if(minStar is None): minStar = 1
    searchMap = createSearchMap(inputList,operatorDB,minStar)
    chunks = searchMapToStringChunks(searchMap)
    return {"title":" ".join(inputList),"msgList":chunks}

starCombineListMap = {}
def compareTagKey(tag:str):
    return tagNameList.index(tag) if tag in tagNameList else -1

def compareTagTupleKey(tagTuple:tuple):
    num = len(tagTuple)
    order = len(tagNameList)
    ret = 0
    for i in range(num):
        ret += compareTagKey(tagTuple[i]) * order**(2-i)
    return order

def mapToMsgChunksHighStars(combineList):
    if(not combineList):
        return ["条件を満たす組み合わせはありません"]
    chunks = []
    smartList = clearSearchMap(combineList)
    keySorted = sorted(smartList.items(),key=lambda x:compareTagTupleKey(x[0]))
    for (key,value) in keySorted:
        keyStrList = toStrList(key)
        keyMsg = "+".join(keyStrList)
        valueStr = str(value[0])
        chunk = keyMsg + " -> " + valueStr + "\n"
        chunks.append(chunk)
    return chunks

def showHighStars(minStar:int = 4):
    global starCombineListMap
    combineList = starCombineListMap.get(minStar,None)
    if(not combineList):
        #最低の星が満たすやつを探す
        searchList = jobTags + otherTags
        allCombineList = createSearchMap(searchList,operatorDB,minStar,equals=True)
        starCombineListMap[minStar] = allCombineList
        combineList = allCombineList
    chunks = mapToMsgChunksHighStars(combineList)
    return {
        "title":"★{0}確定タグ一覧".format(minStar),
        "msgList":chunks
    }

    