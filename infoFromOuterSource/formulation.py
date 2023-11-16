import sys
import yaml
sys.path.append('../')
from infoFromOuterSource.idtoname import ItemIdToName
from rcutils import netutil,itemArray
from typing import Dict,List
from riseicalculator2 import listInfo

#素材合成の情報を保持するクラス
#FormulaItemは素材合成のレシピ一つ
#Formulaは全部のレシピをまとめたもの
class FormulaItem:
    def __init__(self,formulaJson:Dict):
        self.key = formulaJson["itemId"]
        self.name = ItemIdToName.getStr(self.key)
        baseDict:Dict[str,float] = {}
        for item in formulaJson["costs"]:
            baseDict[item["id"]] = item["count"]
        self.__baseArray = itemArray.ItemArray(baseDict)
        self.__selfArray = itemArray.ItemArray({self.key:-formulaJson["count"]})
        outcomeDict:Dict[str,float] = {}
        for item in formulaJson["extraOutcomeGroup"]:
            weight = item["weight"]
            outcomeDict[item["itemId"]] = weight * item["itemCount"]
        self.__outcomeArray = itemArray.ItemArray(outcomeDict)
        goldCost = formulaJson["goldCost"]
        self.__goldCostArray = itemArray.ItemArray({ItemIdToName.jaToId("龍門幣1000"):goldCost/1000})

    def toFormulaArray(self)->itemArray.ItemArray:
        return self.__baseArray + self.__selfArray + self.__goldCostArray
    
    def toOutcomeArray(self,dropRate:float,isGlobal:bool) -> itemArray.ItemArray:
        filterList = listInfo.getValueTarget(isGlobal)
        outcomeArray = self.__outcomeArray.filterByZH(filterList)
        outcomeArray *= 1/outcomeArray.totalCount()
        return outcomeArray * dropRate
    
    def toFormulaArrayWithOutcome(self,dropRate:float,isGlobal:bool) -> itemArray.ItemArray:
        return self.toFormulaArray() - self.toOutcomeArray(dropRate,isGlobal)
    
    def __repr__(self)->str:
        return self.name


get_json = netutil.get_json

class Formula:
    __idToFormula:Dict[str,FormulaItem] = {}
    def init():
        FORMULA_URL = 'https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/building_data.json'
        allInfo:dict = get_json(FORMULA_URL)["workshopFormulas"]
        formulaDict = {}
        for item in allInfo.values():
            id = item["itemId"]
            value = FormulaItem(item)
            formulaDict[id] = value
        Formula.__idToFormula = formulaDict
    
    def __checkAndInit():
        if(not Formula.__idToFormula): Formula.init()

    def getFormulaItem(idStr:float) -> FormulaItem:
        Formula.__checkAndInit()
        return Formula.__idToFormula.get(idStr)

    def getFormulaArray(idStr:float) -> itemArray.ItemArray:
        if formula := Formula.getFormulaItem(idStr):
            return formula.toFormulaArray()
        else:
            return itemArray.ItemArray()
    
    def getFormulaArrayListWithOutcome(dropRate:float,isGlobal:bool) -> List[itemArray.ItemArray]:
        Formula.__checkAndInit()
        return [x.toFormulaArrayWithOutcome(dropRate,isGlobal) for x in Formula.__idToFormula.values()]
    
    def getAllFormulaItems() -> List[FormulaItem]:
        Formula.__checkAndInit()
        return [x for x in Formula.__idToFormula.values()]
