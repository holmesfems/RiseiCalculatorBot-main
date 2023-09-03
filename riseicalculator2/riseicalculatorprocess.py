import numpy as np
import numpy.linalg as LA
import sys
sys.path.append('../')
from idtoname.idtoname import ItemIdToName,ZoneIdToName
from rcutils import netutil,getnow,hasduplicates
import re
import pandas as pd
import re
import math
import datetime
import random
from io import StringIO
import unicodedata
from collections import ChainMap
import yaml
from typing import Dict,List,Optional,Tuple
from enum import Enum,StrEnum
import enum

PENGUIN_URL = 'https://penguin-stats.io/PenguinStats/api/v2/'
headers = {'User-Agent':'ArkPlanner'}
def get_json(s,AdditionalReq=None):
    return netutil.get_json(PENGUIN_URL+s,AdditionalReq,headers)

#初級&上級資格証
Price = dict()
with open('riseicalculator2/price.txt', 'r', encoding='utf8') as f:
    for line in f.readlines():
        name, value = line.split()
        Price[name] = int(value)

#特別引換証
Price_Special = dict()
with open('riseicalculator2/price_special.txt', 'r', encoding='utf8') as f:
    for line in f.readlines():
        name, value = line.split()
        Price_Special[name] = float(value)

Item_rarity2:List[str] = [
    '固源岩组','全新装置','聚酸酯组', 
    '糖组','异铁组','酮凝集组',
    '扭转醇','轻锰矿','研磨石',
    'RMA70-12','凝胶','炽合金',
    '晶体元件','半自然溶剂','化合切削液',
    '转质盐组'
]

Item_rarity2_new:List[str] = [
    
]

Item_rarity3:List[str] = [
    '提纯源岩','改量装置','聚酸酯块', 
    '糖聚块','异铁块','酮阵列', 
    '白马醇','三水锰矿','五水研磨石',
    'RMA70-24','聚合凝胶','炽合金块',
    '晶体电路','精炼溶剂','切削原液',
    '转质盐聚块'
]

Item_rarity3_new:List[str] = [
    
]

ValueTarget:List[str] = [
    '基础作战记录', '初级作战记录', '中级作战记录', '高级作战记录', 
    '赤金','龙门币1000',
    '源岩', '固源岩', '固源岩组', '提纯源岩', 
    '破损装置', '装置', '全新装置', '改量装置', 
    '酯原料', '聚酸酯', '聚酸酯组', '聚酸酯块', 
    '代糖', '糖', '糖组', '糖聚块', 
    '异铁碎片', '异铁', '异铁组', '异铁块', 
    '双酮', '酮凝集', '酮凝集组', '酮阵列', 
    '扭转醇', '白马醇',
    '轻锰矿', '三水锰矿',
    '研磨石', '五水研磨石',
    'RMA70-12', 'RMA70-24',
    '凝胶', '聚合凝胶',
    '炽合金', '炽合金块',
    '晶体元件', '晶体电路',
    '半自然溶剂','精炼溶剂',
    '化合切削液','切削原液',
    '转质盐组','转质盐聚块','烧结核凝晶',
    '聚合剂', '双极纳米片', 'D32钢','晶体电子单元',
    '技巧概要·卷1', '技巧概要·卷2', '技巧概要·卷3',
]

ValueTarget_new:List[str] = [
    
]

#ドロップアイテム&ステージのカテゴリ情報を入手
with open("riseicalculator2/StageCategoryDict.json","rb") as file:
    StageCategoryDict = yaml.safe_load(file)

#一部理論値と実際のクリア時間が乖離しているステージで個別修正
with open("riseicalculator2/minClearTimeInjection.json","r") as file:
    minClearTimeInjection = yaml.safe_load(file)

#大陸版実装済み、グロ版未実装のステージまとめ 実装次第削除してOK
new_zone:List[str] = [
#    'main_11', #11章
    'main_12', #12章
    'permanent_sidestory_13_zone1', #GA
    'permanent_sidestory_14_zone1', #LE
    'permanent_sidestory_15_zone1', #DV
    'permanent_sub_5_zone1', #CW
]

#大陸版基準、グロ版基準調整用
def getGlobalOrMainland(ParamName,glob:bool):
    if glob:
        return eval(ParamName)
    else:
        return eval(ParamName) + eval(ParamName+'_new')

def getItemRarity2(glob:bool) -> List[str]:
    return getGlobalOrMainland("Item_rarity2",glob)

def getItemRarity3(glob:bool) -> List[str]:
    return getGlobalOrMainland("Item_rarity3",glob)

def getValueTarget(glob:bool) -> List[str]:
    return getGlobalOrMainland("ValueTarget",glob)

def getStageCategoryDict(glob:bool):
    if glob:
        return StageCategoryDict["main"]
    else:
        return ChainMap(StageCategoryDict["main"],StageCategoryDict["new"])

def valueTargetZHToJA(zhStr:str) -> str:
    specialDict = {'龙门币1000':"龍門幣1000"}
    return specialDict.get(zhStr,ItemIdToName.zhToJa(zhStr))

def valueTargetIndexOf(zhStr:str,glob:bool) -> int:
    try:
        return getValueTarget(glob).index(zhStr)
    except ValueError:
        return -1

def idInValueTarget(id:str,glob:bool) -> bool:
    valueTarget = getValueTarget(glob)
    zhStr = ItemIdToName.getZH(id)
    return zhStr in valueTarget

def categoryZHToJA(zhStr:str,glob:bool) -> bool:
    categoryDict = getStageCategoryDict(glob)
    return categoryDict[zhStr]["to_ja"]

class CalculateMode(Enum):
    SANITY = enum.auto()
    TIME = enum.auto()
    def __str__(self) -> str:
        if self is CalculateMode.SANITY:
            return "理性"
        else:
            return "時間"

class DropItem:
    def __init__(self,dropRate,times):
        self.dropRate = dropRate
        self.times = times
    
    def __repr__(self) -> str:
        return str(self.dropRate)

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
    
    def __iadd__(self,other):
        #ドロップアイテムの加算
        for key,value in other.dropDict.items():
            #重複要素は登録しない
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
    def toDropArray(self, isGlobal) -> np.ndarray:
        dropRateList = []
        for item in getValueTarget(isGlobal):
            id = ItemIdToName.zhToId(item)
            dropRate = self.dropDict.get(id,DropItem(0,0)).dropRate
            dropRateList.append(dropRate)
        return np.array(dropRateList)

    def toTimesArray(self,isGlobal) -> np.ndarray:
        timesList = []
        for item in getValueTarget(isGlobal):
            id = ItemIdToName.zhToId(item)
            times = self.dropDict.get(id,DropItem(0,2)).times
            timesList.append(times)
        return np.array(timesList)
    
    def toStdDevArray(self,isGlobal) -> np.ndarray:
        dropArray = self.toDropArray(isGlobal)
        extra = dropArray%1.0
        timesArray = self.toTimesArray(isGlobal)-1
        return (extra*(1.0-extra)/timesArray)**0.5
    
    def getDropItem(self, zhStr) -> DropItem:
        return self.dropDict.get(zhStr,DropItem(0,0))
    
    def maxTimes(self):
        return self.__maxtimes
    def minTimes(self):
        return self.__mintimes
    
class RiseiOrTimeValues:
    def __init__(self,valueArray:np.ndarray,isGlobal:bool,mode:CalculateMode):
        self.isGlobal = isGlobal
        self.valueArray = valueArray
        self.mode = mode
        self.devArray = np.zeros(len(valueArray))

    def __repr__(self) -> str:
        nameDict = self.toNameDict()
        devDict = self.toNameDictStdDev()
        valueTarget = getValueTarget(self.isGlobal)
        jaValueTarget = [valueTargetZHToJA(x) for x in valueTarget]
        return "\n".join([x+" : "+"{0:.3f} ± {1:.4f}".format(nameDict[x],devDict[x]*2) for x in jaValueTarget])

    def toNameDict(self) -> Dict[str,float]:
        valueTarget = getValueTarget(self.isGlobal)
        return {valueTargetZHToJA(valueTarget[i]):self.valueArray[i] for i in range(len(valueTarget))}
    
    def toNameDictStdDev(self) -> Dict[str,float]:
        valueTarget = getValueTarget(self.isGlobal)
        return {valueTargetZHToJA(valueTarget[i]):self.devArray[i] for i in range(len(valueTarget))}
    

    def getValueFromZH(self,zhstr:str) -> float:
        index = valueTargetIndexOf(zhstr,self.isGlobal)
        return self.valueArray[index]
    
    def getValueFromCode(self,codeStr:str) -> float:
        zhstr = ItemIdToName.getZH(codeStr)
        return self.getValueFromZH(zhstr)
    
    def getStdDevFromZH(self,zhstr:str) -> float:
        index = valueTargetIndexOf(zhstr,self.isGlobal)
        return self.devArray[index]

    def setDevArray(self,stdDevArray:np.ndarray):
        self.devArray = stdDevArray


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
        if(minClearTime == None): minClearTime = 0
        self.minClearTime = minClearTimeInjection.get(self.name,minClearTime/1000) #等倍秒
        #ドロップリストを記録する
        self.dropList = DropList()
        self.mainDropIds = [x["itemId"] for x in dictItem.get("dropInfos",[]) if x["dropType"] == "NORMAL_DROP" and "itemId" in x.keys()]
    
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
    
    def getDropRate(self,zhStr,isGlobal) -> float:
        index = valueTargetIndexOf(zhStr,isGlobal)
        return self.toDropArray(isGlobal)[index]
    
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
        stdev = self.toStdDevArray(riseiValue.isGlobal)
        dev1 = np.dot(stdev**2,riseiValue.valueArray**2)
        dev2 = np.dot(self.toDropArray(riseiValue.isGlobal)**2,riseiValue.devArray**2)
        dev = dev1 + dev2
        return dev ** 0.5

    def getMaxEfficiencyItem(self,riseiValue:RiseiOrTimeValues) -> Tuple[str,float]:
        maxKey,dropRate,value = max([(key,value.dropRate,value.dropRate*riseiValue.getValueFromCode(key))for key,value in self.dropList.dropDict.items()],key = lambda x:x[1])
        return (ItemIdToName.getStr(maxKey),dropRate)

    def __repr__(self) -> str:
        ret = self.name
        if "re_" in self.zoneId:
            ret += "(Re)"
        #print(self.maxTimes())
        return ret

class StageInfo:
    def __init__(self,isGlobal,validBaseMinTimes:int):
        self.isGlobal = isGlobal
        self.validBaseMinTimes = validBaseMinTimes
        self.mainStageDict = {}
        self.eventStageDict = {}
        self.mainCodeToStageDict = {}
        self.eventCodeToStageDict = {}
        self.lastUpdated = None
        self.init()
    #ステージ情報更新できるように外から呼び出せるようにする
    def init(self):
        allStageList = get_json("stages")
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
        def createStageDict(stageList):
            return {x["stageId"]:StageItem(x) for x in stageList}
        
        self.mainStageDict = createStageDict(mainStageList)
        self.eventStageDict = createStageDict(eventStageList)

        #作戦コードから逆引きする辞書を作成
        def createCodeToStageDict(stageDict):
            codeToStage = {}
            for value in stageDict.values():
                codeToStage[str(value)] = value
            return codeToStage
        self.mainCodeToStageDict = createCodeToStageDict(self.mainStageDict)
        self.eventCodeToStageDict = createCodeToStageDict(self.eventStageDict)

        #matrix代入, targetServerはCNで固定
        additionalHeader = {"server":"CN","show_closed_zones":"true"}
        matrix = get_json('result/matrix',additionalHeader)["matrix"] #一回目ここで死んでる
        allStageDict = {**self.mainStageDict,**self.eventStageDict}
        for item in matrix:
            key = item["stageId"]
            stageItem = allStageDict.get(key)
            if not stageItem: continue
            stageItem.addDropList(item,self.isGlobal)
        
        #カテゴリ辞書の作成
        categoryDict = getStageCategoryDict(self.isGlobal)
        self.categoryDict ={}
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
        self.lastUpdated = getnow.getnow()

    def validBaseStages(self) -> List[StageItem]:
        return [x for x in self.mainStageDict.values() if x.maxTimes() >= self.validBaseMinTimes]

    def categoryValidStages(self,category:str)->List[StageItem]:
        allStageList:List[StageItem] = self.categoryDict[category]["Stages"]
        validStageList:List[StageItem] = [x for x in allStageList if x.maxTimes() >= self.validBaseMinTimes]
        return validStageList
    
    def stageToCategory(self,stage:StageItem) -> List[str]:
        return [key for key,value in self.categoryDict.items() if stage in value["Stages"]]
    
    #全ステージの効率を計算し、最大効率のカテゴリを取得
    class CategoryMaxEfficiencyItem:
        def __init__(self,maxValue:float,stage:StageItem,categories:List[str]):
            self.maxValue = maxValue
            self.stage = stage
            self.categories = categories

    def getCategoryMaxEfficiency(self,values:RiseiOrTimeValues)->CategoryMaxEfficiencyItem:
        validStageList = self.validBaseStages()
        efficiencyAndStages:List[Tuple[float,StageItem]]  = [(x.getEfficiency(values),x) for x in validStageList]
        maxValue,maxStage = max(efficiencyAndStages,key= lambda x: x[0])
        maxCategories = self.stageToCategory(maxStage)
        return StageInfo.CategoryMaxEfficiencyItem(maxValue,maxStage,maxCategories)

    def generateCategorySeed(self) -> Dict[str,StageItem]:
        ret:Dict[str,StageItem] = {}
        for key in self.categoryDict.keys():
            validStageList = self.categoryValidStages(key)
            randomChoiced = random.choice(validStageList)
            ret[key] = randomChoiced
        if hasduplicates.has_duplicates(ret.values()):
            return self.generateCategorySeed() #重複要素があればやり直し
        return ret

    def __repr__(self) -> str:
        return "Main:" + str(self.mainStageDict.values()) + "\n" + "Event:" + str(self.eventStageDict.values())

class Calculator:
    def __init__(self,isGlobal:bool,doInit:bool):
        self.isGlobal:bool = isGlobal
        self.initialized = False
        if(doInit):
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
            formula = get_json('formula')
            for formulaItem in formula:
                if formulaItem["name"] not in getValueTarget(isGlobal):
                    continue
                item = Calculator.ConvertionItem(isGlobal,"合成-"+ItemIdToName.getStr(formulaItem["id"]))
                item.setValue({
                    formulaItem["name"]:-1,
                    "龙门币1000":formulaItem["goldCost"]/1000,
                    **{
                        costItem["name"]:costItem["count"] for costItem in formulaItem["costs"]
                    }
                })
                #副産物を考慮
                exOutcome:List[Tuple[str,float]] = [(x["name"],x["weight"]) for x in formulaItem["extraOutcome"] if x["name"] in getValueTarget(isGlobal)]
                totalweight = sum([x[1] for x in exOutcome])
                exOutcomeDict:Dict[str,float] = {x[0]:-x[1]/totalweight*convertionDropRate for x in exOutcome}
                item.addValue(exOutcomeDict)
                convertionItemList.append(item)
            
            # 本の合成
            # 技1*3=技2
            item = Calculator.ConvertionItem(isGlobal,"スキル本換算1")
            item.setValue({
                "技巧概要·卷1":3,
                "技巧概要·卷2":-1-convertionDropRate
            })
            convertionItemList.append(item)

            item = Calculator.ConvertionItem(isGlobal,"スキル本換算2")
            item.setValue({
                "技巧概要·卷2":3,
                "技巧概要·卷3":-1-convertionDropRate
            })
            convertionItemList.append(item)
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

        
    #作戦記録、龍門幣、本のステージドロップ
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
        def __init__(self,isGlobal:bool,stageInfo:StageInfo) -> None:
            self.isGlobal = isGlobal
            self.stageInfo = stageInfo
            self.baseStageItemDict:Dict[str,Calculator.BaseStageDropItem] = {}
            #初期化　ランダムにseed生成
            seed = self.stageInfo.generateCategorySeed()
            self.initBaseStages(seed)
            self.epsilon = 0.00001

        def initBaseStages(self,seed:Dict[str,StageItem]):
            self.baseStageItemDict = {key:Calculator.BaseStageDropItem(self.isGlobal,key,value) for key,value in seed.items()}

        def getMatrix(self):
            return np.array([x.stageItem.toDropArray(self.isGlobal) for x in self.baseStageItemDict.values()])
        
        def getCostArray(self,mode:CalculateMode):
            return np.array([x.stageItem.apCost if mode is CalculateMode.SANITY else x.stageItem.minClearTime for x in self.baseStageItemDict.values()])
        
        def getStdDevMatrix(self):
            return np.array([x.stageItem.toStdDevArray(self.isGlobal) for x in self.baseStageItemDict.values()])
        
        def __repr__(self) -> str:
            return str({categoryZHToJA(key,self.isGlobal):value.stageItem.name for key,value in self.baseStageItemDict.items()})
        
        def update(self,values:RiseiOrTimeValues) -> bool:
            mode = values.mode
            maxEfficiencyItem = self.stageInfo.getCategoryMaxEfficiency(values)
            if not maxEfficiencyItem.categories:
                msg = "カテゴリから外れたマップを検出、計算を中断します\n"
                msg += "マップ" + maxEfficiencyItem.stage.name + "は、何を稼ぐステージですか？\n"
                raise Exception(msg)
            if maxEfficiencyItem.maxValue <= 1.0 + self.epsilon:
                return False #続けて更新しなくてよい
            targetCategory = random.choice(maxEfficiencyItem.categories)
            print(targetCategory,":",maxEfficiencyItem.stage.name,"=",maxEfficiencyItem.maxValue,"基準マップ差し替え実行")
            self.baseStageItemDict[targetCategory] = Calculator.BaseStageDropItem(self.isGlobal,targetCategory,maxEfficiencyItem.stage)
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
        divMatrix = self.getDevMatrix(mode)
        divArray = np.dot(np.dot(probMatrixInv**2,divMatrix**2),values.valueArray**2)**0.5
        values.setDevArray(divArray)
        return values

    def init(self,validBaseMinTimes:int=3000):
        self.stageInfo = StageInfo(self.isGlobal,validBaseMinTimes)
        self.convertionMatrix = Calculator.ConvertionMatrix(self.isGlobal)
        self.constStageMatrix = Calculator.ConstStageMatrix(self.isGlobal)
        self.calculate()
        self.initialized = True
    
    def calculate(self):
        self.baseStageMatrixForSanity = Calculator.BaseStageMatrix(self.isGlobal,self.stageInfo)
        self.baseStageMatrixForTime = Calculator.BaseStageMatrix(self.isGlobal,self.stageInfo)
        self.riseiValues = self.solveOptimizedValue(CalculateMode.SANITY)
        self.timeValues = self.solveOptimizedValue(CalculateMode.TIME)
        
    def tryRecalculate(self,validBaseMinTimes:int):
        if validBaseMinTimes != self.stageInfo.validBaseMinTimes:
            self.calculate()

    def getValues(self,mode:CalculateMode) -> RiseiOrTimeValues:
        if mode is CalculateMode.SANITY: return self.riseiValues
        return self.timeValues

    #ステージ情報が古ければ更新する。期限は外部からの指定、指定しない場合は強制更新
    def tryReInit(self,timeDiff:Optional[datetime.timedelta],validBaseMinTimes:Optional[int]) -> bool:
        now = getnow.getnow()
        if self.initialized and timeDiff and now < self.stageInfo.lastUpdated+timeDiff:
            if validBaseMinTimes != self.stageInfo.validBaseMinTimes:
                self.calculate()
                return True
            return False
        if self.initialized:
            baseMinTimes = validBaseMinTimes if validBaseMinTimes else self.stageInfo.validBaseMinTimes
            self.init(baseMinTimes)
        elif validBaseMinTimes:
            self.init(validBaseMinTimes)
        else:
            self.init()
        return True

    def searchMainStage(self,targetCode:str) -> List[StageItem]:
        return [value for key,value in self.stageInfo.mainCodeToStageDict.items() if key.startswith(targetCode)]
    
    def autoCompleteMainStage(self,targetCode:str,limit:int=25) -> List[str]:
        return [str(x) for x in self.searchMainStage(targetCode)][:limit]
    
    def searchEventStage(self,targetCode:str) -> List[StageItem]:
        return [value for key,value in self.stageInfo.eventCodeToStageDict.items() if key.startswith(targetCode)]
    
    def autoCompleteEventStage(self,targetCode:str,limit:int=25) -> List[str]:
        return [str(x) for x in self.searchEventStage(targetCode)][:limit]
    
    def getStageDev(self,targetStage:StageItem,values:RiseiOrTimeValues) -> float:
        baseMatrix = self.getBaseStageMatrix(values.mode)
        if(baseMatrix.contains(targetStage)): return 0
        return targetStage.getStdDev(values)
    
    def dumpToFile(self,mode:CalculateMode):
        columnsName = [valueTargetZHToJA(x) for x in getValueTarget(self.isGlobal)] + ['理性消費']
        baseMatrix = self.getBaseStageMatrix(mode)
        rowsName = self.convertionMatrix.getRowsName() + self.constStageMatrix.getRowsName() + baseMatrix.getRowsName() + ["理性価値"]
        probMatrix = self.getProbMatrix(mode)
        values = self.getValues(mode).valueArray
        costs = self.getCostArray(mode)
        mainData = np.vstack((probMatrix,values))
        mainData = np.hstack((mainData,np.concatenate([costs,[0]]).reshape(-1,1)))
        df = pd.DataFrame(mainData,columns=columnsName,index=rowsName)
        df.to_excel('BaseStages.xlsx')
        print("基準マップデータをBaseStages.xlsxに保存しました")

class CalculatorManager:
    calculatorForGlobal = Calculator(True,True)
    calculatorForMainland = Calculator(False,True)

    def selectCalculator(isGlobal:bool):
        return CalculatorManager.calculatorForGlobal if isGlobal else CalculatorManager.calculatorForMainland
    
    def setCalculator(isGlobal:bool,newCalculator:Calculator):
        if isGlobal:
            CalculatorManager.calculatorForGlobal = newCalculator
        else:
            CalculatorManager.calculatorForMainland = newCalculator

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

    def getValues(isGlobal:bool,mode:CalculateMode,baseMinTimes:int = 3000, cache_minutes:float = 30) -> RiseiOrTimeValues:
        calculator = CalculatorManager.selectCalculator(isGlobal)
        if (calculator == None):
            calculator = Calculator(isGlobal,False) 
            CalculatorManager.setCalculator(isGlobal,calculator)
        calculator.tryReInit(CalculatorManager.__getTimeDelta(cache_minutes),baseMinTimes)
        return calculator.getValues(mode)
    
    def filterStagesByShowMinTimes(stageList:List[StageItem],showMinTimes):
        return [x for x in stageList if x.maxTimes() >= showMinTimes]

    def dumpToPrint(toPrint):
        return "```" + "\n".join(["".join(x) for x in toPrint]) + "```"
    
    def left(digit, msg):
        for c in msg:
            if unicodedata.east_asian_width(c) in ('F', 'W', 'A'):
                digit -= 2
            else:
                digit -= 1
        return msg + ' '*digit

    def sortStagesByEfficiency(stageList:List[StageItem],riseiValues:RiseiOrTimeValues):
        return sorted(stageList,key = lambda x: x.getEfficiency(riseiValues),reverse=True)

    def riseimaterials(targetCategory:str,isGlobal:bool,mode:CalculateMode,baseMinTimes:int = 3000, cache_minutes:float = 30,showMinTimes:int = 1000,maxItems:int = 15):
        riseiValues = CalculatorManager.getValues(isGlobal,mode,baseMinTimes,cache_minutes)
        #print(riseiValue)
        calculator = CalculatorManager.selectCalculator(isGlobal)
        categoryValue = calculator.stageInfo.categoryDict.get(targetCategory)
        if not categoryValue:
            return {
                "title":"昇進素材検索",
                "msgList":["無効なカテゴリ:" + targetCategory]
            }
        stages = categoryValue["Stages"]
        stagesToShow = CalculatorManager.filterStagesByShowMinTimes(stages,showMinTimes)
        msgHeader = categoryValue["to_ja"]+ ": 理性価値(中級)={0:.3f}±{1:.3f}\n".format(riseiValues.getValueFromZH(categoryValue["MainItem"]),riseiValues.getStdDevFromZH(categoryValue["MainItem"]))
        msgChunks = [msgHeader]
        #並び変え
        stagesToShow = CalculatorManager.sortStagesByEfficiency(stagesToShow,riseiValues)
        cnt = 0
        for stage in stagesToShow:
            cnt += 1
            toPrint = [
                ["マップ名       : ",stage.name],
                ["{1}効率       : {0:.1f}%".format(100*stage.getEfficiency(riseiValues),str(mode))],
                ["理性消費       : ",str(stage.apCost)]
            ]
            if stage.minClearTime > 0:
                dropValues = stage.getDropRate(categoryValue["MainItem"],isGlobal)
                for item,order in zip(categoryValue["SubItem"],categoryValue["SubOrder"]):
                    dropValues += stage.getDropRate(item,isGlobal)/order
                dropPerMin = dropValues/stage.minClearTime*120
                toPrint += [
                    ["時間消費(倍速) : ", str(stage.minClearTime/2.0)],
                    ["分入手数(中級) : {0:.2f}".format(dropPerMin)],
                ]
            toPrint += [
                ["主素材効率     : {0:.1f}%".format(100*stage.getPartialEfficiency(riseiValues,categoryValue["Items"]))],
                ["95%信頼区間(2σ): {0:.1f}%".format(100*calculator.getStageDev(stage,riseiValues))],
                ["昇進効率       : {0:.1f}%".format(100*stage.getPartialEfficiency(riseiValues,getValueTarget(isGlobal)[4:]))],
                ["試行数         : ",str(stage.maxTimes())],
            ]
            #print(toPrint)

            msgChunks.append(CalculatorManager.dumpToPrint(toPrint))
            if maxItems > 0 and cnt >= maxItems:
                break
        return {
            "title":"昇進素材検索",
            "msgList":msgChunks
        }

    def riseistages(targetStage:str,isGlobal:bool,mode:CalculateMode,baseMinTimes:int = 3000, cache_minutes:float = 30,showMinTimes:int = 1000,maxItems:int = 15):
        riseiValues = CalculatorManager.getValues(isGlobal,mode,baseMinTimes,cache_minutes)
        calculator = CalculatorManager.selectCalculator(isGlobal)
        stages = calculator.searchMainStage(targetStage)
        stagesToShow = CalculatorManager.filterStagesByShowMinTimes(stages,showMinTimes)
        title = "通常ステージ検索"
        if(not stagesToShow):
            return {
                "title" : title,
                "msgList" : ["無効なステージ指定"+targetStage]
            }
        msgHeader = "検索内容 = " + targetStage
        #名前順でソート
        stagesToShow.sort(key = lambda x:x.name)
        msgChunks = [msgHeader]
        cnt = 0
        for stage in stagesToShow:
            cnt += 1
            toPrint = [
                ["マップ名       : ",stage.name],
                ["総合{1}効率    : {0:.1f}%".format(100*stage.getEfficiency(riseiValues),str(mode))],
                ["95%信頼区間(2σ): {0:.1f}%".format(100*calculator.getStageDev(stage,riseiValues))],
            ]
            dropCategoryList = calculator.stageInfo.stageToCategory(stage)
            if len(dropCategoryList) == 0:
                toPrint.append(["主ドロップ情報未登録"])
            else:
                for category in dropCategoryList:
                    categoryValue = calculator.stageInfo.categoryDict[category]
                    toPrint.append(["{0}: {1:.1f}%".format(CalculatorManager.left(15,categoryValue["to_ja"]+"効率"),
                        100*stage.getPartialEfficiency(riseiValues,categoryValue["Items"]))])
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
                ["昇進効率       : {0:.1f}%".format(100*stage.getPartialEfficiency(riseiValues,getValueTarget(isGlobal)[4:]))],
                ["試行数         : ",str(stage.maxTimes())],
            ]
            msgChunks.append(CalculatorManager.dumpToPrint(toPrint))
            if maxItems > 0 and cnt >= maxItems:
                break
        return {
            "title":title,
            "msgList":msgChunks
        }
    
    def riseievents(targetStage:str,isGlobal:bool,mode:CalculateMode,baseMinTimes:int = 3000, cache_minutes:float = 30,showMinTimes:int = 1000,maxItems:int = 15):
        riseiValues = CalculatorManager.getValues(isGlobal,mode,baseMinTimes,cache_minutes)
        calculator = CalculatorManager.selectCalculator(isGlobal)
        stages = calculator.searchEventStage(targetStage)
        #print(stages)
        stagesToShow = CalculatorManager.filterStagesByShowMinTimes(stages,showMinTimes)
        title = "イベントステージ検索"
        if(not stagesToShow):
            return {
                "title" : title,
                "msgList" : ["無効なステージ指定"+targetStage]
            }
        msgHeader = "検索内容 = " + targetStage
        #名前順でソート
        stagesToShow.sort(key = lambda x:x.name)
        msgChunks = [msgHeader]
        cnt = 0
        for stage in stagesToShow:
            cnt += 1
            maindrop, droprate = stage.getMaxEfficiencyItem(riseiValues)
            toPrint = [
                ["マップ名       : ",str(stage)],
                ["イベント名     : ",stage.zoneName],
                ["総合{1}効率   : {0:.1f}%".format(100*stage.getEfficiency(riseiValues),str(mode))],
                ["主ドロップ     : ",maindrop],
                ["ドロップ率     : {0:.2f}%".format(100*droprate)],
                ["試行数         : ",str(stage.maxTimes())],
                ["理性消費       : ",str(stage.apCost)],
            ]
            if stage.minClearTime > 0:
                toPrint += [
                    ["時間消費(倍速) : ", str(stage.minClearTime/2.0)],
                    ["分間入手数     : {0:.2f}".format(droprate/stage.minClearTime*120)],
                ]
            msgChunks.append(CalculatorManager.dumpToPrint(toPrint))
            if maxItems > 0 and cnt >= maxItems:
                break
        return {
            "title":title,
            "msgList":msgChunks
        }
    
    def riseilists(toPrintTarget:ToPrint,isGlobal:bool,mode:CalculateMode,baseMinTimes:int = 3000, cache_minutes:float = 30):
        riseiValues = CalculatorManager.getValues(isGlobal,mode,baseMinTimes,cache_minutes)
        calculator = CalculatorManager.selectCalculator(isGlobal)
        if toPrintTarget is CalculatorManager.ToPrint.BASEMAPS:
            baseMapStr = str(calculator.getBaseStageMatrix(mode))
            msg = "基準ステージ一覧:`{0}`".format(baseMapStr)
            return {
                "title" : "基準ステージ表示",
                "msgList": [msg]
            }
        elif toPrintTarget is CalculatorManager.ToPrint.SAN_VALUE_LISTS:
            title = "{0}価値一覧".format(str(mode))
            toPrint = []
            for key in getValueTarget(isGlobal):
                value = riseiValues.getValueFromZH(key)
                stddev = riseiValues.getValueFromZH(key)
                toPrint.append([
                    "{0}: {1:.3f} ± {2:.3f}".format(CalculatorManager.left(15,valueTargetZHToJA(key)),value,stddev*2)
                ])
            return {
                "title":title,
                "msgList" : [CalculatorManager.dumpToPrint(toPrint)]
            }
        elif toPrintTarget is CalculatorManager.ToPrint.TE2LIST:
            title = "初級資格証効率"
            ticket_efficiency2 = {ItemIdToName.zhToJa(x):(riseiValues.getValueFromZH(x)/Price[x],riseiValues.getStdDevFromZH(x)/Price[x]) for x in getItemRarity2(isGlobal)}
            toPrint = []
            ticket_efficiency2_sorted = sorted(ticket_efficiency2.items(),key = lambda x:x[1][0],reverse=True)
            for key,value in ticket_efficiency2_sorted:
                toPrint.append(["{0}:\t{1:.3f} ± {2:.3f}".format(CalculatorManager.left(15,key),value[0],value[1]*2)])
            return {
                "title":title,
                "msgList" : [CalculatorManager.dumpToPrint(toPrint)]
            }
        elif toPrintTarget is CalculatorManager.ToPrint.TE3LIST:
            title = "上級資格証効率"
            ticket_efficiency3 = {ItemIdToName.zhToJa(x):(riseiValues.getValueFromZH(x)/Price[x],riseiValues.getStdDevFromZH(x)/Price[x]) for x in getItemRarity3(isGlobal)}
            toPrint = []
            ticket_efficiency3_sorted = sorted(ticket_efficiency3.items(),key = lambda x:x[1][0],reverse=True)
            for key,value in ticket_efficiency3_sorted:
                toPrint.append(["{0}:\t{1:.3f} ± {2:.3f}".format(CalculatorManager.left(15,key),value[0],value[1]*2)])
            return {
                "title":title,
                "msgList" : [CalculatorManager.dumpToPrint(toPrint)]
            }
        elif toPrintTarget is CalculatorManager.ToPrint.SPECIAL_LIST:
            title = "特別引換証効率"
            ticket_efficiency_special = {ItemIdToName.zhToJa(x):(riseiValues.getValueFromZH(x)/Price_Special[x],riseiValues.getStdDevFromZH(x)/Price_Special[x]) for x in getItemRarity2(isGlobal)+getItemRarity3(isGlobal)}
            toPrint = []
            ticket_efficiency_special_sorted = sorted(ticket_efficiency_special.items(),key = lambda x:x[1][0],reverse=True)
            for key,value in ticket_efficiency_special_sorted:
                toPrint.append(["{0}:\t{1:.3f} ± {2:.3f}".format(CalculatorManager.left(15,key),value[0],value[1]*2)])
            return {
                "title":title,
                "msgList" : [CalculatorManager.dumpToPrint(toPrint)]
            }
        elif toPrintTarget is CalculatorManager.ToPrint.CCLIST:
            #契約賞金引換証
            ccNumber = '11'
            Price_CC = list()
            try:
                with open('price_cc{0}.txt'.format(ccNumber), 'r', encoding='utf8') as f:
                    for line in f.readlines():
                        name, value ,quantity = line.split()
                        Price_CC.append([name,float(value),quantity])
            except FileNotFoundError as e:
                return "CC#{0}の交換値段が未設定です！".format(ccNumber)
            title = "契約賞金引換効率(CC#{0})```".format(ccNumber)
            ticket_efficiency_CC = [(ItemIdToName.zhToJa(x[0]),(riseiValues.getValueFromZH(x[0])/x[1],riseiValues.getStdDevFromZH(x[0])/x[1]),x[2]) for x in Price_CC if x[0] in getValueTarget(isGlobal)]
            ticket_efficiency_CC_sorted = sorted(ticket_efficiency_CC,key = lambda x:x[1][0],reverse=True)
            toPrint = []
            for key,value,quantity in ticket_efficiency_CC_sorted:
                toPrint.append(["{0}: {1:.3f} ± {2:.3f}".format(CalculatorManager.left(20,key+'({0})'.format(quantity)),value[0],value[1]*2)])
            return {
                "title":title,
                "msgList" : [CalculatorManager.dumpToPrint(toPrint)]
            }
        return {
            "title":"エラー",
            "msgList" : ["未知のコマンド："+str(toPrintTarget)]
        }
        