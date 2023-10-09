from __future__ import annotations
import sys
sys.path.append('../')
from rcutils import netutil,itemArray
import re
from infoFromOuterSource.idtoname import SkillIdToName,ItemIdToName
from typing import Dict,List,Tuple
from riseicalculator2.listInfo import getItemRarity4,getItemRarity3,getItemRarity2,getValueTarget
from infoFromOuterSource.formulation import Formula
from riseicalculator2.riseicalculatorprocess import CalculatorManager,CalculateMode
from enum import StrEnum
import enum
import yaml

CHAR_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/character_table.json"
CHAR_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/ja_JP/gamedata/excel/character_table.json"
UNI_EQ_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/uniequip_table.json"
UNI_EQ_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/ja_JP/gamedata/excel/uniequip_table.json"
PATCH_CHAR_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/ja_JP/gamedata/excel/char_patch_table.json"
EPSILON = 1e-4
get_json = netutil.get_json

jobIdToName:Dict[str,str] = {
    "WARRIOR":"前衛",
    "SNIPER" :"狙撃",
    "SPECIAL":"特殊",
    "SUPPORT":"補助",
    "TANK"   :"重装",
    "PIONEER":"先鋒",
    "CASTER" :"術師",
    "MEDIC"  :"医療"
}

class ItemCost:
    def __init__(self,valueList:List[Dict]=[]):
        itemDict = {}
        if valueList is None: valueList = []
        for item in valueList:
            key = item["id"]
            itemDict[key] = item["count"]
        self.itemArray = itemArray.ItemArray(itemDict)
    
    def copy(self):
        copy = ItemCost()
        copy.itemArray = self.itemArray.copy()
        return copy
    
    def __repr__(self):
        content =  ", ".join(["{0} × {1:d}".format(key,round(value)) if abs(value - round(value)) < EPSILON else "{0} × {1:.3f}".format(key,value) for key,value in self.itemArray.toNameCountDict().items()])
        return "[{0}]".format(content)
    
    def __iadd__(self,other:ItemCost):
        self.itemArray += other.itemArray
        return self

    def __add__(self,other:ItemCost)->ItemCost:
        copy = self.copy()
        copy += other
        return copy
    
    def filterRare2(self)->ItemCost:
        R2List = getItemRarity2(False)
        copy = self.copy()
        copy.itemArray = copy.itemArray.filterByZH(R2List)
        return copy
    
    #上級素材→中級換算、副産物無し
    def rare3and4ToRare2(self)->ItemCost:
        copy = self.copy()
        R4List = getItemRarity4(False)
        R3List = getItemRarity3(False)
        for item in R4List + R3List:
            id = ItemIdToName.zhToId(item)
            count = copy.itemArray.getById(id)
            if not count:continue
            formulaArray = Formula.getFormulaArray(id)
            formulaArray *= count
            formulaArray.normalize()
            formulaCost = ItemCost.fromItemArray(formulaArray)
            copy += formulaCost
        return copy.filterRare2()
    
    def sum(list:List[ItemCost]):
        if(not list): return ItemCost()
        ret = list[0].copy()
        for item in list[1:]:
            ret += item
        return ret
    
    def normalizeGold(self):
        self.itemArray.normalizeGold()
        return self

    def normalize(self):
        self.itemArray.normalize()
        return self
    
    def toRiseiValue(self,glob:bool = True)->float:
        riseiValue = CalculatorManager.getValues(glob,CalculateMode.SANITY)
        return riseiValue.getValueFromItemArray(self.itemArray)
    
    def toRiseiValue_OnlyValueTarget(self,glob:bool = True)->float:
        riseiValue = CalculatorManager.getValues(glob,CalculateMode.SANITY)
        return riseiValue.getValueFromItemArray_OnlyValueTarget(self.itemArray)
    
    def toStrBlock(self,sortByCount = False):
        sortedArray = self.itemArray.copy()
        items = sortedArray.toNameCountDict().items()
        if(sortByCount):
            items = sorted(items,key=lambda x: x[1],reverse=True)
        body = ["{0} × {1:d}".format(key,round(value)) if abs(value - round(value)) < EPSILON else "{0} × {1:.3f}".format(key,value) for key,value in items]
        return CalculatorManager.dumpToPrint(body)
    
    def fromItemArray(array:itemArray.ItemArray) -> ItemCost:
        ret = ItemCost()
        ret.itemArray = array.copy()
        return ret
    
    def toMaterialCost(self):
        ret = ItemCost()
        ret.itemArray = self.itemArray.filterByZH(getValueTarget(False))
        return ret
    
class OperatorCosts:
    def __init__(self,key,value):
        self.name = value["name"]
        self.id = key
        #昇進段階 昇進1, 昇進2に必要な素材
        self.phases:List[ItemCost] = [ItemCost(item["evolveCost"]) for item in value["phases"]][1:]
        #スキル特化に必要な素材
        #第一index:スキル指定 第2index:特化段階指定
        ret = []
        for item in value["skills"]:
            costs = [ItemCost(x["levelUpCost"]) for x in item["levelUpCostCond"]]
            key = SkillIdToName.getStr(item["skillId"])
            ret.append((key,costs))
        self.skills:List[Tuple[str,List[ItemCost]]] = ret
        #スキルLv1~7に必要な素材
        self.allSkills:List[ItemCost] = [ItemCost(x["lvlUpCost"]) for x in value["allSkillLvlup"]]

        #大陸版限定オペレーターか
        self.cnOnly:bool = value["cnOnly"] 
        #モジュール initInfoだけでは足りないので、別途追加
        self.uniqeEq:Dict[str,ItemCost] = {}
        self.uniqeEqIsCNOnly:Dict[str,bool] = {}
        #星の数
        #大陸版では "TIER_n"のstr、日本版ではnのintになる
        rarity = value["rarity"]
        if(type(rarity) is str):
            #大陸版表記
            keyRegex = r"TIER_(\d+)"
            match = re.match(keyRegex,rarity)
            self.stars:int = int(match.group(1))
        else:
            #JP版表記
            self.stars:int = rarity+1
        
        #昇格オペレーター(前衛アーミヤ)かの判定
        self.isPatch = value["isPatch"]

    #モジュールの素材を追加する
    def addEq(self,uniEq):
        eqType = uniEq["typeName2"]
        if(not eqType):return #デフォルトのやつは追加しない
        costDicts = uniEq["itemCost"]
        key = eqType
        costs = [ItemCost(costValue) for costKey,costValue in costDicts.items()]
        self.uniqeEq[key] = costs
        self.uniqeEqIsCNOnly[key] = uniEq["cnOnly"]

    def totalPhaseCost(self)->ItemCost:
        return ItemCost.sum(self.phases)
    
    def totalSkillMasterCost(self)->ItemCost:
        return ItemCost.sum([ItemCost.sum(x[1]) for x in self.skills])

    def totalSkillLv7Cost(self)->ItemCost:
        return ItemCost.sum(self.allSkills)
    
    def totalUniqueEQCost(self)->ItemCost:
        return ItemCost.sum([ItemCost.sum(value) for value in self.uniqeEq.values()])
    
    def totalUniqueEQCostCNOnly(self) -> ItemCost:
        return ItemCost.sum([ItemCost.sum(value) for key,value in self.uniqeEq.items() if self.uniqeEqIsCNOnly[key]])
    
    def hasCNOnlyUEQ(self) -> bool:
        return any(self.uniqeEqIsCNOnly.values())
    
    def allCost(self)->ItemCost:
        ret = self.totalPhaseCost()
        ret += self.totalSkillMasterCost()
        ret += self.totalSkillLv7Cost()
        ret += self.totalUniqueEQCost()
        return ret
    
    def allCostExceptEq(self)->ItemCost:
        ret = self.totalPhaseCost()
        ret += self.totalSkillMasterCost()
        ret += self.totalSkillLv7Cost()
        return ret
    
    def isCNOnly(self):
        return self.cnOnly

    def __repr__(self):
        return self.name + ":" + str(self.allCost())

class AllOperatorsInfo:
    def __init__(self):
        self.operatorDict:Dict[str,OperatorCosts] = {}
        self.nameToId:Dict[str,str] = {}
        self.init()

    def init(self):
        allInfoCN = get_json(CHAR_TABLE_URL_CN)
        allInfoJP = get_json(CHAR_TABLE_URL_JP)
        allUEQ:dict = get_json(UNI_EQ_URL_CN)["equipDict"]
        allUEQ_JP:dict = get_json(UNI_EQ_URL_JP)["equipDict"]

        with open("charmaterials/customZhToJa.yaml","rb") as f:
            customZhToJaDict:Dict[str,str] = yaml.safe_load(f)

        for key,value in allInfoCN.items():
            keyRegex = r"([^_]+)_(\d+)_([^_]+)"
            #print(key)
            match = re.match(keyRegex,key)
            type = match.group(1)
            #print(type)
            if(type != "char"): continue #オペレーターのみ登録
            if(value["isNotObtainable"]): continue #獲得できるオペレーターのみ登録
            jpValue = allInfoJP.get(key)
            if(jpValue):
                value = jpValue
                value["cnOnly"] = False
            else:
                value["cnOnly"] = True
                jpName = customZhToJaDict.get(value["name"],None)
                if(jpName):
                    value["name"] = jpName
            value["isPatch"] = False
            self.operatorDict[key] = OperatorCosts(key,value)
            self.nameToId[value["name"]] = key
        
        #昇格(前衛アーミヤ)
        patchInfoJP:dict = get_json(PATCH_CHAR_TABLE_URL_JP)["patchChars"]
        for key,value in patchInfoJP.items():
            #今は前衛アーミヤ一人だけ、今後追加されたらまた調整する必要があるかも
            value["cnOnly"] = False
            value["name"] = value["name"] + "({0})".format(jobIdToName[value["profession"]])
            value["isPatch"] = True
            self.operatorDict[key] = OperatorCosts(key,value)
            self.nameToId[value["name"]] = key
        
        for key,value in allUEQ.items():
            charId = value["charId"]
            jpValue = allUEQ_JP.get(key)
            if(jpValue):
                value["cnOnly"] = False
            else:
                value["cnOnly"] = True
            self.operatorDict[charId].addEq(value)
    
    def getOperatorNames(self):
        return self.nameToId.keys()
    
    def getOperatorCostFromName(self,nameStr:str):
        id = self.nameToId.get(nameStr,None)
        if(not id): return None
        return self.operatorDict.get(id,None)
    
    def getAllCostItems(self)->Dict[str,OperatorCosts]:
        return self.operatorDict.copy()

class OperatorCostsCalculator:
    class CostListSelection(StrEnum):
        STAR5ELITE = enum.auto()
        COSTOFCNONLY = enum.auto()

    operatorInfo = AllOperatorsInfo()

    def init():
        OperatorCostsCalculator.operatorInfo.init()

    def autoCompleteForMasterCosts(name:str,limit:int = 25) -> List[Tuple[str,str]]:
        return [(value.name,value.name) for value in OperatorCostsCalculator.operatorInfo.operatorDict.values() if name in value.name and value.stars>=4][:limit]
    
    def skillMasterCosts(operatorName:str,skillNum:int) -> Dict:
        costItem = OperatorCostsCalculator.operatorInfo.getOperatorCostFromName(operatorName)
        title = "スキル特化素材検索"
        if(not costItem): return {
            "title" : title,
            "msgList":["オペレーター【"+operatorName+"】は存在しません"],
            "type": "err"
        }
        skillCostList = costItem.skills
        if(skillNum > len(skillCostList)):return{
            "title" : title,
            "msgList":["オペレーター【"+operatorName+"】のスキル"+str(skillNum)+"は存在しません"],
            "type": "err"
        }
        skillName,skillCost = skillCostList[skillNum-1]
        if(not skillCost):return{
            "title" : title,
            "msgList":["オペレーター【"+operatorName+"】のスキル"+str(skillNum)+"の特化は存在しません"],
            "type": "err"
        }

        isGlobal = not costItem.isCNOnly()
        allCost = ItemCost.sum(skillCost)
        msgList = []
        title = "スキル特化検索: " + skillName
        for i in range(1,4):
            masterCost = skillCost[i-1]
            riseiValue = masterCost.toRiseiValue(isGlobal)
            headerMsg = "特化{0} 理性価値:{1:.2f}".format(i,riseiValue)
            blockMsg = masterCost.toStrBlock()
            msgList.append(headerMsg + blockMsg + "\n")
        
        #合計素材
        headerMsg = "合計  理性価値:{0:.2f}".format(riseiValue)
        blockMsg = allCost.toStrBlock()
        msgList.append(headerMsg + blockMsg + "\n")

        #中級換算
        r2Cost = allCost.rare3and4ToRare2()
        headerMsg = "合計  中級換算"
        blockMsg = r2Cost.toStrBlock()
        msgList.append(headerMsg + blockMsg)

        return{
            "title" : title,
            "msgList":msgList
        }

    def operatorCostList(selection:CostListSelection) -> Dict:
        if(selection is OperatorCostsCalculator.CostListSelection.STAR5ELITE):
            star5Operators = {key:value for key,value in OperatorCostsCalculator.operatorInfo.getAllCostItems().items() if value.stars == 5 and not value.isPatch}
            riseiValueDict = {key:value.totalPhaseCost().toRiseiValue_OnlyValueTarget(not value.isCNOnly()) for key,value in star5Operators.items()}
            sortedValueDict = {key:value for key,value in sorted(riseiValueDict.items(),key=lambda x:x[1],reverse=True)}
            title = "★5昇進素材価値表"
            headerMsg = "SoCは以下の計算に含まれません:"
            msgList = [headerMsg]
            toPrint = []
            for index,(key,value) in enumerate(sortedValueDict.items()):

                name = star5Operators[key].name
                #print(name,star5Operators[key].totalPhaseCost())
                riseiValue = value
                #phaseCost = star5Operators[key].totalPhaseCost()
                toPrint.append(f"{index+1}. {name} : {riseiValue:.3f}")
                if((index + 1)% 50 == 0):
                    msgList.append(CalculatorManager.dumpToPrint(toPrint))
                    toPrint = []
            if(toPrint):
                msgList.append(CalculatorManager.dumpToPrint(toPrint))
            return {"title":title,
                    "msgList":msgList
                    }
        
        elif(selection is OperatorCostsCalculator.CostListSelection.COSTOFCNONLY):
            cnOnlyOperators = {key:value for key,value in OperatorCostsCalculator.operatorInfo.getAllCostItems().items() if value.isCNOnly()}
            title = "未実装オペレーターの消費素材合計"
            msgList = []
            toPrint = []
            for key,value in cnOnlyOperators.items():
                toPrint.append(value.name)
            msgList.append("未実装オペレーター一覧：" + CalculatorManager.dumpToPrint(toPrint) + "\n")

            totalCost = ItemCost.sum([value.allCostExceptEq() for value in cnOnlyOperators.values()])
            msgList.append("全昇進、全特化の合計消費:" + totalCost.toStrBlock() + "\n")
            eqCNOnlyOperators = {key:value for key,value in OperatorCostsCalculator.operatorInfo.getAllCostItems().items() if value.hasCNOnlyUEQ()}
            eqCost = ItemCost.sum([value.totalUniqueEQCostCNOnly() for value in eqCNOnlyOperators.values()])
            msgList.append("未実装モジュールの合計消費:" + eqCost.toStrBlock() + "\n")
            msgList.append("全合計の中級素材換算:"+(totalCost+eqCost).rare3and4ToRare2().toStrBlock(sortByCount=True) + "\n")
            totalCostValue = totalCost.toRiseiValue(False) + eqCost.toRiseiValue(False)
            msgList.append(f"合計理性価値(補完チップ系抜き):{totalCostValue:.3f}\n")
            msgList.append(f"源石換算 : {totalCostValue/135:.3f}\n")
            msgList.append(f"日本円換算 : {totalCostValue/135/175*10000:.0f} 円")
            return {"title":title,
                    "msgList":msgList
                    }
            
        else:
            return{
                "title":"エラー",
                "msgList":"未知のコマンド:" + str(selection)
            }
    def autoCompleteForEliteCosts(name:str,limit:int = 25) -> List[Tuple[str,str]]:
        return [(value.name,value.name) for value in OperatorCostsCalculator.operatorInfo.operatorDict.values() if name in value.name and value.stars>=4 and not value.isPatch][:limit]
    
    def operatorEliteCost(operatorName:str):
        costItem = OperatorCostsCalculator.operatorInfo.getOperatorCostFromName(operatorName)
        title = "昇進必要素材検索"
        if(not costItem): return {
            "title" : title,
            "msgList":["オペレーター【"+operatorName+"】は存在しません"],
            "type": "err"
        }
        eliteCostList = costItem.phases
        if(not eliteCostList): return{
            "title" : title,
            "msgList":["オペレーター【"+operatorName+"】の昇進は存在しません"],
            "type": "err"
        }
        isGlobal = not costItem.isCNOnly()

        totalCost = ItemCost.sum(eliteCostList)
        title = "昇進必要素材検索: " + costItem.name
        msgList = []
        for i in range(1,3):
            eliteCost = eliteCostList[i-1]
            riseiValue = eliteCost.toRiseiValue(isGlobal)
            headerMsg = "昇進{0} 理性価値:{1:.2f}".format(i,riseiValue)
            blockMsg = eliteCost.toStrBlock()
            msgList.append(headerMsg + blockMsg + "\n")
        
        #合計素材
        riseiValue = totalCost.toRiseiValue(isGlobal)
        headerMsg = "合計  理性価値:{0:.2f}".format(riseiValue)
        blockMsg = totalCost.toStrBlock()
        msgList.append(headerMsg + blockMsg + "\n")

        #中級換算
        r2Cost = totalCost.rare3and4ToRare2()
        headerMsg = "合計  中級換算"
        blockMsg = r2Cost.toStrBlock()
        msgList.append(headerMsg + blockMsg)

        return{
            "title" : title,
            "msgList":msgList
        }

