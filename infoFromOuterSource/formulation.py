import sys
import yaml
sys.path.append('../')
from infoFromOuterSource.idtoname import ItemIdToName
from rcutils import netutil,itemArray
from typing import Dict,List

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
        self.baseArray = itemArray.ItemArray(baseDict)
        self.selfArray = itemArray.ItemArray({self.key:-formulaJson["count"]})
        totalWeight = 0
        outcomeDict:Dict[str,float] = {}
        for item in formulaJson["extraOutcomeGroup"]:
            weight = item["weight"]
            outcomeDict[item["itemId"]] = weight * item["itemCount"]
            totalWeight += weight
        self.outcomeArray = itemArray.ItemArray(outcomeDict)
        self.outcomeArray *= 1.0/totalWeight
        goldCost = formulaJson["goldCost"]
        self.goldCostArray = itemArray.ItemArray({ItemIdToName.jaToId("龍門幣1000"):goldCost/1000})

    def toFormulaArray(self)->itemArray.ItemArray:
        return self.baseArray + self.selfArray + self.goldCostArray
    
    def toFormulaArrayWithOutcome(self,dropRate:float) -> itemArray.ItemArray:
        return self.toFormulaArray() - self.outcomeArray * dropRate
    
    def __repr__(self)->str:
        return self.name


get_json = netutil.get_json

class Formula:
    __idToFormula:Dict[str,FormulaItem] = {}
    def init():
        FORMULA_URL = 'https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/building_data.json'
        allInfo:dict = get_json(FORMULA_URL)["workshopFormulas"]
        Formula.__idToFormula:Dict[str,FormulaItem] = {}
        for index,item in allInfo.items():
            id = item["itemId"]
            value = FormulaItem(item)
            Formula.__idToFormula[id] = value
    
    def __checkAndInit():
        if(not Formula.__idToFormula): Formula.init()

    def getFormulaArray(idStr:float) -> itemArray.ItemArray:
        Formula.__checkAndInit()
        formula = Formula.__idToFormula.get(idStr)
        if(formula):
            return formula.toFormulaArray()
        else:
            return itemArray.ItemArray()
    
    def getFormulaArrayListWithOutcome(dropRate:float) -> List[itemArray.ItemArray]:
        Formula.__checkAndInit()
        return [x.toFormulaArrayWithOutcome(dropRate) for x in Formula.__idToFormula.values()]
    
    def getAllFormulaItems() -> List[FormulaItem]:
        Formula.__checkAndInit()
        return [x for x in Formula.__idToFormula.values()]
