import sys
import yaml
sys.path.append('../')
from rcutils import netutil
from typing import Dict
import re

get_json = netutil.get_json

ITEM_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/item_table.json"
ITEM_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData_YoStar/main/ja_JP/gamedata/excel/item_table.json"
class ItemIdToName:
    __idToStr = {}
    __ZHToJA = {}
    __ZHToid = {}
    __idToZH = {}
    __JAToid = {}
    def init():
        allInfoCN,allInfoJP = netutil.get_json_aio([ITEM_TABLE_URL_CN,ITEM_TABLE_URL_JP])
        allInfoCN = allInfoCN["items"]
        allInfoJP = allInfoJP["items"]
        ItemIdToName.__idToStr = {}
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
            else:
                jaName = customZHToJA.get(value["name"])
                if(jaName): 
                    ItemIdToName.__ZHToJA[value["name"]] = jaName
                    value["name"] = jaName
            ItemIdToName.__idToStr[key] = value["name"]
            ItemIdToName.__JAToid[value["name"]] = key
        
        #理性価値計算で使う特殊なアイテムのIDを入れる
        with open("./infoFromOuterSource/customItemId.yaml","rb") as file:
            customItems = yaml.safe_load(file)
        for item in customItems:
            if item["id"] in ItemIdToName.__idToStr.keys(): continue
            ItemIdToName.__idToStr[item["id"]] = item["ja"]
            ItemIdToName.__ZHToJA[item["zh"]] = item["ja"]
            ItemIdToName.__ZHToid[item["zh"]] = item["id"]
            ItemIdToName.__idToZH[item["id"]] = item["zh"]
            ItemIdToName.__JAToid[item["ja"]] = item["id"]
    
    def getStr(id:str)->str:
        if(not ItemIdToName.__idToStr):
            ItemIdToName.init()
        return ItemIdToName.__idToStr.get(id,"Missing")
    
    def zhToJa(zhStr:str)->str:
        if(not ItemIdToName.__ZHToJA):
            ItemIdToName.init()
        return ItemIdToName.__ZHToJA.get(zhStr,zhStr)
    
    def zhToId(zhStr:str)->str:
        if(not ItemIdToName.__ZHToid):
            ItemIdToName.init()
        return ItemIdToName.__ZHToid.get(zhStr,None)
    
    def jaToId(jaStr:str)->str:
        if(not ItemIdToName.__JAToid):
            ItemIdToName.init()
        return ItemIdToName.__JAToid.get(jaStr,None)
    
    def getZH(id:str)->str:
        if(not ItemIdToName.__idToZH):
            ItemIdToName.init()
        return ItemIdToName.__idToZH.get(id,"Missing")

SKILL_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/skill_table.json"
SKILL_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData_YoStar/main/ja_JP/gamedata/excel/skill_table.json"
class SkillIdToName:
    __idToStr = {}
    __idToDescription = {}
    def init():
        allInfoCN,allInfoJP = netutil.get_json_aio([SKILL_TABLE_URL_CN,SKILL_TABLE_URL_JP])
        SkillIdToName.__idToStr = {}
        for key,value in allInfoCN.items():
            jpValue = allInfoJP.get(key)
            if(jpValue):
                value = jpValue
            SkillIdToName.__idToStr[key] = value["levels"][0]["name"]
            #最大特化のスキル説明
            desription:str = value["levels"][-1]["description"]
            if(desription):
                bareplace1 = re.compile(r"<@ba\.[a-z]+>")
                desription = bareplace1.sub("",desription)
                bareplace2 = re.compile(r"<\$ba\.[a-z]+>")
                desription = bareplace2.sub("",desription)
                desription = desription.replace("</>","").replace("-{-","{").replace("{-","-{").replace("\\n","\n")
                def cleanStr(string:str)->str:
                    return string.replace("[","").replace("]","").replace(".","")
                desription = cleanStr(desription)
                desription = desription.replace(":0%",":.0%")
                rawDict = value["levels"][-1]["blackboard"]
                try:
                    def checkint(x:float):
                        if(x is None): return None
                        if(x==round(x)): return int(x)
                        return x
                    replaceDict = {cleanStr(item["key"]):checkint(item.get("value",None)) for item in rawDict}
                    if("duration" not in replaceDict):
                        replaceDict["duration"] = value["levels"][-1]["duration"]
                    replaceDict_upper = {key.upper():value for key,value in replaceDict.items()}
                    if(replaceDict):
                        try:
                            desription = desription.format(**replaceDict,**replaceDict_upper)
                            desription = desription.replace("--","")
                        except Exception as e:
                            print(f"{desription=}")
                            print(f"{replaceDict=}")
                            raise e
                except Exception as e:
                    print(f"{rawDict=}")
                    raise e
            else:
                desription = ""
            SkillIdToName.__idToDescription[key] = desription
    
    def getStr(id):
        if(not SkillIdToName.__idToStr):
            SkillIdToName.init()
        return SkillIdToName.__idToStr.get(id,"Missing")
    
    def getDescription(id):
        if(not SkillIdToName.__idToDescription):
            SkillIdToName.init()
        return SkillIdToName.__idToDescription.get(id,"")

STAGE_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/stage_table.json"
STAGE_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData_YoStar/main/ja_JP/gamedata/excel/stage_table.json"
class StageIdToName:
    __idToStr = {}
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
    
    def getStr(id):
        if(not StageIdToName.__idToStr):
            StageIdToName.init()
        return SkillIdToName.__idToStr.get(id,"Missing")

ZONE_TABLE_URL = "https://penguin-stats.io/PenguinStats/api/v2/zones"
class ZoneIdToName:
    __idToStr = {}
    def init():
        headers = {'User-Agent':'ArkPlanner'}
        allInfo = get_json(ZONE_TABLE_URL,headers=headers)
        ZoneIdToName.__idToStr = {}
        for items in allInfo:
            ZoneIdToName.__idToStr[items["zoneId"]] = items["zoneName_i18n"]["ja"]
    
    def getStr(id):
        if(not ZoneIdToName.__idToStr):
            ZoneIdToName.init()
        return ZoneIdToName.__idToStr.get(id,"Missing")