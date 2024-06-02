from __future__ import annotations
import numpy as np
import numpy.linalg as LA
import sys
sys.path.append('../')
from infoFromOuterSource.idtoname import ItemIdToName,ZoneIdToName
from infoFromOuterSource.formulation import Formula
from rcutils import netutil,getnow,hasduplicates,itemArray
from rcutils.rcReply import RCReply,RCMsgType
import pandas as pd
import datetime
import random
import unicodedata
import yaml
from typing import Dict,List,Optional,Tuple
from enum import StrEnum
import enum
from riseicalculator2.listInfo import *
from dataclasses import dataclass

PENGUIN_URL = 'https://penguin-stats.io/PenguinStats/api/v2/'
EPSILON = 1e-6
DEFAULT_SHOW_MIN_TIMES = 1000
DEFAULT_CACHE_TIME = 120 #minutes
EXCEL_FILENAME = 'BaseStages.xlsx'
BASEMINTIMES_UPPER = 3000 #baseMinTimes上限値

headers = {'User-Agent':'ArkPlanner'}
def get_json(s,AdditionalReq={}):
    return netutil.get_json(PENGUIN_URL+s,AdditionalReq,headers)

#初級&上級資格証
with open('riseicalculator2/price.yaml', 'rb') as f:
    Price:Dict[str,float] = yaml.safe_load(f)

#特別引換証
with open('riseicalculator2/price_special.yaml', 'rb') as f:
    Price_Special:Dict[str,float] = yaml.safe_load(f)


#大陸版実装済み、グロ版未実装のステージまとめ 実装次第削除してOK
new_zone:List[str] = [
    # 'main_13', #13章
    # 'permanent_sidestory_14_zone1', #LE
    # 'permanent_sidestory_15_zone1', #DV
    # 'permanent_sub_5_zone1', #CW
    
]

def valueTargetZHToJA(zhStr:str) -> str:
    return ItemIdToName.zhToJa(zhStr)

def getDataFrameColumnsName(glob:bool) -> List[str]:
    return [valueTargetZHToJA(x) for x in getValueTarget(glob)] + ['理性消費']

def valueTargetIndexOf(zhStr:str,glob:bool) -> int:
    try:
        return getValueTarget(glob).index(zhStr)
    except ValueError:
        return -1

def idInValueTarget(id:str,glob:bool) -> bool:
    valueTarget = getValueTarget(glob)
    zhStr = ItemIdToName.getZH(id)
    return zhStr in valueTarget

def categoryZHToJA(zhStr:str,glob:bool) -> str:
    categoryDict = getStageCategoryDict(glob)
    return categoryDict[zhStr]["to_ja"]

class CalculateMode(StrEnum):
    SANITY = enum.auto()
    TIME = enum.auto()
    def __str__(self) -> str:
        if self is CalculateMode.SANITY:
            return "理性"
        else:
            return "時間"

@dataclass
class DropItem:
    dropRate:float
    times:int

class DropList:
    ##SampleJson: {"stageId":"act18d0_08_perm","itemId":"30073","times":19118,"quantity":308,"stdDev":0.1259,"start":1620244800000,"end":null},
    def __init__(self,dropItem=None):
        self.dropDict:Dict[str,DropItem] = {}
        self.__maxtimes = 0
        self.__mintimes = 0
        if not dropItem: return #valueが空の場合、空ドロップを返す
        #アイテムがターゲットなのかは外部でチェック
        self.dropDict[dropItem["itemId"]] = DropItem(dropItem["quantity"] / dropItem["times"],dropItem["times"])
        self.__maxtimes = dropItem["times"]
        self.__mintimes = dropItem["times"]
    
    def __iadd__(self,other:DropList):
        #ドロップアイテムの加算
        for key,value in other.dropDict.items():
            #重複要素は新しいものを適用する
            self.dropDict[key] = value
        #最大試行数
        if other.__maxtimes > self.__maxtimes:
            self.__maxtimes = other.__maxtimes
        #最少試行数
        if other.__mintimes < self.__mintimes:
            self.__mintimes = other.__mintimes
        return self
    
    def __repr__(self) -> str:
        return str(self.dropDict)
    
    #龍門幣ドロップはここに含まれないので、外部で別途足す
    def toDropArray(self, isGlobal:bool) -> np.ndarray:
        dropRateArray = np.zeros(len(getValueTarget(isGlobal)))
        for index,item in enumerate(getValueTarget(isGlobal)):
            id = ItemIdToName.zhToId(item)
            dropRate = self.dropDict.get(id,DropItem(0,0)).dropRate
            dropRateArray[index] = dropRate
        return dropRateArray

    def toTimesArray(self,isGlobal:bool) -> np.ndarray:
        timesArray = np.zeros(len(getValueTarget(isGlobal)))
        for index,item in enumerate(getValueTarget(isGlobal)):
            id = ItemIdToName.zhToId(item)
            times = self.dropDict.get(id,DropItem(0,2)).times
            timesArray[index] = times
        return timesArray
    
    def toStdDevArray(self,isGlobal:bool) -> np.ndarray:
        dropArray = self.toDropArray(isGlobal)
        extra = dropArray%1.0
        timesArray = self.toTimesArray(isGlobal)-1
        return (extra*(1.0-extra)/timesArray)**0.5
    
    def getDropItem(self, zhStr:str) -> DropItem:
        return self.dropDict.get(zhStr,DropItem(0,0))
    
    def maxTimes(self):
        return self.__maxtimes
    def minTimes(self):
        return self.__mintimes
    
class RiseiOrTimeValues:
    with open("riseicalculator2/constValues.yaml","rb") as f:
        __constValueDict:Dict[str,float] = yaml.safe_load(f)

    def __init__(self,valueArray:np.ndarray,isGlobal:bool,mode:CalculateMode):
        self.isGlobal = isGlobal
        self.valueArray = valueArray
        self.mode = mode
        self.devArray = np.zeros(len(valueArray))

    def __repr__(self) -> str:
        nameDict = self.toNameValueDict()
        devDict = self.toNameStdDevDict()
        valueTarget = getValueTarget(self.isGlobal)
        jaValueTarget = [valueTargetZHToJA(x) for x in valueTarget]
        return "\n".join([x+" : "+"{0:.3f} ± {1:.4f}".format(nameDict[x],devDict[x]*2) for x in jaValueTarget])

    def toNameValueDict(self) -> Dict[str,float]:
        valueTarget = getValueTarget(self.isGlobal)
        return {valueTargetZHToJA(valueTarget[i]):self.valueArray[i] for i in range(len(valueTarget))}
    
    def toNameStdDevDict(self) -> Dict[str,float]:
        valueTarget = getValueTarget(self.isGlobal)
        return {valueTargetZHToJA(valueTarget[i]):self.devArray[i] for i in range(len(valueTarget))}
    
    def getValueFromZH(self,zhstr:str) -> float:
        index = valueTargetIndexOf(zhstr,self.isGlobal)
        if(index >= 0):
            return self.valueArray[index]
        else:
            jastr = ItemIdToName.zhToJa(zhstr)
            return RiseiOrTimeValues.__constValueDict.get(jastr,0.0)
    
    def getValueFromJa(self,jastr:str) -> float:
        zhStr = ItemIdToName.getZH(ItemIdToName.jaToId(jastr))
        return self.getValueFromZH(zhStr)
    
    def getValueFromJaList(self,jastrList:List[str]) -> List[float]:
        return [self.getValueFromJa(jastr) for jastr in jastrList]

    def getValueFromCode(self,codeStr:str) -> float:
        zhstr = ItemIdToName.getZH(codeStr)
        return self.getValueFromZH(zhstr)
    
    def getValueFromJaCountDict(self,jaCountDict:Dict[str,float]):
        return sum([self.getValueFromJa(name)*count for name,count in jaCountDict.items()])

    def getStdDevFromZH(self,zhstr:str) -> float:
        index = valueTargetIndexOf(zhstr,self.isGlobal)
        if(index >= 0):
            return self.devArray[index]
        else:
            return 0.0

    def setDevArray(self,stdDevArray:np.ndarray):
        self.devArray = stdDevArray

    def toIdValueDict(self) -> Dict[str,float]:
        valueTarget = getValueTarget(self.isGlobal)
        return {ItemIdToName.zhToId(valueTarget[i]):self.valueArray[i] for i in range(len(valueTarget))}
    
    def getValueFromItemArray(self,array:itemArray.ItemArray) -> float:
        zhDict = array.normalizeSoC().toZHStrCountDict()
        ret = 0
        for key,count in zhDict.items():
            value = self.getValueFromZH(key)
            ret += count * value
        return ret
    
    def getValueFromItemArray_OnlyValueTarget(self,array:itemArray.ItemArray) -> float:
        zhDict = array.toZHStrCountDict()
        ret = 0
        for key,count in zhDict.items():
            if(key not in getValueTarget(self.isGlobal)): continue
            value = self.getValueFromZH(key)
            ret += count * value
        return ret
    
    def toRiseiArrayFromColumnJaNameList(self,columns:List[str])->np.ndarray:
        return np.array([self.getValueFromJa(name) for name in columns])

__allBufferdInfo = {}
def getBufferedInfo(req:str,additional,force:bool):
    if(force): __allBufferdInfo.pop(req,None)
    ret = __allBufferdInfo.get(req,None)
    if (ret is None):
        ret = get_json(req,additional)
    if(not force):
        __allBufferdInfo[req] = ret
    return ret

def getStage(force):
    return getBufferedInfo("stages",None,force)

def getMatrix(force):
    additionalHeader = {"server":"CN","show_closed_zones":"true"}
    return getBufferedInfo("result/matrix",additionalHeader,force)["matrix"]
        

class StageItem:
    def __init__(self,dictItem):
        self.name = dictItem["code"]
        self.zoneId = dictItem["zoneId"]
        self.zoneName = ZoneIdToName.getStr(dictItem["zoneId"])
        self.id = dictItem["stageId"]
        self.apCost = dictItem["apCost"]
        self.stageType = dictItem["stageType"]
        #一部のクリア時間は理論値と乖離するので、個別で調整
        minClearTime = dictItem["minClearTime"]
        if(minClearTime is None): minClearTime = 0
        self.minClearTime = minClearTimeInjection.get(self.name,minClearTime/1000) #等倍秒
        #ドロップリストを記録する
        self.dropList = DropList()
        self.mainDropIds = [x["itemId"] for x in dictItem.get("dropInfos",[]) if x["dropType"] == "NORMAL_DROP" and "itemId" in x.keys()]
    
    def getMainDropJaStr(self) -> str:
        msg = " ".join([ItemIdToName.getStr(x) for x in self.mainDropIds])
        if(msg):
            return " "+msg
        return ""

    def isValidForShow(self,showMinTimes:int,isGlobal:bool):
        if self.maxTimes() < showMinTimes:
            return False
        if self.dropList.toDropArray(isGlobal).sum() < EPSILON:
            return False
        return True

    #ドロップ配列を入手 理性消費で貰える金も追加する
    def toDropArray(self,isGlobal:bool) -> np.ndarray:
        #ドロップ率で計算したドロップ配列
        dropRateArray = self.dropList.toDropArray(isGlobal)
        #理性消費に応じて金を追加
        lmdIndex = valueTargetIndexOf('龙门币1000',isGlobal)
        length = len(getValueTarget(isGlobal))
        lmdArray = np.zeros(length)
        lmdArray[lmdIndex] = self.apCost*0.012
        return dropRateArray + lmdArray
    
    def getDropRate(self,zhStr:str,isGlobal:bool) -> float:
        index = valueTargetIndexOf(zhStr,isGlobal)
        return self.toDropArray(isGlobal)[index]
    
    #データフレームにする
    def toDataFrame(self,isGlobal:bool) -> pd.DataFrame:
        columns = getDataFrameColumnsName(isGlobal)
        mainData = [np.append(self.toDropArray(isGlobal),self.apCost)]
        index = [str(self)]
        return pd.DataFrame(mainData,index = index, columns=columns)
    
    #計算モードに応じてコストを取得
    def getCost(self,mode:CalculateMode):
        if mode is CalculateMode.SANITY:
            return self.apCost
        elif mode is CalculateMode.TIME:
            return self.minClearTime
        return None
    
    #標準偏差値を取得
    def toStdDevArray(self,isGlobal:bool) -> np.ndarray:
        return self.dropList.toStdDevArray(isGlobal)
    
    #matrix加算用
    def addDropList(self,dropItem,isGlobal:bool):
        itemId = dropItem["itemId"]
        if idInValueTarget(itemId,isGlobal):
            self.dropList += DropList(dropItem)

    def minTimes(self):
        return self.dropList.minTimes()
    
    def maxTimes(self):
        return self.dropList.maxTimes()
    #理性効率を計算
    def getEfficiency(self,riseiValue:RiseiOrTimeValues) -> float:
        totalValue = sum(self.toDropArray(riseiValue.isGlobal) * riseiValue.valueArray)
        mode = riseiValue.mode
        if mode is CalculateMode.SANITY:
            return totalValue / self.apCost
        elif self.minClearTime <= 0:
            return -1
        return totalValue / self.minClearTime
    
    def getPartialEfficiency(self,riseiValue:RiseiOrTimeValues,items:List[str]) -> float:
        mode = riseiValue.mode
        totalValue = sum(
            [riseiValue.getValueFromZH(x)*self.getDropRate(x,riseiValue.isGlobal) for x in items]
        )
        if mode is CalculateMode.SANITY:
            return totalValue / self.apCost
        elif self.minClearTime <= 0:
            return -1
        return totalValue / self.minClearTime
    
    #誤差項を計算
    def getStdDev(self,riseiValue:RiseiOrTimeValues) -> float:
        stdDev = self.toStdDevArray(riseiValue.isGlobal)
        dev1 = np.dot(stdDev**2,riseiValue.valueArray**2)
        dev2 = np.dot(self.toDropArray(riseiValue.isGlobal)**2,riseiValue.devArray**2)
        dev = dev1 + dev2
        return dev ** 0.5

    def getMaxEfficiencyItem(self,riseiValue:RiseiOrTimeValues) -> Tuple[str,float]:
        maxKey,dropRate,value = max([(key,value.dropRate,value.dropRate*riseiValue.getValueFromCode(key))for key,value in self.dropList.dropDict.items()],key = lambda x:x[1])
        return (ItemIdToName.getStr(maxKey),dropRate)

    def __repr__(self) -> str:
        return self.nameWithReplicate()
    
    def nameWithReplicate(self) -> str:
        ret = self.name
        if "re_" in self.zoneId:
            ret += "(Re)"
        #print(self.maxTimes())
        return ret

class StageInfo:
    def __init__(self,isGlobal:bool):
        self.isGlobal = isGlobal
        self.mainStageDict:Dict[str,StageItem] = {}
        self.eventStageDict:Dict[str,StageItem] = {}
        self.mainCodeToStageDict:Dict[str,StageItem] = {}
        self.eventCodeToStageDict:Dict[str,StageItem] = {}
        self.lastUpdated = None
        self.firstInitialized = False
        self.init()
    #ステージ情報更新できるように外から呼び出せるようにする
    def init(self):
        allStageList = getStage(self.firstInitialized)
        #イベントステージを除外
        exclusionList = new_zone if self.isGlobal else []
        exclusionList += ["recruit"] #公開求人を除外
        mainStageList = [x for x in allStageList if x["stageType"] in ["MAIN","SUB"] and x["zoneId"] not in exclusionList and "tough" not in x["zoneId"]]
        #常設イベントステージ
        mainStageList += [x for x in allStageList if x["stageType"] in ["ACTIVITY"] and "permanent" in x["zoneId"] and x["zoneId"] not in exclusionList]
        #イベントステージ、常に日本版未実装を含む
        eventStageList = [x for x in allStageList if x["stageType"] in ["ACTIVITY"] \
            and "permanent" not in x["zoneId"] \
            and "act" in x["zoneId"] \
            and "gacha" not in x["stageId"] \
            #ウルサスの子供を除外
            and "act10d5" not in x["zoneId"] 
        ]
        def createStageDict(stageList) -> Dict[str,StageItem]:
            return {x["stageId"]:StageItem(x) for x in stageList}
        
        self.mainStageDict = createStageDict(mainStageList)
        self.eventStageDict = createStageDict(eventStageList)

        #作戦コードから逆引きする辞書を作成
        def createCodeToStageDict(stageDict:Dict[str,StageItem]) -> Dict[str,StageItem]:
            codeToStage = {}
            for value in stageDict.values():
                codeToStage[str(value)] = value
            return codeToStage
        self.mainCodeToStageDict = createCodeToStageDict(self.mainStageDict)
        self.eventCodeToStageDict = createCodeToStageDict(self.eventStageDict)
        
        #カテゴリ辞書の作成
        categoryDict = getStageCategoryDict(self.isGlobal)
        self.categoryDict:Dict[str,dict] ={}
        for key,value in categoryDict.items():
            #print(value)
            self.categoryDict[key] = {
                "Stages" : [self.mainCodeToStageDict[x] for x in value["Stages"] if x in self.mainCodeToStageDict],
                "Items" : value["Items"],
                "MainItem": value["MainItem"],
                "SubItem" : value.get("SubItem",[]),
                "SubOrder" : value.get("SubOrder",[]),
                "to_ja" : value["to_ja"]
            }
        self.initMatrix()
    
    def initMatrix(self):
        #matrix代入, targetServerはCNで固定
        matrix = getMatrix(self.firstInitialized)#一回目ここで死んでる
        allStageDict = {**self.mainStageDict,**self.eventStageDict}
        for item in matrix:
            key = item["stageId"]
            stageItem = allStageDict.get(key)
            if not stageItem: continue
            stageItem.addDropList(item,self.isGlobal)
        self.lastUpdated = getnow.getnow()
        self.firstInitialized = True

    def validBaseStages(self,validBaseMinTimes:int) -> List[StageItem]:
        return sum([self.categoryValidStages(category,validBaseMinTimes) for category in getStageCategoryDict(self.isGlobal).keys()],[])

    def categoryValidStages(self,category:str,validBaseMinTimes:int)->List[StageItem]:
        allStageList:List[StageItem] = self.categoryDict[category]["Stages"]
        #新素材のステージの有効ステージが存在しない場合、validBaseMinTimesを無視する
        validStageList:List[StageItem] = [x for x in allStageList if x.maxTimes() >= validBaseMinTimes]
        if(not validStageList): validStageList = allStageList
        return validStageList
    
    def stageToCategory(self,stage:StageItem) -> List[str]:
        return [key for key,value in self.categoryDict.items() if stage in value["Stages"]]
    
    #全ステージの効率を計算し、最大効率のカテゴリを取得
    class CategoryMaxEfficiencyItem:
        def __init__(self,maxValue:float,stage:StageItem,categories:List[str]):
            self.maxValue = maxValue
            self.stage = stage
            self.categories = categories

    def getCategoryMaxEfficiency(self,values:RiseiOrTimeValues,validBaseMinTimes:int)->CategoryMaxEfficiencyItem:
        validStageList = self.validBaseStages(validBaseMinTimes)
        efficiencyAndStages:List[Tuple[float,StageItem]]  = [(x.getEfficiency(values),x) for x in validStageList]
        maxValue,maxStage = max(efficiencyAndStages,key= lambda x: x[0])
        maxCategories = self.stageToCategory(maxStage)
        return StageInfo.CategoryMaxEfficiencyItem(maxValue,maxStage,maxCategories)

    def generateCategorySeed(self,validBaseMinTimes:int) -> Dict[str,StageItem]:
        ret:Dict[str,StageItem] = {}
        for key in self.categoryDict.keys():
            validStageList = self.categoryValidStages(key,validBaseMinTimes)
            randomChoiced = random.choice(validStageList)
            ret[key] = randomChoiced
        if hasduplicates.has_duplicates(ret.values()):
            return self.generateCategorySeed(validBaseMinTimes) #重複要素があればやり直し
        return ret

    def __repr__(self) -> str:
        return "Main:" + str(self.mainStageDict.values()) + "\n" + "Event:" + str(self.eventStageDict.values())

class Calculator:
    def __init__(self,isGlobal:bool):
        self.isGlobal:bool = isGlobal
        self.initialized = False
        self.stageInfo:StageInfo = None
        self.convertionMatrix:Calculator.ConstStageMatrix = None
        self.init()
    
    class ConvertionItem:
        def __init__(self,isGlobal:bool,name:str = ""):
            totalCount = len(getValueTarget(isGlobal))
            self.valueArray = np.zeros(totalCount)
            self.isGlobal = isGlobal
            self.name = name
        
        def setValue(self,valueDict:Dict[str,float]):
            for zhStr,value in valueDict.items():
                index = valueTargetIndexOf(zhStr,self.isGlobal)
                if(index >= 0):
                    self.valueArray[index] = value
        
        def addValue(self,valueDict:Dict[str,float]):
            for zhStr,value in valueDict.items():
                index = valueTargetIndexOf(zhStr,self.isGlobal)
                if(index >= 0):
                    self.valueArray[index] += value

        def getValueArray(self):
            return self.valueArray
        
        def __repr__(self) -> str:
            return self.name + ":" + str(self.valueArray)
    
    class ConvertionMatrix:
        def __init__(self,isGlobal:bool,convertionDropRate:float = 0.18):
            convertionItemList:List[Calculator.ConvertionItem] = []
            self.isGlobal = isGlobal
            #経験値換算
            #基础作战记录*2=初级作战记录
            item:Calculator.ConvertionItem = Calculator.ConvertionItem(isGlobal,"経験値換算1")
            item.setValue({
                "基础作战记录":-2,
                "初级作战记录":1
            })
            convertionItemList.append(item)

            # 初级作战记录*2.5=中级作战记录
            item = Calculator.ConvertionItem(isGlobal,"経験値換算2")
            item.setValue({
                "初级作战记录":-2.5,
                "中级作战记录":1
            })
            convertionItemList.append(item)

            # 中级作战记录*2=高级作战记录
            item = Calculator.ConvertionItem(isGlobal,"経験値換算3")
            item.setValue({
                "中级作战记录":-2,
                "高级作战记录":1
            })
            convertionItemList.append(item)

            # 赤金*2 = 龙门币1000
            item = Calculator.ConvertionItem(isGlobal,"純金換算")
            item.setValue({
                "赤金":-2,
                "龙门币1000":1
            })
            convertionItemList.append(item)

            # 素材合成換算
            formula = Formula.getAllFormulaItems()
            for formulaItem in formula:
                if ItemIdToName.getZH(formulaItem.key) not in getValueTarget(isGlobal):
                    continue
                #print(ItemIdToName.getZH(formulaItem.key))
                item = Calculator.ConvertionItem(isGlobal,"合成-"+ItemIdToName.getStr(formulaItem.key))
                item.setValue(formulaItem.toFormulaArrayWithOutcome(convertionDropRate,self.isGlobal).toZHStrCountDict())
                convertionItemList.append(item)
            
            # 本の合成
            # 技1*3=技2
            # item = Calculator.ConvertionItem(isGlobal,"スキル本換算1")
            # item.setValue({
            #     "技巧概要·卷1":3,
            #     "技巧概要·卷2":-1-convertionDropRate
            # })
            # convertionItemList.append(item)

            # item = Calculator.ConvertionItem(isGlobal,"スキル本換算2")
            # item.setValue({
            #     "技巧概要·卷2":3,
            #     "技巧概要·卷3":-1-convertionDropRate
            # })
            # convertionItemList.append(item)
            self.convertionItemList:List[Calculator.ConvertionItem] = convertionItemList

        def getMatrix(self):
            return np.array([x.getValueArray() for x in self.convertionItemList])
        
        def getCostArray(self,mode:CalculateMode):
            return np.zeros(len(self.convertionItemList))
        
        def getStdDevMatrix(self):
            return np.zeros(shape=(len(self.convertionItemList),len(getValueTarget(self.isGlobal))))
        
        def __repr__(self) -> str:
            return "\n".join([str(item) for item in self.convertionItemList])
        
        def getRowsName(self):
            return [x.name for x in self.convertionItemList]

        
    #作戦記録、龍門幣、本のステージドロップを司るクラス
    class StageDropItem(ConvertionItem):
        def __init__(self, isGlobal: bool, name: str = ""):
            super().__init__(isGlobal, name)
            self.apCost:int = 0
            self.minClearTime:float = 0
        
        def setCosts(self, ap:int, time:float):
            self.apCost = ap
            self.minClearTime = time
        
        def setDropArray(self,array:np.ndarray):
            self.valueArray = array

    class ConstStageMatrix:
        def __init__(self,isGlobal:bool):
            self.isGlobal = isGlobal
            self.constStageItemList:List[Calculator.StageDropItem] = []
            #LS-6
            item:Calculator.StageDropItem = Calculator.StageDropItem(isGlobal,"LS-6")
            item.setValue({
                "初级作战记录":0,
                "中级作战记录":2,
                "高级作战记录":4,
                "龙门币1000":0.432
            })
            item.setCosts(36,183.0)
            self.constStageItemList.append(item)

            #CE-6
            item = Calculator.StageDropItem(isGlobal,"CE-6")
            item.setValue({
                "龙门币1000":10
            })
            item.setCosts(36,172)
            self.constStageItemList.append(item)

            #CA-5
            item = Calculator.StageDropItem(isGlobal,"CA-5")
            item.setValue({
                "技巧概要·卷1":1.5,
                "技巧概要·卷2":1.5,
                "技巧概要·卷3":2,
                "龙门币1000":0.36
            })
            item.setCosts(30,173)
            self.constStageItemList.append(item)
        
        def getMatrix(self):
            return np.array([x.getValueArray() for x in self.constStageItemList])
        
        def getCostArray(self,mode:CalculateMode):
            return np.array([x.apCost if mode is CalculateMode.SANITY else x.minClearTime for x in self.constStageItemList])
        
        def getStdDevMatrix(self):
            return np.zeros(shape=(len(self.constStageItemList),len(getValueTarget(self.isGlobal))))
        
        def __repr__(self) -> str:
            return "\n".join([str(item) for item in self.constStageItemList])
        
        def getRowsName(self):
            return [x.name for x in self.constStageItemList]
        
    class BaseStageDropItem:
        def __init__(self, isGlobal:bool, category:str, stageItem:StageItem):
            self.stageItem = stageItem
            self.name = categoryZHToJA(category,isGlobal) + stageItem.name
            self.isGlobal = isGlobal
        def __repr__(self) -> str:
            return self.name # + ":" + str(self.stageItem.toDropArray(self.isGlobal))

    class BaseStageMatrix:
        def __init__(self,isGlobal:bool,stageInfo:StageInfo,validBaseMinTimes:int) -> None:
            self.isGlobal = isGlobal
            self.stageInfo = stageInfo
            self.baseStageItemDict:Dict[str,Calculator.BaseStageDropItem] = {}
            self.validBaseMinTimes = validBaseMinTimes
            #初期化　ランダムにseed生成
            seed = self.stageInfo.generateCategorySeed(self.validBaseMinTimes)
            self.initBaseStages(seed)
            self.lastUpdated:datetime.datetime = None

        def initBaseStages(self,seed:Dict[str,StageItem]):
            self.baseStageItemDict = {key:Calculator.BaseStageDropItem(self.isGlobal,key,value) for key,value in seed.items()}

        def getMatrix(self):
            return np.array([x.stageItem.toDropArray(self.isGlobal) for x in self.baseStageItemDict.values()])
        
        def getCostArray(self,mode:CalculateMode):
            return np.array([x.stageItem.apCost if mode is CalculateMode.SANITY else x.stageItem.minClearTime for x in self.baseStageItemDict.values()])
        
        def getStdDevMatrix(self):
            return np.array([x.stageItem.toStdDevArray(self.isGlobal) for x in self.baseStageItemDict.values()])
        
        def toString(self) -> str:
            return str({categoryZHToJA(key,self.isGlobal):value.stageItem.name for key,value in self.baseStageItemDict.items()})

        def __repr__(self) -> str:
            return self.toString()
        
        def update(self,values:RiseiOrTimeValues) -> bool:
            maxEfficiencyItem = self.stageInfo.getCategoryMaxEfficiency(values,self.validBaseMinTimes)
            if not maxEfficiencyItem.categories:
                msg = "カテゴリから外れたマップを検出、計算を中断します\n"
                msg += "マップ" + maxEfficiencyItem.stage.name + "は、何を稼ぐステージですか？\n"
                raise Exception(msg)
            if maxEfficiencyItem.maxValue <= 1.0 + EPSILON:
                return False #続けて更新しなくてよい
            targetCategory = random.choice(maxEfficiencyItem.categories)
            print(targetCategory,":",maxEfficiencyItem.stage.name,"=",maxEfficiencyItem.maxValue,"基準マップ差し替え実行")
            self.baseStageItemDict[targetCategory] = Calculator.BaseStageDropItem(self.isGlobal,targetCategory,maxEfficiencyItem.stage)
            self.lastUpdated = getnow.getnow()
            return True

        def getBaseStages(self) -> Dict[str,str]:
            return {key:value.stageItem.name for key,value in self.baseStageItemDict.items()}
        
        def contains(self,stage:StageItem):
            return stage in [x.stageItem for x in self.baseStageItemDict.values()]
        
        def getRowsName(self):
            return [x.name for x in self.baseStageItemDict.values()]
    
    def getBaseStageMatrix(self,mode:CalculateMode) -> BaseStageMatrix:
        return self.baseStageMatrixForSanity if mode is CalculateMode.SANITY else self.baseStageMatrixForTime

    def getProbMatrix(self,mode:CalculateMode) -> np.ndarray:
        return np.vstack((
            self.convertionMatrix.getMatrix(),
            self.constStageMatrix.getMatrix(),
            self.getBaseStageMatrix(mode).getMatrix()
        ))
    
    def getCostArray(self,mode:CalculateMode) -> np.ndarray:
        return np.concatenate([
            self.convertionMatrix.getCostArray(mode),
            self.constStageMatrix.getCostArray(mode),
            self.getBaseStageMatrix(mode).getCostArray(mode)
        ])
    
    def getDevMatrix(self,mode:CalculateMode) -> np.ndarray:
        return np.vstack((
            self.convertionMatrix.getStdDevMatrix(),
            self.constStageMatrix.getStdDevMatrix(),
            self.getBaseStageMatrix(mode).getStdDevMatrix()
        ))
    
    def getBaseMinTimes(self,mode:CalculateMode) -> bool:
        return self.getBaseStageMatrix(mode).validBaseMinTimes

    def solveValues(self,mode:CalculateMode) -> RiseiOrTimeValues:
        probMatrix = self.getProbMatrix(mode)
        costArray = self.getCostArray(mode)
        valueArray = LA.solve(probMatrix,costArray)
        return RiseiOrTimeValues(valueArray,self.isGlobal,mode)
    
    #最適な理性効率を計算し、基準ステージを更新する
    def solveOptimizedValue(self,mode:CalculateMode) -> RiseiOrTimeValues:
        print("計算を開始します..")
        values = self.solveValues(mode)
        baseMatrix = self.getBaseStageMatrix(mode)
        while(baseMatrix.update(values)):
            values = self.solveValues(mode)
        print("Done")
        #誤差を設定する
        probMatrix = self.getProbMatrix(mode)
        probMatrixInv = np.linalg.inv(probMatrix)
        devMatrix = self.getDevMatrix(mode)
        devArray = np.dot(np.dot(probMatrixInv**2,devMatrix**2),values.valueArray**2)**0.5
        values.setDevArray(devArray)
        return values

    def init(self,validBaseMinTimes:int=3000,mode:CalculateMode = None, forceRecreateStageInfo:bool = False):

        #ステージ情報クラスを更新
        if(self.stageInfo and not forceRecreateStageInfo):
            self.stageInfo.initMatrix() #ステージの構成情報までは更新しない（ドロップ情報のみ更新）
        else:
            self.stageInfo = StageInfo(self.isGlobal) #ステージ全更新
        
        #一回目、もしくは強制更新の場合、convertionMatrix(アイテム合成情報)を更新
        if(not self.convertionMatrix or forceRecreateStageInfo): 
            self.convertionMatrix = Calculator.ConvertionMatrix(self.isGlobal)

        #LS CE CAクラスは作成コスト低いのでとりあえず更新
        self.constStageMatrix = Calculator.ConstStageMatrix(self.isGlobal)
        self.calculate(mode,validBaseMinTimes)
        self.initialized = True
    
    def calculate(self,mode:CalculateMode = None,validBaseMinTimes:int=3000):
        if (mode is None or mode is CalculateMode.SANITY):
            self.baseStageMatrixForSanity = Calculator.BaseStageMatrix(self.isGlobal,self.stageInfo,validBaseMinTimes)
            self.riseiValues = self.solveOptimizedValue(CalculateMode.SANITY)
        if (mode is None or mode is CalculateMode.TIME):
            self.baseStageMatrixForTime = Calculator.BaseStageMatrix(self.isGlobal,self.stageInfo,validBaseMinTimes)
            self.timeValues = self.solveOptimizedValue(CalculateMode.TIME)
        
    def tryRecalculate(self,mode:CalculateMode = None, validBaseMinTimes:int = 3000)->bool:
        #mode is None: いずれかのvalidBaseMinTimesと違う
        if (mode is None and self.baseStageMatrixForSanity.validBaseMinTimes == validBaseMinTimes and self.baseStageMatrixForTime.validBaseMinTimes == validBaseMinTimes):
            return False
        if mode is not None:
            baseStageMatrix = self.getBaseStageMatrix(mode)
            if baseStageMatrix.lastUpdated > self.stageInfo.lastUpdated and baseStageMatrix.validBaseMinTimes == validBaseMinTimes:
                return False
        self.calculate(mode,validBaseMinTimes)
        return True

    def getValues(self,mode:CalculateMode) -> RiseiOrTimeValues:
        if mode is CalculateMode.SANITY: return self.riseiValues
        return self.timeValues

    #ステージ情報が古ければ更新する。期限は外部からの指定、指定しない場合は強制更新
    def tryReInit(self,timeDiff:Optional[datetime.timedelta],validBaseMinTimes:Optional[int],mode:CalculateMode = None) -> bool:
        now = getnow.getnow()
        if self.initialized and timeDiff and (timeDiff<datetime.timedelta(0) or now < self.stageInfo.lastUpdated+timeDiff):
            return self.tryRecalculate(mode,validBaseMinTimes)
        if self.initialized:
            baseMinTimes = validBaseMinTimes if validBaseMinTimes else self.getBaseMinTimes(mode)
            self.init(baseMinTimes,mode)
        elif validBaseMinTimes:
            self.init(validBaseMinTimes,mode)
        else:
            self.init(mode=mode)
        return True

    def searchMainStage(self,targetCode:str,showMinTimes:int) -> List[StageItem]:
        return [value for key,value in self.stageInfo.mainCodeToStageDict.items() if key.startswith(targetCode) and value.isValidForShow(showMinTimes,self.isGlobal)]
    
    def autoCompleteMainStage(self,targetCode:str,limit:int=25) -> List[Tuple[str,str]]:
        return [(str(x)+x.getMainDropJaStr(),str(x)) for x in self.searchMainStage(targetCode,DEFAULT_SHOW_MIN_TIMES)][:limit]
    
    def searchEventStage(self,targetCode:str,showMinTimes:int) -> List[StageItem]:
        return [value for key,value in self.stageInfo.eventCodeToStageDict.items() if key.startswith(targetCode) and value.isValidForShow(showMinTimes,self.isGlobal)]
    
    def autoCompleteEventStage(self,targetCode:str,limit:int=25) -> List[Tuple[str,str]]:
        return [(str(x)+x.getMainDropJaStr(),str(x)) for x in self.searchEventStage(targetCode,DEFAULT_SHOW_MIN_TIMES)][:limit]
    
    #理性効率の誤差項を計算する
    def getStageDev(self,targetStage:StageItem,values:RiseiOrTimeValues) -> float:
        baseMatrix = self.getBaseStageMatrix(values.mode)
        if(baseMatrix.contains(targetStage)): return 0
        cost = targetStage.getCost(values.mode)
        cost = cost if cost > 0 else 1
        #効率の誤差 = ステージ価値の誤差 / ステージコスト
        return targetStage.getStdDev(values) / cost
    
    def toDataFrame(self,mode:CalculateMode) -> pd.DataFrame:
        columnsName = getDataFrameColumnsName(self.isGlobal)
        baseMatrix = self.getBaseStageMatrix(mode)
        rowsName = self.convertionMatrix.getRowsName() + self.constStageMatrix.getRowsName() + baseMatrix.getRowsName() + ["理性価値","標準偏差"]
        probMatrix = self.getProbMatrix(mode)
        values = self.getValues(mode).valueArray
        stdDev = self.getValues(mode).devArray
        costs = self.getCostArray(mode)
        mainData = np.vstack((probMatrix,values,stdDev))
        mainData = np.hstack((mainData,np.concatenate([costs,[0,0]]).reshape(-1,1)))
        return pd.DataFrame(mainData,columns=columnsName,index=rowsName)
    
    def dumpToFile(self,mode:CalculateMode):
        df = self.toDataFrame(mode)
        df.to_excel(EXCEL_FILENAME)
        print("基準マップデータを"+EXCEL_FILENAME+"に保存しました")

    def getUpdatedTimeStr(self) -> str:
        time = self.stageInfo.lastUpdated
        return "ドロップデータ更新時刻:\t{0}".format(time.strftime('%Y/%m/%d %H:%M:%S'))

class CalculatorManager:
    calculatorForGlobal = Calculator(True)
    calculatorForMainland = Calculator(False)
    CC_NUMBER = "12"
    
    def selectCalculator(isGlobal:bool):
        return CalculatorManager.calculatorForGlobal if isGlobal else CalculatorManager.calculatorForMainland
    
    def updateAllCalculators():
        CalculatorManager.calculatorForGlobal.init(forceRecreateStageInfo=True)
        CalculatorManager.calculatorForMainland.init(forceRecreateStageInfo=True)

    def __getTimeDelta(minutes:float):
        return datetime.timedelta(minutes = minutes)
    
    class ToPrint(StrEnum):
        BASEMAPS = enum.auto()
        SAN_VALUE_LISTS = enum.auto()
        ITEMS = enum.auto()
        ZONE = enum.auto()
        EVENTS = enum.auto()
        TE2LIST = enum.auto()
        TE3LIST = enum.auto()
        SPECIAL_LIST = enum.auto()
        CCLIST = enum.auto()
        POLIST = enum.auto()

    def getValues(isGlobal:bool,mode:CalculateMode,baseMinTimes:int = 3000, cache_minutes:float = DEFAULT_CACHE_TIME) -> RiseiOrTimeValues:
        #print(f"mode:{mode},baseMinTimes:{baseMinTimes},cacheMinutes:{cache_minutes}")
        if baseMinTimes > BASEMINTIMES_UPPER: baseMinTimes = BASEMINTIMES_UPPER
        if baseMinTimes < 0: baseMinTimes = 0
        calculator = CalculatorManager.selectCalculator(isGlobal)
        calculator.tryReInit(CalculatorManager.__getTimeDelta(cache_minutes),baseMinTimes,mode)
        return calculator.getValues(mode)
    
    def filterStagesByShowMinTimes(stageList:List[StageItem],showMinTimes:int,isGlobal:bool):
        ret = [x for x in stageList if x.isValidForShow(showMinTimes,isGlobal)]
        if(not ret):
            return stageList #フィルターの結果全部なくなってしまう可哀想なカテゴリは全部返す
        return ret

    def dumpToPrint(toPrint,header = ""):
        body = "\n".join(["".join(x) for x in toPrint])
        return f"```{header}\n{body}```"
    
    def left(digit, msg):
        for c in msg:
            if unicodedata.east_asian_width(c) in ('F', 'W', 'A'):
                digit -= 2
            else:
                digit -= 1
        return msg + ' '*digit
    def stagesToExcelFile(mode:CalculateMode,isGlobal:bool,stageList:List[StageItem],filename:str):
        calculator = CalculatorManager.selectCalculator(isGlobal)
        valuesDF = calculator.toDataFrame(mode)
        allDFs = [stage.toDataFrame(isGlobal) for stage in stageList]
        allDFs.insert(0,valuesDF)
        df:pd.DataFrame = pd.concat(objs=allDFs)
        df.to_excel(filename)
    
    def execStagesToExcelFile(mode:CalculateMode,isGlobal:bool,stageList:List[StageItem],filename:str,exec:bool = True)->str:
        if(exec):
            CalculatorManager.stagesToExcelFile(mode,isGlobal,stageList,filename)
            return filename
        else:
            return None

    def sortStagesByEfficiency(stageList:List[StageItem],riseiValues:RiseiOrTimeValues):
        return sorted(stageList,key = lambda x: x.getEfficiency(riseiValues),reverse=True)
    
    
    def riseicalculatorMaster(toPrint:str,targetItem:str,targetStage:str,isGlobal:bool,mode:CalculateMode,baseMinTimes:int = 3000, cache_minutes:float = DEFAULT_CACHE_TIME,showMinTimes:int = 1000,maxItems:int = 15, toCsv = False) -> RCReply:
        #Chat GPT経由で呼び出されることはないので、responseToAIの値は入れなくて良い
        if toPrint == "items":
            if(not targetItem): 
                return RCReply(
                    embbedTitle="エラー",
                    embbedContents=["target_itemに素材カテゴリを入れてください"],
                    msgType=RCMsgType.ERR
                )
            return CalculatorManager.riseimaterials(targetItem,isGlobal,mode,baseMinTimes,cache_minutes,showMinTimes,maxItems,toCsv)
        elif toPrint == "zone":
            if(not targetStage):
                return RCReply(
                    embbedTitle="エラー",
                    embbedContents=["event_codeにマップ名を入れてください"],
                    msgType=RCMsgType.ERR
                )
            return CalculatorManager.riseistages(targetStage,isGlobal,mode,baseMinTimes,cache_minutes,showMinTimes,maxItems,toCsv)
        elif toPrint == "events":
            if(not targetStage):
                return RCReply(
                    embbedTitle="エラー",
                    embbedContents=["event_codeにマップ名を入れてください"],
                    msgType=RCMsgType.ERR
                )
            return CalculatorManager.riseievents(targetStage,isGlobal,mode,baseMinTimes,cache_minutes,showMinTimes,maxItems,toCsv)
        else:
            toPrintTarget = CalculatorManager.ToPrint(toPrint)
            return CalculatorManager.riseilists(toPrintTarget,isGlobal,mode,baseMinTimes,cache_minutes,toCsv)

    def riseimaterials(targetCategory:str,isGlobal:bool,mode:CalculateMode,baseMinTimes:int = 3000, cache_minutes:float = DEFAULT_CACHE_TIME,showMinTimes:int = 1000,maxItems:int = 15, toCsv = False) -> RCReply:
        #大陸版先行素材を選ぶ場合、isGlobal指定にかかわらず、自動で大陸版計算とする
        if(targetCategory in StageCategoryDict["new"].keys()): isGlobal = False
        riseiValues:RiseiOrTimeValues = CalculatorManager.getValues(isGlobal,mode,baseMinTimes,cache_minutes)
        #print(riseiValue)
        calculator:Calculator = CalculatorManager.selectCalculator(isGlobal)
        if not (categoryValue := calculator.stageInfo.categoryDict.get(targetCategory)):
            return RCReply(
                embbedTitle=title,
                embbedContents=["無効なカテゴリ:" + targetCategory],
                msgType=RCMsgType.ERR,
                responseForAI=f"Error: Invalid Category: {targetCategory}"
            )
        title = "昇進素材検索"
        stages = categoryValue.get("Stages",[])
        stagesToShow = CalculatorManager.filterStagesByShowMinTimes(stages,showMinTimes,isGlobal)
        

        msgHeader = categoryValue["to_ja"]+ ": {2}価値(中級)={0:.3f}±{1:.3f}\n".format(riseiValues.getValueFromZH(categoryValue["MainItem"]),riseiValues.getStdDevFromZH(categoryValue["MainItem"]),str(mode))
        msgChunks = [msgHeader]
        
        #並び変え
        stagesToShow = CalculatorManager.sortStagesByEfficiency(stagesToShow,riseiValues)
        reply = RCReply()
        jsonForAI = []
        cnt = 0

        for stage in stagesToShow:
            cnt += 1
            toPrint = [
                ["マップ名       : ",stage.name],
                ["{1}効率       : {0:.1%}".format(stage.getEfficiency(riseiValues),str(mode))],
                ["理性消費       : {0}".format(stage.apCost)]
            ]
            if stage.minClearTime > 0:
                dropValues = stage.getDropRate(categoryValue["MainItem"],isGlobal)
                for item,order in zip(categoryValue["SubItem"],categoryValue["SubOrder"]):
                    dropValues += stage.getDropRate(item,isGlobal)/order
                dropPerMin = dropValues/stage.minClearTime*120
                toPrint += [
                    ["時間消費(倍速) : {0:.2f}".format(stage.minClearTime/2.0)],
                    ["分入手数(中級) : {0:.2f}".format(dropPerMin)],
                ]
            toPrint += [
                ["主素材効率     : {0:.1%}".format(stage.getPartialEfficiency(riseiValues,categoryValue["Items"]))],
                ["99%信頼区間(3σ): {0:.1%}".format(calculator.getStageDev(stage,riseiValues)*3)],
                ["昇進効率       : {0:.1%}".format(stage.getPartialEfficiency(riseiValues,getValueTarget(isGlobal)[4:]))],
                ["試行数         : ",str(stage.maxTimes())],
            ]
            #print(toPrint)
            jsonForAI.append({
                "stageName":stage.nameWithReplicate(),
                "totalEfficiency":round(stage.getEfficiency(riseiValues),3),
                "mainDropEfficiency":round(stage.getPartialEfficiency(riseiValues,categoryValue["Items"]),3),
                "sanityCost":stage.apCost,
                "timeCost":round(stage.minClearTime/2.0,2),
                "dropPerMinute": round(dropPerMin,2)
            })

            msgChunks.append(CalculatorManager.dumpToPrint(toPrint))
            if maxItems > 0 and cnt >= maxItems:
                break
        #ステージドロップをExcelに整理
        MATERIAL_CSV_NAME = "MaterialsDrop.xlsx"
        reply.embbedTitle = title
        reply.embbedContents = msgChunks
        reply.plainText = calculator.getUpdatedTimeStr()
        reply.responseForAI = str({"stageInfo":jsonForAI})
        if(toCsv):
            reply.attatchments = CalculatorManager.execStagesToExcelFile(mode,isGlobal,stagesToShow,MATERIAL_CSV_NAME)
        return reply

    def riseistages(targetStage:str,isGlobal:bool,mode:CalculateMode,baseMinTimes:int = 3000, cache_minutes:float = DEFAULT_CACHE_TIME,showMinTimes:int = 1000,maxItems:int = 15,toCsv = False) -> RCReply:
        riseiValues:RiseiOrTimeValues = CalculatorManager.getValues(isGlobal,mode,baseMinTimes,cache_minutes)
        calculator:Calculator = CalculatorManager.selectCalculator(isGlobal)
        stagesToShow = calculator.searchMainStage(targetStage,showMinTimes)
        title = "通常ステージ検索"
        if(not stagesToShow):
            return RCReply(
                embbedTitle=title,
                embbedContents=["無効なステージ指定"+targetStage],
                msgType=RCMsgType.ERR,
                responseForAI=f"Error: Invalid stage: {targetStage}"
            )
        msgHeader = "検索内容 = " + targetStage
        #名前順でソート
        stagesToShow.sort(key = lambda x:x.name)
        msgChunks = [msgHeader]
        cnt = 0
        jsonForAI = []
        reply = RCReply()
        for stage in stagesToShow:
            cnt += 1
            toPrint = [
                ["マップ名       : ",stage.name],
                ["総合{1}効率    : {0:.1%}".format(stage.getEfficiency(riseiValues),str(mode))],
                ["99%信頼区間(3σ): {0:.1%}".format(calculator.getStageDev(stage,riseiValues)*3)],
            ]
            dropCategoryList = calculator.stageInfo.stageToCategory(stage)
            if len(dropCategoryList) == 0:
                toPrint.append(["主ドロップ情報未登録"])
            else:
                for category in dropCategoryList:
                    categoryValue = calculator.stageInfo.categoryDict[category]
                    toPrint.append(["{0}: {1:.1%}".format(CalculatorManager.left(15,categoryValue["to_ja"]+"効率"),
                        stage.getPartialEfficiency(riseiValues,categoryValue["Items"]))])
                    if stage.minClearTime > 0:
                        dropValues = stage.getDropRate(categoryValue["MainItem"],isGlobal)
                        for item,order in zip(categoryValue["SubItem"],categoryValue["SubOrder"]):
                            dropValues += stage.getDropRate(item,isGlobal)/order
                        dropPerMin = dropValues/stage.minClearTime*120
                        toPrint += [
                            ["分入手数(中級) : {0:.2f}".format(dropPerMin)],
                        ]
            toPrint.append(["理性消費       : ",str(stage.apCost)])
            if stage.minClearTime > 0:
                toPrint.append(["時間消費(倍速) : ", str(stage.minClearTime/2.0)])
            toPrint += [
                ["昇進効率       : {0:.1%}".format(stage.getPartialEfficiency(riseiValues,getValueTarget(isGlobal)[4:]))],
                ["試行数         : {0}".format(stage.maxTimes())],
            ]

            jsonForAI.append({
                "stageName":stage.nameWithReplicate(),
                "mainDrop":stage.getMaxEfficiencyItem(riseiValues)[0],
                "totalEfficiency":round(stage.getEfficiency(riseiValues),3),
                "sanityCost":stage.apCost,
                "timeCost":round(stage.minClearTime/2.0,2),
            })

            msgChunks.append(CalculatorManager.dumpToPrint(toPrint))
            if maxItems > 0 and cnt >= maxItems:
                break
        #ステージドロップをExcelに整理
        STAGE_CSV_NAME = "StageDrop.xlsx"
        reply.embbedTitle = title
        reply.embbedContents = msgChunks
        reply.plainText = calculator.getUpdatedTimeStr()
        reply.responseForAI = str({"stageInfo":jsonForAI})
        if(toCsv):
            reply.attatchments = CalculatorManager.execStagesToExcelFile(mode,isGlobal,stagesToShow,STAGE_CSV_NAME)
        return reply

    def riseievents(targetStage:str,isGlobal:bool,mode:CalculateMode,baseMinTimes:int = 3000, cache_minutes:float = DEFAULT_CACHE_TIME,showMinTimes:int = 1000,maxItems:int = 20,toCsv = False) -> RCReply:
        riseiValues:RiseiOrTimeValues = CalculatorManager.getValues(isGlobal,mode,baseMinTimes,cache_minutes)
        calculator:Calculator = CalculatorManager.selectCalculator(isGlobal)
        stagesToShow = calculator.searchEventStage(targetStage,showMinTimes)
        #print(stages)
        title = "イベントステージ検索"
        if(not stagesToShow):
            return RCReply(
                embbedTitle=title,
                embbedContents=["無効なステージ指定"+targetStage],
                msgType=RCMsgType.ERR,
                responseForAI=f"Error: Invalid stage: {targetStage}"
            )
        msgHeader = "検索内容 = " + targetStage

        #名前順でソート
        stagesToShow.sort(key = lambda x:x.name)
        msgChunks = [msgHeader]
        cnt = 0
        jsonForAI = []
        reply = RCReply()
        for stage in stagesToShow:
            cnt += 1
            maindrop, droprate = stage.getMaxEfficiencyItem(riseiValues)
            toPrint = [
                ["マップ名       : {0}".format(stage.nameWithReplicate())],
                ["イベント名     : {0}".format(stage.zoneName)],
                ["総合{1}効率   : {0:.1%}".format(stage.getEfficiency(riseiValues),str(mode))],
                ["主ドロップ     : ",maindrop],
                ["ドロップ率     : {0:.2%}".format(droprate)],
                ["試行数         : {0}".format(stage.maxTimes())],
                ["理性消費       : {0}".format(stage.apCost)],
            ]
            if stage.minClearTime > 0:
                toPrint += [
                    ["時間消費(倍速) : ", str(stage.minClearTime/2.0)],
                    ["分間入手数     : {0:.2f}".format(droprate/stage.minClearTime*120)],
                ]
            msgChunks.append(CalculatorManager.dumpToPrint(toPrint))
            jsonForAI.append({
                "stageName":stage.nameWithReplicate(),
                "eventName":stage.zoneName,
                "efficiency":round(stage.getEfficiency(riseiValues),3),
                "mainDrop":maindrop,
                "sanityCost":stage.apCost,
                "timeCost":round(stage.minClearTime/2.0,2),
                "dropRate":round(droprate,4)
            })
            if maxItems > 0 and cnt >= maxItems:
                break
        #ステージドロップをExcelに整理
        EVENT_CSV_NAME = "EventDrop.xlsx"
        reply.embbedTitle = title
        reply.embbedContents = msgChunks
        reply.plainText = calculator.getUpdatedTimeStr()
        reply.responseForAI = str({"stageInfo":jsonForAI})
        if(toCsv):
            reply.attatchments = CalculatorManager.execStagesToExcelFile(mode,isGlobal,stagesToShow,EVENT_CSV_NAME)
        return reply
      
    def riseilists(toPrintTarget:ToPrint,isGlobal:bool,mode:CalculateMode,baseMinTimes:int = 3000, cache_minutes:float = DEFAULT_CACHE_TIME,toCsv = False) -> RCReply:
        riseiValues:RiseiOrTimeValues = CalculatorManager.getValues(isGlobal,mode,baseMinTimes,cache_minutes)
        calculator:Calculator = CalculatorManager.selectCalculator(isGlobal)
        reply = RCReply()
        if toPrintTarget is CalculatorManager.ToPrint.BASEMAPS:
            baseMapStr = calculator.getBaseStageMatrix(mode).toString()
            reply.embbedTitle = "基準ステージ表示"
            reply.embbedContents = [f"`{baseMapStr}`"]
            reply.responseForAI = f"baseMaps:{baseMapStr}"
            
        elif toPrintTarget is CalculatorManager.ToPrint.SAN_VALUE_LISTS:
            title = "{0}価値一覧".format(str(mode))
            toPrint = []
            jsonForAI = {}
            for key in getValueTarget(isGlobal):
                value = riseiValues.getValueFromZH(key)
                stdDev = riseiValues.getStdDevFromZH(key)
                toPrint.append([
                    "{0}: {1:.3f} ± {2:.3f}".format(CalculatorManager.left(15,valueTargetZHToJA(key)),value,stdDev*2)
                ])
                jsonForAI[valueTargetZHToJA(key)] = round(value,3)
            reply.embbedTitle = title
            reply.embbedContents = [CalculatorManager.dumpToPrint(toPrint)]
            reply.responseForAI = str({"values":jsonForAI})

        elif toPrintTarget is CalculatorManager.ToPrint.TE2LIST:
            title = "初級資格証効率"
            ticket_efficiency2 = {ItemIdToName.zhToJa(x):(riseiValues.getValueFromZH(x)/Price[x],riseiValues.getStdDevFromZH(x)/Price[x]) for x in getItemRarity2(isGlobal) if x in Price.keys()}
            ticket_efficiency2_sorted = sorted(ticket_efficiency2.items(),key = lambda x:x[1][0],reverse=True)
            toPrint = [["{0}:\t{1:.3f} ± {2:.3f}".format(CalculatorManager.left(15,key),value[0],value[1]*2)] for key,value in ticket_efficiency2_sorted]
            jsonForAI = {key:round(value[0],3) for key,value in ticket_efficiency2_sorted}

            reply.embbedTitle = title
            reply.embbedContents = [CalculatorManager.dumpToPrint(toPrint)]
            reply.responseForAI = str({"efficiencies":jsonForAI})
 
        elif toPrintTarget is CalculatorManager.ToPrint.TE3LIST:
            title = "上級資格証効率"
            ticket_efficiency3 = {ItemIdToName.zhToJa(x):(riseiValues.getValueFromZH(x)/Price[x],riseiValues.getStdDevFromZH(x)/Price[x]) for x in getItemRarity3(isGlobal) if x in Price.keys()}
            ticket_efficiency3_sorted = sorted(ticket_efficiency3.items(),key = lambda x:x[1][0],reverse=True)
            toPrint = [["{0}:\t{1:.3f} ± {2:.3f}".format(CalculatorManager.left(15,key),value[0],value[1]*2)] for key,value in ticket_efficiency3_sorted]
            jsonForAI = {key:round(value[0],3) for key,value in ticket_efficiency3_sorted}

            reply.embbedTitle = title
            reply.embbedContents = [CalculatorManager.dumpToPrint(toPrint)]
            reply.responseForAI = str({"efficiencies":jsonForAI})

        elif toPrintTarget is CalculatorManager.ToPrint.SPECIAL_LIST:
            title = "特別引換証効率"
            ticket_efficiency_special = {ItemIdToName.zhToJa(x):(riseiValues.getValueFromZH(x)/Price_Special[x],riseiValues.getStdDevFromZH(x)/Price_Special[x]) for x in getItemRarity2(isGlobal)+getItemRarity3(isGlobal) if x in Price_Special.keys()}
            ticket_efficiency_special_sorted = sorted(ticket_efficiency_special.items(),key = lambda x:x[1][0],reverse=True)
            toPrint = [["{0}:\t{1:.3f} ± {2:.3f}".format(CalculatorManager.left(15,key),value[0],value[1]*2)] for key,value in ticket_efficiency_special_sorted]
            jsonForAI = {key:round(value[0],3) for key,value in ticket_efficiency_special_sorted}

            reply.embbedTitle = title
            reply.embbedContents = [CalculatorManager.dumpToPrint(toPrint)]
            reply.responseForAI = str({"efficiencies":jsonForAI})

        elif toPrintTarget is CalculatorManager.ToPrint.CCLIST:
            #契約賞金引換証
            CCLIST_FILENAME = "CCList.xlsx"
            Price_CC = getCCList()
            title = f"契約賞金引換効率(CC#{CalculatorManager.CC_NUMBER})"
            def efficiency(x:CCExchangeItem):
                return riseiValues.getValueFromZH(x.name)/x.value
            sorted_PriceCC = sorted(Price_CC,key = efficiency,reverse=True)
            ticket_efficiency_CC_sorted = [(x.fullname(),(efficiency(x),riseiValues.getStdDevFromZH(x.name)/x.value)) for x in sorted_PriceCC]
            toPrint = [["{0}: {1:.3f} ± {2:.3f}".format(CalculatorManager.left(18,name),value[0],value[1]*2)] for name,value in ticket_efficiency_CC_sorted]
            jsonForAI = {key:round(value[0],3) for key,value in ticket_efficiency_CC_sorted}

            reply.embbedTitle = title
            reply.embbedContents = [CalculatorManager.dumpToPrint(toPrint)]
            reply.responseForAI = str({"efficiencies":jsonForAI})

            if toCsv:
                columns = ["素材名","値段","在庫","交換効率"]
                rows = [[ItemIdToName.zhToJa(x.name),x.value,x.quantity,efficiency(x)]for x in sorted_PriceCC]
                df = pd.DataFrame(rows,columns=columns)
                df.to_excel(CCLIST_FILENAME)
                reply.attatchments = [CCLIST_FILENAME]
        elif toPrintTarget is CalculatorManager.ToPrint.POLIST:
            #結晶交換所効率
            POLIST_FILENAME = "POList.xlsx"
            Price_PO = getPOList()
            title = f"結晶交換所効率(Pinch Out)"
            def efficiency(x:CCExchangeItem):
                return riseiValues.getValueFromZH(x.name)/x.value
            sorted_PricePO = sorted(Price_PO,key = efficiency,reverse=True)
            ticket_efficiency_PO_sorted = [(x.fullname(),(efficiency(x),riseiValues.getStdDevFromZH(x.name)/x.value)) for x in sorted_PricePO]
            toPrint = [["{0}: {1:.3f} ± {2:.3f}".format(CalculatorManager.left(18,name),value[0],value[1]*2)] for name,value in ticket_efficiency_PO_sorted]
            jsonForAI = {key:round(value[0],3) for key,value in ticket_efficiency_PO_sorted}

            reply.embbedTitle = title
            reply.embbedContents = [CalculatorManager.dumpToPrint(toPrint)]
            reply.responseForAI = str({"efficiencies":jsonForAI})

            if toCsv:
                columns = ["素材名","値段","在庫","交換効率"]
                rows = [[ItemIdToName.zhToJa(x.name),x.value,x.quantity,efficiency(x)]for x in sorted_PricePO]
                df = pd.DataFrame(rows,columns=columns)
                df.to_excel(POLIST_FILENAME)
                reply.attatchments = [POLIST_FILENAME]
        if(reply.embbedContents):
            if toCsv and not reply.attatchments:
                calculator.dumpToFile(mode)
                reply.attatchments = [EXCEL_FILENAME]
            reply.plainText = calculator.getUpdatedTimeStr()
            return reply
        return RCReply(
            embbedTitle="エラー",
            embbedContents=["未知のコマンド："+str(toPrintTarget)],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: command not found: {toPrintTarget}"
        )

    #課金パック効率モジュール
    #課金パック情報
    class KakinPack:
        def __init__(self,name:str,priceAndContents:Dict[str,Union[float,Dict[str,float]]],riseiValues:RiseiOrTimeValues):
            self.name = name
            self.price = priceAndContents["price"]
            self.isConstant = priceAndContents["isConstant"]
            self.array = itemArray.ItemArray.fromJaCountDict(priceAndContents["contents"])
            self.totalValue = riseiValues.getValueFromItemArray(self.array)
            self.totalOriginium = self.totalValue / riseiValues.getValueFromJa('純正源石')
            self.isGlobal = riseiValues.isGlobal
            basicPackName = "10000円恒常パック" if self.isGlobal else "648元源石"
            basicPrice = getKakinList(self.isGlobal)[basicPackName]["price"]
            basicArray = itemArray.ItemArray.fromJaCountDict(getKakinList(self.isGlobal)[basicPackName]["contents"])
            basicValue = riseiValues.getValueFromItemArray(basicArray)
            self.totalRealMoney = self.totalValue / basicValue * basicPrice
            self.totalEfficiency = self.totalRealMoney / self.price
            self.gachaCount = self.array.getGachaCount()
            basicGachaCount = basicArray.getGachaCount()
            self.gachaEfficiency = self.gachaCount / self.price * basicPrice / basicGachaCount
            moneyUnit = '円' if self.isGlobal else '元'
            self.targetValueDict = {
                "総合効率    " : f"{self.totalEfficiency:.2%}",
                "ガチャ効率  " : f"{self.gachaEfficiency:.2%}",
                "パック値段  " : f"{self.price:.0f}{moneyUnit}",
                "合計理性価値" : f"{self.totalValue:.2f}",
                "純正源石換算" : f"{self.totalOriginium:.2f}",
                "マネー換算  " : f"{self.totalRealMoney:.2f}{moneyUnit}",
                "ガチャ数    " : f"{round(self.gachaCount,2)}"
            }

        def strBlock(self):
            return "```\n" +\
                "\n".join([f"{key}: {value}" for key,value in self.targetValueDict.items()]) +\
                "```\n"
        
        def contentsStrBlock(self):
            return "```\n" +\
                "\n".join([f"{name} × {count}" for name,count in self.array.toNameCountDict().items()]) +\
                "```\n"
        
        def toCountArrayFromColumnJaNameList(self,columns:List[str])->np.ndarray:
            return np.array([self.array.getByJa(name) for name in columns])
        
        def targetNameList(self)->List[str]:
            return [key.strip() for key in self.targetValueDict.keys()]
        
        def targetValueList(self) -> List[float]:
            return [self.totalEfficiency,self.gachaEfficiency,
                    self.price,self.totalValue,
                    self.totalOriginium,self.totalRealMoney,
                    self.gachaCount]
        
        def toJsonForAI(self):
            return {
                "name":self.name,
                "totalEfficiency":self.totalEfficiency,
                "gachaEfficiency":self.gachaEfficiency,
                "price":f"{self.price} yen" if self.isGlobal else f"{self.price} RMB",
                "contents":self.array.toNameCountDict()
            }
    
    def autoCompletion_riseikakin(current:str,limit:int=25)->List[Tuple[str,str]]:
        totalCommandList = [("全体比較(グローバル)","Total_Global"),("全体比較(大陸版)","Total_Mainland")]
        nameList = [(name,name) for name,value in getKakinList(True).items() if not value["isConstant"]]
        nameList += [(name,name) for name,value in getKakinList(False).items() if not value["isConstant"]]
        ret = [item for item in totalCommandList+nameList if current in item[0]][:limit]
        if(ret): return ret
        constantNameList = [(name,name) for name,value in getKakinList(True).items() if value["isConstant"]] +\
            [(name,name) for name,value in getKakinList(False).items() if value["isConstant"]]
        ret = [item for item in constantNameList if current in item[0]][:limit]
        return ret
    
    def riseikakin(toPrintTarget:str,baseMinTimes:int = 3000, cache_minutes:float = DEFAULT_CACHE_TIME, toCsv:bool = False) -> RCReply:
        #グローバル状態を計算
        KAKIN_FILENAME = "kakinList.xlsx"
        isGlobal:bool = ...
        totalJATuple = ("全体比較(グローバル)","Total_Global")
        totalCNTuple = ("全体比較(大陸版)","Total_Mainland")
        if(toPrintTarget in totalJATuple):
            isGlobal = True
        elif(toPrintTarget in totalCNTuple):
            isGlobal = False
        elif(toPrintTarget in getKakinList(True).keys()):
            isGlobal = True
        elif(toPrintTarget in getKakinList(False).keys()):
            isGlobal = False
        else:
            return RCReply(
                embbedTitle="エラー",
                embbedContents=["存在しない課金パック："+toPrintTarget],
                msgType=RCMsgType.ERR,
                responseForAI=f"Error: The purchase pack is not found: {toPrintTarget}"
            )

        riseiValues:RiseiOrTimeValues = CalculatorManager.getValues(isGlobal,CalculateMode.SANITY,baseMinTimes,cache_minutes)
        calculator:Calculator = CalculatorManager.selectCalculator(isGlobal)
        kakinList = getKakinList(isGlobal)
        #比較用
        constantList = [CalculatorManager.KakinPack(key,value,riseiValues) for key,value in kakinList.items() if value["isConstant"]]
        constantStrBlock = "参考用課金効率:```\n" +\
            "\n".join([f"{pack.name}: {pack.totalEfficiency:.2%}" for pack in constantList]) +\
            "```"
        msgList = []
        title:str = ...
        file:str = None
        def getMaterialSet(packList:List[CalculatorManager.KakinPack])->List[str]:
            materialSet = []
            for item in packList:
                materialSet += list(item.array.toNameCountDict().keys())
                materialSet = list(set(materialSet))
            return materialSet
        
        def listToCSV(packList:List[CalculatorManager.KakinPack]):
            materialSet = getMaterialSet(packList)
            columns = materialSet + packList[0].targetNameList()
            index = [item.name for item in packList] + ["理性価値"]
            data = np.array([item.array.getByJaList(materialSet) for item in packList] + [riseiValues.getValueFromJaList(materialSet)])
            valueData = np.array([item.targetValueList() for item in packList]+[[None for _ in packList[0].targetNameList()]])
            data = np.concatenate([data,valueData],1)
            df = pd.DataFrame(data,index=index,columns=columns)
            df.to_excel(KAKIN_FILENAME)
            return KAKIN_FILENAME

        jsonForAI:List|Dict = ...
        if toPrintTarget in totalJATuple or toPrintTarget in totalCNTuple:
            title = "課金パック比較"
            #限定パックの情報表示
            limitedList = [CalculatorManager.KakinPack(key,value,riseiValues) for key,value in kakinList.items() if not value["isConstant"]]
            sortedList = list(sorted(limitedList,key=lambda x: x.totalEfficiency,reverse=True))
            for item in sortedList:
                msgList.append(f"{item.name}:{item.strBlock()}")
            msgList.append(constantStrBlock)
            jsonForAI = [item.toJsonForAI() for item in sortedList]
            if toCsv:
                #CSV出力をする
                file = listToCSV(sortedList + constantList)
        else:
            kakinPack = CalculatorManager.KakinPack(toPrintTarget,kakinList[toPrintTarget],riseiValues)
            title = kakinPack.name
            msgList.append(f"内容物:" + kakinPack.contentsStrBlock())
            msgList.append(f"理性価値情報:" + kakinPack.strBlock())
            msgList.append(constantStrBlock)
            jsonForAI = kakinPack.toJsonForAI()
            if toCsv:
                file = listToCSV([kakinPack] + constantList)
        attatchments = [file] if file is not None else []

        return RCReply(
            plainText=calculator.getUpdatedTimeStr(),
            embbedTitle=title,
            embbedContents=msgList,
            attatchments=attatchments,
            responseForAI=str(jsonForAI)
        )
