import sys
sys.path.append('../')
from rcutils import netutil
import re
from idtoname.idtoname import SkillIdToName,ItemIdToName
from typing import Dict

CHAR_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/character_table.json"
CHAR_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/ja_JP/gamedata/excel/character_table.json"
UNI_EQ_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/uniequip_table.json"


get_json = netutil.get_json

class ItemCost:
    class ItemInfo:
        def __init__(self,jsonValue):
            if(jsonValue):
                self.id = jsonValue["id"]
                self.count = jsonValue["count"]
                self.name = ItemIdToName.getStr(self.id)
            else:
                self.id = ""
                self.count = 0
                self.name = ""

        def copy(self):
            copy = ItemCost.ItemInfo(None)
            copy.id = self.id
            copy.count = self.count
            copy.name = self.name
            return self
        
        def __add__(self,otherItem):
            copy = self.copy()
            copy += otherItem
            return copy

        def __iadd__(self, otherItem):
            if(self.id == otherItem.id):
                self.count += otherItem.count
            return self
        
        def __repr__(self):
            return self.name + "×" + str(self.count)


    def __init__(self,valueList):
        self.itemDict = {}
        if not valueList: return
        for item in valueList:
            key = item["id"]
            self.itemDict[key] = ItemCost.ItemInfo(item)
    
    def copy(self):
        copy = ItemCost(None)
        copy.itemDict = self.itemDict.copy()
        return copy
    
    def __repr__(self):
        return ",".join([str(x) for x in sorted(self.itemDict.values(),key = lambda y:y.id)])
    
    def __add__(self,other):
        copy = self.copy()
        for key,value in other.itemDict.items():
            before = copy.itemDict.get(key)
            if(not before): #copy側にkeyが無い
                copy.itemDict[key] = value
            else:
                copy.itemDict[key] += value
        return copy
    
    def sum(list):
        if(not list): return ItemCost(None)
        ret = list[0]
        for item in list[1:]:
            ret = ret + item
        return ret

class Operator:
    def __init__(self,key,value):
        self.name = value["name"]
        self.id = key
        self.phases = value["phases"] #昇進段階
        self.skills = value["skills"] #スキル特化
        self.allSkills = value["allSkillLvlup"] #スキルLv1~7 
        self.idValue = value["idValue"] #実装順？
        self.cnOnly = value["cnOnly"] #大陸版限定オペレーターか
        self.uniqeEq = []

    def addEq(self,uniEq):
        self.uniqeEq.append(uniEq)

    def totalPhaseCost(self):
        costs = [ItemCost(item["evolveCost"]) for item in self.phases]
        return ItemCost.sum(costs)
    
    def totalSkillMasterCost(self):
        ret = {}
        for item in self.skills:
            costs = [ItemCost(x["levelUpCost"]) for x in item["levelUpCostCond"]]
            key = SkillIdToName.getStr(item["skillId"])
            ret[key] = ItemCost.sum(costs)
        return ItemCost.sum([x for x in ret.values()])

    def totalSkillLv7Cost(self):
        costs = [ItemCost(x["lvlUpCost"]) for x in self.allSkills]
        return ItemCost.sum(costs)
    
    def totalUniqueEQCost(self):
        ret = {}
        for item in self.uniqeEq:
            costDicts = item["itemCost"]
            key = item["uniEquipName"]
            if(not costDicts):
                ret[key] = ItemCost(None)
                continue
            costs = [ItemCost(costValue) for costKey,costValue in costDicts.items()]
            ret[key] = ItemCost.sum(costs)
        return ret
    
    def isCNOnly(self):
        return self.cnOnly

    def __repr__(self):
        return self.name

class AllOperatorsInfo:
    def __init__(self):
        self.operatorDict:Dict[str,Operator] = {}
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
            value["idValue"] = int(match.group(2))
            self.operatorDict[key] = Operator(key,value)
        
        allUEQ = get_json(UNI_EQ_URL_CN)["equipDict"]
        for key,value in allUEQ.items():
            charId = value["charId"]
            self.operatorDict[charId].addEq(value)
        
        operatorCNOnly = [x for x in self.operatorDict.values() if x.cnOnly]
        allCosts = ItemCost(None)
        for item in operatorCNOnly:
            print(item.name)
            allCosts = allCosts + item.totalPhaseCost()
            allCosts = allCosts + item.totalSkillLv7Cost()
            allCosts = allCosts + item.totalSkillMasterCost()
            #print(item.totalUniqueEQCost())
        #print(self.operatorDict)
        print(allCosts)
    
def main():
    a = AllOperatorsInfo()
    
if (__name__ == "__main__"):
    main()