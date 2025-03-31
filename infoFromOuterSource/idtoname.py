import sys
import yaml
sys.path.append('../')
from rcutils import netutil,strutil
from typing import Dict
import re

get_json = netutil.get_json

ITEM_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/item_table.json"
ITEM_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData_YoStar/main/ja_JP/gamedata/excel/item_table.json"
class ItemIdToName:
    __idToJA:Dict[str,str] = {}
    __ZHToJA:Dict[str,str] = {}
    __ZHToid:Dict[str,str] = {}
    __idToZH:Dict[str,str] = {}
    __JAToid:Dict[str,str] = {}
    @staticmethod
    def init():
        allInfoCN,allInfoJP = netutil.get_json_aio([ITEM_TABLE_URL_CN,ITEM_TABLE_URL_JP])
        allInfoCN:dict = allInfoCN["items"]
        allInfoJP:dict = allInfoJP["items"]
        ItemIdToName.__idToJA = {}
        ItemIdToName.__ZHToJA = {}
        ItemIdToName.__ZHToid = {}
        ItemIdToName.__idToZH = {}
        ItemIdToName.__JAToid = {}
        with open("./infoFromOuterSource/customItemZHToJA.yaml","rb") as file:
            customZHToJA:Dict[str,str] = yaml.safe_load(file)
        for key,value in allInfoCN.items():
            jpValue = allInfoJP.get(key)
            cnName = value["name"] 
            ItemIdToName.__ZHToid[cnName] = key
            ItemIdToName.__idToZH[key] = cnName
            if(jpValue):
                ItemIdToName.__ZHToJA[value["name"]] = jpValue["name"]
                value = jpValue
                ItemIdToName.__idToJA[key] = value["name"]
                ItemIdToName.__JAToid[value["name"]] = key
            else:
                jaName = customZHToJA.get(value["name"])
                if(jaName): 
                    ItemIdToName.__ZHToJA[value["name"]] = jaName
                    value["name"] = jaName
                    ItemIdToName.__idToJA[key] = value["name"]
                    ItemIdToName.__JAToid[value["name"]] = key
        
        for key,jpValue in allInfoJP.items(): #中国語情報での追加漏れを確認
            if(key in ItemIdToName.__idToZH): continue
            jpName = jpValue["name"]
            ItemIdToName.__idToJA[key] = jpName
            ItemIdToName.__JAToid[jpName] = key

            
        #理性価値計算で使う特殊なアイテムのIDを入れる
        with open("./infoFromOuterSource/customItemId.yaml","rb") as file:
            customItems = yaml.safe_load(file)
        for item in customItems:
            #中国語、日本語の情報が両方あるなら、スルー
            if item["id"] in ItemIdToName.__idToZH and item["id"] in ItemIdToName.__idToJA: continue
            if  item["id"] in ItemIdToName.__idToJA: #中国語情報のみ欠損
                jaName = ItemIdToName.__idToJA[item["id"]]
                ItemIdToName.__ZHToJA[item["zh"]] = jaName
                ItemIdToName.__ZHToid[item["zh"]] = item["id"]
                ItemIdToName.__idToZH[item["id"]] = item["zh"]
                continue
            if item["id"] in ItemIdToName.__idToZH: #日本語情報のみ欠損
                zhName = ItemIdToName.__idToZH[item["id"]]
                ItemIdToName.__ZHToJA[zhName] = item["ja"]
                ItemIdToName.__idToJA[item["id"]] = item["ja"]
                ItemIdToName.__JAToid[item["ja"]] = item["id"]
                continue
            #同じ情報(zh jaのセット)が既にある場合、更新によってcustomIDが古くなっているのでスルー 違うIDならこの項目に問題があるのでスルー
            if item["zh"] in ItemIdToName.__ZHToid and item["ja"] in ItemIdToName.__JAToid:continue
            if item["zh"] in ItemIdToName.__ZHToid: #中国語で対応するIDがある
                idStr = ItemIdToName.__ZHToid[item["zh"]]
                if(idStr in ItemIdToName.__idToJA): continue #正しい日本語が既にある
                #日本語について補足
                ItemIdToName.__idToJA[idStr] = item["ja"]
                ItemIdToName.__JAToid[item["ja"]] = idStr
                ItemIdToName.__ZHToJA[item["zh"]] = item["ja"]
                continue
            if item["ja"] in ItemIdToName.__JAToid: #日本語で対応するIDがある
                idStr = ItemIdToName.__JAToid[item["ja"]]
                if(idStr in ItemIdToName.__idToZH): continue #正しい中国語が既にある
                ItemIdToName.__ZHToid[item["zh"]]=idStr
                ItemIdToName.__ZHToJA[item["zh"]]=item["ja"]
                ItemIdToName.__idToZH[idStr] = item["zh"]
                continue

            #完全オリジナルモノ
            ItemIdToName.__idToJA[item["id"]]=item["ja"]
            ItemIdToName.__ZHToJA[item["zh"]]=item["ja"]
            ItemIdToName.__ZHToid[item["zh"]]=item["id"]
            ItemIdToName.__idToZH[item["id"]]=item["zh"]
            ItemIdToName.__JAToid[item["ja"]]=item["id"]

    @staticmethod
    def getStr(id:str)->str:
        if(not ItemIdToName.__idToJA):
            ItemIdToName.init()
        return ItemIdToName.__idToJA.get(id,ItemIdToName.__idToZH.get(id,"Missing"))
    
    @staticmethod
    def zhToJa(zhStr:str)->str:
        if(not ItemIdToName.__ZHToJA):
            ItemIdToName.init()
        return ItemIdToName.__ZHToJA.get(zhStr,zhStr)
    
    @staticmethod
    def zhToId(zhStr:str):
        if(not ItemIdToName.__ZHToid):
            ItemIdToName.init()
        return ItemIdToName.__ZHToid.get(zhStr,None)
    
    @staticmethod
    def jaToId(jaStr:str) :
        if(not ItemIdToName.__JAToid):
            ItemIdToName.init()
        return ItemIdToName.__JAToid.get(jaStr,None)
    
    @staticmethod
    def getZH(id:str)->str:
        if(not ItemIdToName.__idToZH):
            ItemIdToName.init()
        return ItemIdToName.__idToZH.get(id,"Missing")

SKILL_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/skill_table.json"
SKILL_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData_YoStar/main/ja_JP/gamedata/excel/skill_table.json"
class SkillIdToName:
    with open("infoFromOuterSource/skillmetacode.yaml",encoding="utf-8") as f:
        skillMetaDict:Dict[str,str] = yaml.safe_load(f)
    class SkillItem:
        def __init__(self,skillJson):
            self.name = skillJson["name"]
            description:str = skillJson["description"]
            if description:
                bareplace1 = re.compile(r"<@ba\.?[a-z0-9]+>")
                description = bareplace1.sub("",description)
                bareplace2 = re.compile(r"<\$ba\.?(dt\.)?[a-z0-9]+>")
                description = bareplace2.sub("",description)
                description = strutil.replace_byDict(description,{
                    "</>":"",
                    "-{-":"{",
                    "{-":"-{",
                    "\\n":"\n",
                    "AOE":"aoe"
                })
                def cleanStr(string:str)->str:
                    return string.replace("[","").replace("]","").replace(".","")
                description = cleanStr(description)
                description = description.replace(":0%",":.0%")
                rawDict = skillJson["blackboard"]
                try:
                    def checkint(x:float):
                        if(x is None): return None
                        if(x==round(x)): return int(x)
                        return x
                    replaceDict = {cleanStr(item["key"]):checkint(item.get("value",None)) for item in rawDict}
                    if("duration" not in replaceDict):
                        replaceDict["duration"] = skillJson["duration"]
                    replaceDict_upper = {key.upper():value for key,value in replaceDict.items()}
                    if(replaceDict):
                        try:
                            description = description.format(**replaceDict,**replaceDict_upper)
                            description = description.replace("--","")
                        except Exception as e:
                            print(f"{description=}")
                            print(f"{replaceDict=}")
                            raise e
                except Exception as e:
                    print(f"{rawDict=}")
                    raise e
                skillMetaDict = SkillIdToName.skillMetaDict
                self.__description = description
                #SP/発動情報を補足
                self.initSP:float = skillJson["spData"]["initSp"]
                self.totalSP:float = skillJson["spData"]["spCost"]
                self.skillType = skillMetaDict.get(skillJson["skillType"])
                self.spType = skillMetaDict.get(skillJson["spData"]["spType"])
                self.duration:float = skillJson["duration"]
            else:
                self.__description = ""

        @property
        def description(self):
            if(self.__description):
                skillTypeInfo = self.skillType if self.isPassive() else f"{self.spType}/{self.skillType}"
                if self.duration > 0:
                    skillTypeInfo += f" ⌚{self.duration}秒"
                spInfo = "" if(self.isPassive()) else f"▶{self.initSP} ⚡{self.totalSP}"
                preInfo = f"{skillTypeInfo}\n{spInfo}" if spInfo else skillTypeInfo
                return f"{preInfo}\n{self.__description}"
            else:
                return ""
            
        def isPassive(self):
            return self.hasDescription() and self.skillType == "パッシブ"

        def hasDescription(self):
            return bool(self.__description)
        
        def jsonForAI(self):
            if self.hasDescription():
                if self.isPassive():
                    return {
                        "name": self.name,
                        "skillType": self.skillType,
                        "description": self.description
                    }
                else:
                    return {
                        "name": self.name,
                        "skillType": self.skillType,
                        "initialSp": self.initSP,
                        "spCost": self.totalSP,
                        "spType": self.spType,
                        "description": self.description
                    }
            return {"name": self.name}
        
    __idToSkillItem:Dict[str,SkillItem] = {}

    @staticmethod
    def init():
        allInfoCN,allInfoJP = netutil.get_json_aio([SKILL_TABLE_URL_CN,SKILL_TABLE_URL_JP])
        SkillIdToName.__idToSkillItem = {}
        for key,value in allInfoCN.items():
            jpValue = allInfoJP.get(key)
            if(jpValue):
                value = jpValue
            SkillIdToName.__idToSkillItem[key] = SkillIdToName.SkillItem(value["levels"][-1])

    @staticmethod
    def getItem(id):
        if(not SkillIdToName.__idToSkillItem):
            SkillIdToName.init()
        return SkillIdToName.__idToSkillItem.get(id)
    
    @staticmethod
    def getStr(id):
        if(skillItem := SkillIdToName.getItem(id)):
            return skillItem.name
        else:
            return "Missing"
    
    @staticmethod
    def getDescription(id):
        if(skillItem := SkillIdToName.getItem(id)):
            return skillItem.description
        else:
            return ""

STAGE_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/stage_table.json"
STAGE_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData_YoStar/main/ja_JP/gamedata/excel/stage_table.json"
class StageIdToName:
    __idToStr:Dict[str,str] = {}

    @staticmethod
    def init():
        allInfoCN,allInfoJP = netutil.get_json_aio([STAGE_TABLE_URL_CN,STAGE_TABLE_URL_JP])
        allInfoCN = allInfoCN["stages"]
        allInfoJP = allInfoJP["stages"]
        StageIdToName.__idToStr = {}
        for key,value in allInfoCN.items():
            jpValue = allInfoJP.get(key)
            if(jpValue):
                value = jpValue
            StageIdToName.__idToStr[key] = value["code"]
    
    @staticmethod
    def getStr(id):
        if(not StageIdToName.__idToStr):
            StageIdToName.init()
        return StageIdToName.__idToStr.get(id,"Missing")

ZONE_TABLE_URL = "https://penguin-stats.io/PenguinStats/api/v2/zones"
class ZoneIdToName:
    __idToStr:Dict[str,str] = {}

    @staticmethod
    def init():
        headers = {'User-Agent':'ArkPlanner'}
        allInfo = get_json(ZONE_TABLE_URL,headers=headers)
        ZoneIdToName.__idToStr = {}
        for items in allInfo:
            ZoneIdToName.__idToStr[items["zoneId"]] = items["zoneName_i18n"]["ja"]
    
    @staticmethod
    def getStr(id):
        if(not ZoneIdToName.__idToStr):
            ZoneIdToName.init()
        return ZoneIdToName.__idToStr.get(id,"Missing")