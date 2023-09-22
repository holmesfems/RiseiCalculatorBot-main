from __future__ import annotations
import sys
sys.path.append('../')
from rcutils import netutil,itemArray
import re
from infoFromOuterSource.idtoname import SkillIdToName,ItemIdToName
from typing import Dict,List,Tuple
from riseicalculator2.listInfo import getItemRarity4,getItemRarity3,getItemRarity2
from infoFromOuterSource.formulation import Formula
from riseicalculator2.riseicalculatorprocess import CalculatorManager,CalculateMode

CHAR_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/character_table.json"
CHAR_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/ja_JP/gamedata/excel/character_table.json"
UNI_EQ_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/uniequip_table.json"
PATCH_CHAR_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/ja_JP/gamedata/excel/char_patch_table.json"

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
        content =  ",".join(["{0} × {1:d}".format(key,value) for key,value in self.itemArray.toNameCountDict().items()])
        return "[{0}]".format(content)
    
    def __iadd__(self,other:ItemCost):
        self.itemArray += other.itemArray
        return self

    def __add__(self,other:ItemCost)->ItemCost:
        copy = self.copy()
        copy += other
        return copy
    
    def filterRare2(self)->ItemCost:
        R2List = getItemRarity2(True)
        copy = self.copy()
        copy.itemArray = copy.itemArray.filterByZH(R2List)
        return copy
    
    #上級素材→中級換算、副産物無し
    def rare3and4ToRare2(self)->ItemCost:
        copy = self.copy()
        R4List = getItemRarity4(True)
        R3List = getItemRarity3(True)
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
    
    def toRiseiValue(self)->float:
        riseiValue = CalculatorManager.getValues(True,CalculateMode.SANITY)
        riseiDict = riseiValue.toIdValueDict()
        ret = 0
        copy = self.copy()
        copy.normalize()
        for key,value in copy.itemArray.toIdCountDict().items():
            if(not riseiDict.get(key)):continue
            ret += value * riseiDict[key]
        return ret
    
    def toStrBlock(self):
        sortedArray = self.itemArray.copy()
        return "```"+"\n".join("{0} × {1:d}".format(key,value)for key,value in sortedArray.toNameCountDict().items())+"```"
    
    def fromItemArray(array:itemArray.ItemArray) -> ItemCost:
        ret = ItemCost()
        ret.itemArray = array.copy()
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

    def addEq(self,uniEq):
        eqType = uniEq["typeName2"]
        if(not eqType):return #デフォルトのやつは追加しない
        costDicts = uniEq["itemCost"]
        key = eqType
        costs = [ItemCost(costValue) for costKey,costValue in costDicts.items()]
        self.uniqeEq[key] = costs

    def totalPhaseCost(self)->ItemCost:
        return ItemCost.sum(self.phases)
    
    def totalSkillMasterCost(self)->ItemCost:
        return ItemCost.sum([ItemCost.sum(x[1]) for x in self.skills])

    def totalSkillLv7Cost(self)->ItemCost:
        return ItemCost.sum(self.allSkills)
    
    def totalUniqueEQCost(self)->ItemCost:
        return ItemCost.sum([ItemCost.sum(value) for value in self.uniqeEq.values()])
    
    def allCost(self)->ItemCost:
        ret = self.totalPhaseCost()
        ret += self.totalSkillMasterCost()
        ret += self.totalSkillLv7Cost()
        ret += self.totalUniqueEQCost()
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

            self.operatorDict[key] = OperatorCosts(key,value)
            self.nameToId[value["name"]] = key
        
        #昇格(前衛アーミヤ)
        patchInfoJP:dict = get_json(PATCH_CHAR_TABLE_URL_JP)["patchChars"]
        for key,value in patchInfoJP.items():
            #今は前衛アーミヤ一人だけ、今後追加されたらまた調整する必要があるかも
            value["cnOnly"] = False
            value["name"] = value["name"] + "({0})".format(jobIdToName[value["profession"]])
            self.operatorDict[key] = OperatorCosts(key,value)
            self.nameToId[value["name"]] = key
        
        allUEQ = get_json(UNI_EQ_URL_CN)["equipDict"]
        for key,value in allUEQ.items():
            charId = value["charId"]
            self.operatorDict[charId].addEq(value)
    
    def getOperatorNames(self):
        return self.nameToId.keys()
    
    def getOperatorCostFromName(self,nameStr:str):
        id = self.nameToId[nameStr]
        return self.operatorDict.get(id,None)
    
    def getAllCostOfCNOnly(self):
        operatorCNOnly = [x for x in self.operatorDict.values() if x.cnOnly]
        allCosts = ItemCost(None)
        for item in operatorCNOnly:
            print(item.name)
            allCosts += item.totalPhaseCost()
            allCosts += item.totalSkillLv7Cost()
            allCosts += item.totalSkillMasterCost()
            #print(item.totalUniqueEQCost())
        #print(self.operatorDict)
        return allCosts
    
    def getAllCostItems(self)->Dict[str,OperatorCosts]:
        return self.operatorDict.copy()
    
class OperatorCostsCalculator:
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
            "msgList":["オペレーター【"+operatorName+"】は存在しません"]
        }
        skillCostList = costItem.skills
        if(skillNum > len(skillCostList)):return{
            "title" : title,
            "msgList":["オペレーター【"+operatorName+"】のスキル"+str(skillNum)+"は存在しません"]
        }
        skillName,skillCost = skillCostList[skillNum-1]
        if(not skillCost):return{
            "title" : title,
            "msgList":["オペレーター【"+operatorName+"】のスキル"+str(skillNum)+"の特化は存在しません"]
        }

        allCost = ItemCost.sum(skillCost)
        msgList = []
        title = "スキル特化検索: " + skillName
        for i in range(1,4):
            masterCost = skillCost[i-1]
            riseiValue = masterCost.toRiseiValue()
            headerMsg = "特化{0} 理性価値:{1:.2f}".format(i,riseiValue)
            blockMsg = masterCost.toStrBlock()
            msgList.append(headerMsg + blockMsg + "\n")
        
        #合計素材
        riseiValue = allCost.toRiseiValue()
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
    
