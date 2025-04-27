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
from rcutils.rcReply import RCMsgType,RCReply
from typing import Literal
import dataclasses

CHAR_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/character_table.json"
CHAR_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData_YoStar/main/ja_JP/gamedata/excel/character_table.json"
UNI_EQ_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/uniequip_table.json"
UNI_EQ_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData_YoStar/main/ja_JP/gamedata/excel/uniequip_table.json"
PATCH_CHAR_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData_YoStar/main/ja_JP/gamedata/excel/char_patch_table.json"
PATCH_CHAR_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/char_patch_table.json"

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

with open("charmaterials/customZhToJa.yaml","rb") as f:
    __customZhToJaDict:Dict[str,str] = yaml.safe_load(f)

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
    
    def isNotZero(self) -> bool:
        return self.itemArray.isNotZero()
    
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
    
    @staticmethod
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

class EQCostItem:
    def __init__(self, type:str, phaseCosts:List[ItemCost], isCNOnly: bool):
        self.type = type
        self.phaseCosts = phaseCosts
        self.isCNOnly = isCNOnly
    
    def totalCost(self) -> ItemCost:
        return ItemCost.sum(self.phaseCosts)

class EQCost:
    def __init__(self):
        self.eqCostList:List[EQCostItem] = []
    
    def hasUniqeEq(self)->bool:
        return bool(self.eqCostList)
    
    def hasCNOnlyUEQ(self)->bool:
        return any(item.isCNOnly for item in self.eqCostList)
    
    def allUEQ(self) -> List[EQCostItem]:
        return [item for item in self.eqCostList]
    
    def allUEQCost(self) -> ItemCost:
        return ItemCost.sum([item.totalCost() for item in self.allUEQ()])
    
    def globalUEQ(self) -> List[EQCostItem]:
        return [item for item in self.eqCostList if not item.isCNOnly]
    
    def globalUEQCost(self) -> ItemCost:
        return ItemCost.sum([item.totalCost() for item in self.globalUEQ()])
    
    def cnOnlyUEQ(self) -> List[EQCostItem]:
        return [item for item in self.eqCostList if item.isCNOnly]

    def cnOnlyUEQCost(self) -> ItemCost:
        return ItemCost.sum([item.totalCost() for item in self.cnOnlyUEQ()])
    
    def addUEQ(self,item:EQCostItem):
        self.eqCostList.append(item)
        if(len(self.eqCostList) >= 2):
            self.eqCostList.sort(key=lambda x: x.type)

class OperatorCosts:
    def __init__(self,key:str,value:Dict[str,str]):
        self.name = value["name"]
        self.cnName = value["cnName"]
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
        self.skillIds = [item["skillId"] for item in value["skills"]]
        #スキルLv1~7に必要な素材
        self.allSkills:List[ItemCost] = [ItemCost(x["lvlUpCost"]) for x in value["allSkillLvlup"]]

        #大陸版限定オペレーターか
        self.cnOnly:bool = value["cnOnly"]
        #モジュール initInfoだけでは足りないので、別途追加
        self.uniqeEq:EQCost = EQCost()
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
        
        #昇格オペレーター(前衛アーミヤ,医療アーミヤ)かの判定
        self.isPatch = value["isPatch"]

    #モジュールの素材を追加する
    def addEq(self,uniEqJson):
        eqType = uniEqJson["typeName2"]
        if(not eqType):return #デフォルトのやつは追加しない
        costDicts = uniEqJson["itemCost"]
        key = eqType
        costs = [ItemCost(costValue) for costKey,costValue in costDicts.items()]
        eqCostItem = EQCostItem(key,costs,uniEqJson["cnOnly"])
        self.uniqeEq.addUEQ(eqCostItem)

    def hasUniqeEq(self) -> bool:
        return self.uniqeEq.hasUniqeEq()

    def totalPhaseCost(self)->ItemCost:
        return ItemCost.sum(self.phases)
    
    def totalSkillMasterCost(self)->ItemCost:
        return ItemCost.sum([ItemCost.sum(x[1]) for x in self.skills])

    def totalSkillLv7Cost(self)->ItemCost:
        return ItemCost.sum(self.allSkills)
    
    def totalUniqueEQCost(self)->ItemCost:
        return self.uniqeEq.allUEQCost()
    
    def totalUniqueEQCostCNOnly(self) -> ItemCost:
        return self.uniqeEq.cnOnlyUEQCost()
    
    def totalUniqueEQCostGlobal(self) -> ItemCost:
        return self.uniqeEq.globalUEQCost()
    
    def hasCNOnlyUEQ(self) -> bool:
        return self.uniqeEq.hasCNOnlyUEQ()
    
    def allCost(self)->ItemCost:
        ret = self.allCostExceptEq()
        ret += self.totalUniqueEQCost()
        return ret
    
    def allCostExceptEq(self)->ItemCost:
        ret = self.totalSkillMasterCost()
        #昇格オペレーターは、元オペレーターと消費素材共有するため、ここでは計上しない
        if(not self.isPatch): 
            ret += self.totalPhaseCost()
            ret += self.totalSkillLv7Cost()
        return ret
    
    def isCNOnly(self):
        return self.cnOnly

    def __repr__(self):
        return self.name + ":" + str(self.allCost())
    
    def isRecent(self):
        return (not self.isCNOnly()) and (self.cnName in __customZhToJaDict)

class AllOperatorsInfo:
    def __init__(self):
        self.operatorDict:Dict[str,OperatorCosts] = {}
        self.nameToId:Dict[str,str] = {}
        self.cnNameToJaName:Dict[str,str] = {}
        self.init()

    def init(self):
        allInfoCN,allInfoJP,allUEQ,allUEQ_JP = netutil.get_json_aio([CHAR_TABLE_URL_CN,CHAR_TABLE_URL_JP,UNI_EQ_URL_CN,UNI_EQ_URL_JP])
        allUEQ = allUEQ["equipDict"]
        allUEQ_JP:dict = allUEQ_JP["equipDict"]
        try:
            operatorDict:Dict[str,OperatorCosts] = {}
            nameToId:Dict[str,str] = {}
            cnNameToJaName:Dict[str,str] = {}
            

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
                    cnName = value["name"]
                    cnNameToJaName[value["name"]] = jpValue["name"]
                    value = jpValue
                    value["cnOnly"] = False
                    value["cnName"] = cnName
                else:
                    value["cnOnly"] = True
                    jpName = __customZhToJaDict.get(value["name"],None)
                    value["cnName"] = value["name"]
                    if(jpName):
                        cnNameToJaName[value["name"]] = jpName
                        value["name"] = jpName
                value["isPatch"] = False
                operatorDict[key] = OperatorCosts(key,value)
                nameToId[value["name"]] = key
            
            #昇格
            patchInfoJP:dict = get_json(PATCH_CHAR_TABLE_URL_JP)["patchChars"]
            patchTableCN:dict = get_json(PATCH_CHAR_TABLE_URL_CN)
            patchInfoCN:dict = patchTableCN["patchChars"]
            patchKeyCN:dict = patchTableCN["infos"]
            def originalOperatorName(patchKey:str):
                candidate = [key for key,value in patchKeyCN.items() if patchKey in value["tmplIds"]]
                if(candidate): 
                    operator = operatorDict.get(candidate[0])
                    if(operator): return operator.name
                return ""
            for key,value in patchInfoCN.items():
                #今は前衛アーミヤ一人だけ、今後追加されたらまた調整する必要があるかも
                #医療アーミヤも追加されました 2024/05/01
                jpValue = patchInfoJP.get(key)
                if(jpValue):
                    value = jpValue
                    value["cnOnly"] = False
                else:
                    value["cnOnly"] = True
                value["name"] = originalOperatorName(key) + "({0})".format(jobIdToName[value["profession"]])
                value["isPatch"] = True
                operatorDict[key] = OperatorCosts(key,value)
                nameToId[value["name"]] = key
            #モジュール情報
            for key,value in allUEQ.items():
                charId = value["charId"]
                if(value["itemCost"] == None): continue #統合戦略モジュールをスキップ
                jpValue = allUEQ_JP.get(key)
                if(jpValue):
                    value["cnOnly"] = False
                else:
                    value["cnOnly"] = True
                operatorDict[charId].addEq(value)
            self.operatorDict = operatorDict
            self.nameToId = nameToId
            self.cnNameToJaName = cnNameToJaName
        except Exception as e:
            print(e)
    
    def getOperatorNames(self):
        return self.nameToId.keys()
    
    def getOperatorCostFromName(self,nameStr:str):
        id = self.nameToId.get(nameStr,None)
        if(not id): return None
        return self.operatorDict.get(id,None)
    
    def getAllCostItems(self)->Dict[str,OperatorCosts]:
        return self.operatorDict.copy()
    
    def getSortedEliteCostDict(self,star:int):
        operatorCosts = {key:value for key,value in self.getAllCostItems().items() if value.stars == star and not value.isPatch}
        riseiValueDict = {key:value.totalPhaseCost().toRiseiValue_OnlyValueTarget(not value.isCNOnly()) for key,value in operatorCosts.items()}
        sortedValueDict = {key:value for key,value in sorted(riseiValueDict.items(),key=lambda x:x[1],reverse=True)}
        return {operatorCosts[key].name:value for key,value in sortedValueDict.items()}
    
    @dataclasses.dataclass
    class SkillCostInfo:
        skillName: str
        operatorName: str
        index: int
        totalCost: ItemCost
        key:str
        isCNOnly:bool
        def operatorNameIndex(self):
            return self.operatorName + f"(S{self.index})"

    def getSortedSkillCostDict(self,star:int):
        operatorCosts = {key:value for key,value in OperatorCostsCalculator.operatorInfo.getAllCostItems().items() if value.stars==star}
        skillCosts:List[AllOperatorsInfo.SkillCostInfo] = []
        for operator in operatorCosts.values():
            index = 0
            for skillName, skillCostList in operator.skills:
                index+=1
                skillCosts.append(AllOperatorsInfo.SkillCostInfo(skillName,operator.name,index,sum(skillCostList,ItemCost()),operator.skillIds[index-1],operator.isCNOnly()))
        skillCosts.sort(key=lambda x:x.totalCost.toRiseiValue(not x.isCNOnly),reverse=True)
        return {item.key:item for item in skillCosts}

class OperatorCostsCalculator:
    class CostListSelection(StrEnum):
        STAR5ELITE = enum.auto()
        STAR6ELITE = enum.auto()
        STAR4ELITE = enum.auto()
        COSTOFCNONLY = enum.auto()
        COSTOFGLOBAL = enum.auto()
        MASTERSTAR6 = enum.auto()
        MASTERSTAR5 = enum.auto()
        MASTERSTAR4 = enum.auto()
        RECENTINFO = enum.auto()
        
    operatorInfo = AllOperatorsInfo()

    def init():
        OperatorCostsCalculator.operatorInfo.init()

    def autoCompleteForMasterCost(name:str,limit:int = 25) -> List[Tuple[str,str]]:
        return [(value.name,value.name) for value in OperatorCostsCalculator.operatorInfo.operatorDict.values() if name in value.name and value.stars>=4][:limit]
    
    def skillMasterCost(operatorName:str,skillNum:int) -> RCReply:
        costItem = OperatorCostsCalculator.operatorInfo.getOperatorCostFromName(operatorName)
        title = "スキル特化検索"
        if(not costItem): return RCReply(
            embbedTitle=title,
            embbedContents=["オペレーター【"+operatorName+"】は存在しません"],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: Invalid operator name: {operatorName}"
        )
        skillCostList = costItem.skills
        if(not skillCostList): return RCReply(
            embbedTitle=title,
            embbedContents=["オペレーター【"+operatorName+"】はスキルが存在しません"],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: Operator {operatorName} has no skill"
        )
        if(skillNum is not None and skillNum > len(skillCostList)):return RCReply(
            embbedTitle=title,
            embbedContents=["オペレーター【"+operatorName+"】のスキル"+str(skillNum)+"は存在しません"],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: Operator {operatorName} does not have skill {skillNum}"
        )
        if(costItem.stars <= 3):return RCReply(
            embbedTitle=title,
            embbedContents=[f"オペレーター【{operatorName}】はスキルの特化は存在しません"],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: The skill of operator {operatorName} can not be mastered"
        )
        skillName,skillCost = skillCostList[skillNum-1]
        isGlobal = not costItem.isCNOnly()
        allCost = ItemCost.sum(skillCost)
        msgList = []
        title = "スキル特化検索: " + skillName
        skillId = costItem.skillIds[skillNum-1]
        description = SkillIdToName.getDescription(skillId)
        jsonForAI = {
            "skillName": skillName,
            "skillNumber": skillNum,
            "itemCosts":[]
        }
        if(description):
            msgList.append(description + "\n\n")
        for i in range(1,4):
            masterCost = skillCost[i-1]
            riseiValue = masterCost.toRiseiValue(isGlobal)
            headerMsg = "特化{0} 理性価値:{1:.2f}".format(i,riseiValue)
            blockMsg = masterCost.toStrBlock()
            msgList.append(headerMsg + blockMsg + "\n")
            jsonForAI["itemCosts"].append({
                "phase": f"特化{i}",
                "sanityValue":riseiValue,
                "costItem":masterCost.itemArray.toNameCountDict()
            })
        
        #合計素材
        riseiValue = allCost.toRiseiValue(isGlobal)
        headerMsg = "合計  理性価値:{0:.2f}".format(riseiValue)
        blockMsg = allCost.toStrBlock()
        msgList.append(headerMsg + blockMsg + "\n")

        #中級換算
        r2Cost = allCost.rare3and4ToRare2()
        headerMsg = "合計  中級換算"
        blockMsg = r2Cost.toStrBlock()
        msgList.append(headerMsg + blockMsg)
        #jsonForAI["totalIntermediateConvertion"] = r2Cost.itemArray.toNameCountDict()

        #ランキング
        skillCostRanking = OperatorCostsCalculator.operatorInfo.getSortedSkillCostDict(costItem.stars)
        try: 
            nums = len(skillCostRanking)
            index = list(skillCostRanking.keys()).index(costItem.skillIds[skillNum-1])
            msgList.append(f"星{costItem.stars}スキル{nums}個中、第{index+1}位の消費です")

        except:
            ...

        return RCReply(
            embbedTitle=title,
            embbedContents=msgList,
            responseForAI=str(jsonForAI)
        )
    
    def operatorSkillInfo(operatorName:str,skillNum:int) -> RCReply:
        #AIのみから呼び出す予定
        costItem = OperatorCostsCalculator.operatorInfo.getOperatorCostFromName(operatorName)
        title = "スキル説明検索"
        if(not costItem): return RCReply(
            embbedTitle=title,
            embbedContents=["オペレーター【"+operatorName+"】は存在しません"],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: Invalid operator name: {operatorName}"
        )
        skillCostList = costItem.skills
        if(not skillCostList): return RCReply(
            embbedTitle=title,
            embbedContents=["オペレーター【"+operatorName+"】はスキルが存在しません"],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: Operator {operatorName} has no skill"
        )
        if(skillNum is not None and skillNum > len(skillCostList)):return RCReply(
            embbedTitle=title,
            embbedContents=["オペレーター【"+operatorName+"】のスキル"+str(skillNum)+"は存在しません"],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: Operator {operatorName} does not have skill {skillNum}"
        )
        skillName,skillCost = skillCostList[skillNum-1]
        title = "スキル情報: " + skillName
        skillId = costItem.skillIds[skillNum-1]
        skillItem = SkillIdToName.getItem(skillId)
        return RCReply(
            embbedTitle=title,
            embbedContents=[skillItem.description],
            responseForAI=str(skillItem.jsonForAI())
        )

    def operatorCostList(selection:CostListSelection) -> RCReply:
        #OpenAIから呼び出す予定は現状なし、responseForAIは空欄にする
        def printCostRanking(sortedValueDict):
            headerMsg = "SoCは以下の計算に含まれません:"
            msgList = [headerMsg]
            toPrint = []
            for index,(key,value) in enumerate(sortedValueDict.items()):

                name = key
                #print(name,star5Operators[key].totalPhaseCost())
                riseiValue = value
                #phaseCost = star5Operators[key].totalPhaseCost()
                toPrint.append(f"{index+1}. {name} : {riseiValue:.3f}")
                if((index + 1)% 50 == 0):
                    msgList.append(CalculatorManager.dumpToPrint(toPrint))
                    toPrint = []
            if(toPrint):
                msgList.append(CalculatorManager.dumpToPrint(toPrint))
            return msgList
        if(selection is OperatorCostsCalculator.CostListSelection.STAR4ELITE):
            sortedValueDict = OperatorCostsCalculator.operatorInfo.getSortedEliteCostDict(4)
            title = "★4昇進素材価値表"
            return RCReply(
                embbedTitle=title,
                embbedContents=printCostRanking(sortedValueDict)
            )
        elif(selection is OperatorCostsCalculator.CostListSelection.STAR5ELITE):
            sortedValueDict = OperatorCostsCalculator.operatorInfo.getSortedEliteCostDict(5)
            title = "★5昇進素材価値表"
            return RCReply(
                embbedTitle=title,
                embbedContents=printCostRanking(sortedValueDict)
            )
        elif(selection is OperatorCostsCalculator.CostListSelection.STAR6ELITE):
            sortedValueDict = OperatorCostsCalculator.operatorInfo.getSortedEliteCostDict(6)
            title = "★6昇進素材価値表"
            return RCReply(
                embbedTitle=title,
                embbedContents=printCostRanking(sortedValueDict)
            )
        
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
            return RCReply(
                embbedTitle=title,
                embbedContents=msgList
            )
        
        elif(selection is OperatorCostsCalculator.CostListSelection.COSTOFGLOBAL):
            globalOperators = {key:value for key,value in OperatorCostsCalculator.operatorInfo.getAllCostItems().items() if not value.isCNOnly()}
            title = "実装済オペレーターの消費素材合計"
            msgList = []
            # toPrint = []
            # for key,value in globalOperators.items():
            #     toPrint.append(value.name)
            # msgList.append("オペレーター一覧：" + CalculatorManager.dumpToPrint(toPrint) + "\n")

            totalCost = ItemCost.sum([value.allCostExceptEq() for value in globalOperators.values()])
            msgList.append("全昇進、全特化の合計消費:" + totalCost.toStrBlock() + "\n")
            eqOperators = {key:value for key,value in globalOperators.items() if value.hasUniqeEq()}
            eqCost = ItemCost.sum([value.totalUniqueEQCostGlobal() for value in eqOperators.values()])
            msgList.append("実装済モジュールの合計消費:" + eqCost.toStrBlock() + "\n")
            msgList.append("全合計の中級素材換算:"+(totalCost+eqCost).rare3and4ToRare2().toStrBlock(sortByCount=True) + "\n")
            totalCostValue = totalCost.toRiseiValue(glob=True) + eqCost.toRiseiValue(glob=True)
            msgList.append(f"合計理性価値(補完チップ系抜き):{totalCostValue:.3f}\n")
            msgList.append(f"源石換算 : {totalCostValue/135:.3f}\n")
            msgList.append(f"日本円換算 : {totalCostValue/135/175*10000:.0f} 円")
            return RCReply(
                embbedTitle=title,
                embbedContents=msgList
            )
        elif(selection is OperatorCostsCalculator.CostListSelection.MASTERSTAR6):
            return OperatorCostsCalculator.getMasterCostStatistics(6)
        elif(selection is OperatorCostsCalculator.CostListSelection.MASTERSTAR5):
            return OperatorCostsCalculator.getMasterCostStatistics(5)
        elif(selection is OperatorCostsCalculator.CostListSelection.MASTERSTAR4):
            return OperatorCostsCalculator.getMasterCostStatistics(4)
        elif(selection is OperatorCostsCalculator.CostListSelection.RECENTINFO):
            return OperatorCostsCalculator.getRecentEleteMaster()
        else:
            return RCReply(
                embbedTitle="エラー",
                embbedContents=["未知のコマンド:" + str(selection)]
            )

    def getMasterCostStatistics(star:Literal[4,5,6]) -> RCReply:
        skillCosts = list(OperatorCostsCalculator.operatorInfo.getSortedSkillCostDict(star).values())
        skillNums = len(skillCosts)
        title = f"星{star}の特化統計情報"
        msgList = []
        msgList.append(f"総スキル数: {skillNums}\n")
        msgList.append(f"一番消費が重い特化スキル:\n{skillCosts[0].operatorNameIndex()}\n" + skillCosts[0].totalCost.toStrBlock())
        msgList.append(f"合計理性価値: {skillCosts[0].totalCost.toRiseiValue(False):.2f}\n")
        msgList.append("消費が重いスキルTop10:")
        msg = "```\n"
        for index in range(10):
            if(index >= skillNums):break
            skillCostItem = skillCosts[index]
            msg += f"{index+1}.{skillCostItem.operatorNameIndex()}: {skillCostItem.totalCost.toRiseiValue(False):.2f}\n"
        msg += "```\n"
        msgList.append(msg)
        msgList.append(f"一番消費が軽い特化スキル:\n{skillCosts[skillNums-1].operatorNameIndex()}\n" + skillCosts[skillNums-1].totalCost.toStrBlock())
        msgList.append(f"合計理性価値: {skillCosts[skillNums-1].totalCost.toRiseiValue(False):.2f}\n")
        msgList.append("消費が軽いスキルTop10:")
        msg = "```\n"
        for index in range(skillNums-10,skillNums):
            if(index < 0):continue
            skillCostItem = skillCosts[index]
            msg += f"{index+1}.{skillCostItem.operatorNameIndex()}: {skillCostItem.totalCost.toRiseiValue(False):.2f}\n"
        msg += "```\n"
        msgList.append(msg)
        msgList.append(f"平均理性価値: {sum(skillCost.totalCost.toRiseiValue(False) for skillCost in skillCosts)/skillNums:.2f}")

        return RCReply(embbedTitle=title,embbedContents=msgList)
    
    def getRecentEleteMaster() -> RCReply:
        recentOperators = {key:value for key,value in OperatorCostsCalculator.operatorInfo.getAllCostItems().items() if value.isRecent()}
        title = "直近実装昇進検索"
        msgList = []
        eleteCostDicts = {}
        masterCostDicts = {}
        if(len(recentOperators) == 0):
            msgList.append("直近実装のオペレーターは存在しません")
            return RCReply(embbedContents=msgList,embbedTitle=title)
        for key,value in recentOperators.items():
            eleteCostDict = eleteCostDicts.get(value.stars)
            msg = f"{value.name}:\n```\n"
            if(not eleteCostDict):
                eleteCostDict = OperatorCostsCalculator.operatorInfo.getSortedEliteCostDict(value.stars)
                eleteCostDicts[value.stars] = eleteCostDict
            index_Elete = list(eleteCostDict.keys()).index(value.name)
            totalEleteNum = len(eleteCostDict)
            elete_cost = list(eleteCostDict.values())[index_Elete]
            msg += f"昇進必要理性: {elete_cost:.2f}\n"
            msg += f"昇進理性順位: {index_Elete + 1} / {totalEleteNum}\n"
            masterCostDict = masterCostDicts.get(value.stars)
            totalSkillNum = len(masterCostDict)
            if(not masterCostDict):
                masterCostDict = OperatorCostsCalculator.operatorInfo.getSortedSkillCostDict(value.stars)
                masterCostDicts[value.stars] = masterCostDict
            for index, skillId in enumerate(value.skillIds):
                index_Master = list(masterCostDict.keys()).index(skillId)
                msg += f"S{index+1}特化必要理性: {masterCostDict.get(skillId).totalCost.toRiseiValue(not value.isCNOnly())}\n"
                msg += f"特化理性順位: {index_Master+1} / {totalSkillNum}\n"
            msg += "```"
            msgList.append(msg)
        return RCReply(embbedTitle=title,embbedContents=msgList)

    def autoCompleteForEliteCost(name:str,limit:int = 25) -> List[Tuple[str,str]]:
        return [(value.name,value.name) for value in OperatorCostsCalculator.operatorInfo.operatorDict.values() if name in value.name and value.stars>=4 and not value.isPatch][:limit]
    
    def operatorEliteCost(operatorName:str) -> RCReply:
        costItem = OperatorCostsCalculator.operatorInfo.getOperatorCostFromName(operatorName)
        title = "昇進必要素材検索"
        if(not costItem): return RCReply(
            embbedTitle=title,
            embbedContents=["オペレーター【"+operatorName+"】は存在しません"],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: Invalid operator name: {operatorName}"
        )

        eliteCostList = costItem.phases
        if(not eliteCostList): return RCReply(
            embbedTitle=title,
            embbedContents=["オペレーター【"+operatorName+"】の昇進は存在しません"],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: {operatorName} can not be promoted"
        )

        isGlobal = not costItem.isCNOnly()
        totalCost = ItemCost.sum(eliteCostList)
        title = "昇進必要素材検索: " + costItem.name
        msgList = []
        jsonForAI = {
            "itemCosts":[]
        }
        for i in range(1,3):
            eliteCost = eliteCostList[i-1]
            riseiValue = eliteCost.toRiseiValue(isGlobal)
            headerMsg = "昇進{0} 理性価値:{1:.2f}".format(i,riseiValue)
            blockMsg = eliteCost.toStrBlock()
            msgList.append(headerMsg + blockMsg + "\n")
            jsonForAI["itemCosts"].append({
                "phase":f"昇進{i}",
                "sanityValue":riseiValue,
                "costItem":eliteCost.itemArray.toNameCountDict()
            })
        
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

        if(not costItem.isPatch and (costItem.stars == 5 or costItem.stars == 6)):
            sortedValues = OperatorCostsCalculator.operatorInfo.getSortedEliteCostDict(costItem.stars)
            index = list(sortedValues.keys()).index(costItem.name)
            nums = len(sortedValues)
            msgList.append(f"星{costItem.stars}オペレーター{nums}名中、第{index+1}位の消費です")

        #jsonForAI["totalIntermediateConvertion"] = r2Cost.itemArray.toNameCountDict()
        return RCReply(
            embbedTitle=title,
            embbedContents=msgList,
            responseForAI=str(jsonForAI)
        )

    def autoCompleteForModuleCost(name:str,limit:int = 25):
        return [(value.name,value.name) for value in OperatorCostsCalculator.operatorInfo.operatorDict.values() if name in value.name and value.hasUniqeEq()][:limit]

    def operatorModuleCost(operatorName:str):
        costItem = OperatorCostsCalculator.operatorInfo.getOperatorCostFromName(operatorName)
        title = "モジュール必要素材検索"
        if(not costItem): return RCReply(
            embbedTitle=title,
            embbedContents=["オペレーター【"+operatorName+"】は存在しません"],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: Invalid operator name: {operatorName}"
        )

        eqCosts = costItem.uniqeEq
        if(not eqCosts.hasUniqeEq()): return RCReply(
            embbedTitle=title,
            embbedContents=["オペレーター【"+operatorName+"】のモジュールは存在しません"],
            msgType=RCMsgType.ERR,
            responseForAI=f"Error: Operator {operatorName} does not have module"
        )

        title = "モジュール必要素材検索: " + costItem.name
        msgList = []
        jsonForAI = []
        for eqCostItem in eqCosts.allUEQ():
            isGlobal = not eqCostItem.isCNOnly
            header = f"{eqCostItem.type}"
            if(not isGlobal): header += "(大陸版)"
            bodyMsg = ""
            jsonItem = {
                "typeName" : f"{eqCostItem.type}",
                "itemCosts": []
            }
            for i in range(3):
                eqCost = eqCostItem.phaseCosts[i]
                phaseMsg = f"{header} Stage.{i+1} 理性価値:{eqCost.toRiseiValue_OnlyValueTarget(isGlobal):.2f}"
                blockMsg = eqCost.toStrBlock()
                bodyMsg += phaseMsg + blockMsg + "\n"
                jsonItem["itemCosts"].append({
                    "phase": "Unlock" if i == 0 else f"Modify Stage {i}",
                    "sanityValue" : round(eqCost.toRiseiValue_OnlyValueTarget(isGlobal),2),
                    "costItem": eqCost.itemArray.toNameCountDict()
                })
            totalCost = eqCostItem.totalCost()
            lastMsg = f"合計 理性価値:{totalCost.toRiseiValue_OnlyValueTarget(isGlobal):.2f}"
            lastMsg += totalCost.toStrBlock() + "\n"
            lastMsg += "合計 中級換算:"
            lastMsg += totalCost.rare3and4ToRare2().toStrBlock()
            msgList.append(bodyMsg + lastMsg + "\n")
            #jsonItem["totalIntermediateConvertion"] = totalCost.rare3and4ToRare2().itemArray.toNameCountDict()
            jsonForAI.append(jsonItem)
        
        return RCReply(
            embbedTitle=title,
            embbedContents=msgList,
            responseForAI=str({"moduleCost":jsonForAI})
        )