import sys
if __name__ != "__main__":
    sys.path.append('../')
from rcutils import netutil

get_json = netutil.get_json

ITEM_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/item_table.json"
ITEM_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/ja_JP/gamedata/excel/item_table.json"

class ItemIdToName:
    __idToStr = {}
    __ZHToJA = {}
    __ZHToid = {}
    __idToZH = {}
    def init():
        allInfoCN = get_json(ITEM_TABLE_URL_CN)["items"]
        allInfoJP = get_json(ITEM_TABLE_URL_JP)["items"]
        ItemIdToName.__idToStr = {}
        ItemIdToName.__ZHToJA = {}
        ItemIdToName.__ZHToid = {}
        ItemIdToName.__idToZH = {}
        for key,value in allInfoCN.items():
            jpValue = allInfoJP.get(key)
            cnName = value["name"] 
            ItemIdToName.__ZHToid[cnName] = key
            ItemIdToName.__idToZH[key] = cnName
            if(jpValue):
                ItemIdToName.__ZHToJA[value["name"]] = jpValue["name"]
                value = jpValue
            ItemIdToName.__idToStr[key] = value["name"]
    
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
    
    def getZH(id:str)->str:
        if(not ItemIdToName.__idToZH):
            ItemIdToName.init()
        return ItemIdToName.__idToZH.get(id,"Missing")

SKILL_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/skill_table.json"
SKILL_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/ja_JP/gamedata/excel/skill_table.json"

class SkillIdToName:
    __idToStr = {}
    def init():
        allInfoCN = get_json(SKILL_TABLE_URL_CN)
        allInfoJP = get_json(SKILL_TABLE_URL_JP)
        SkillIdToName.__idToStr = {}
        for key,value in allInfoCN.items():
            jpValue = allInfoJP.get(key)
            if(jpValue):
                value = jpValue
            SkillIdToName.__idToStr[key] = value["levels"][0]["name"]
    
    def getStr(id):
        if(not SkillIdToName.__idToStr):
            SkillIdToName.init()
        return SkillIdToName.__idToStr.get(id,"Missing")
    
def initall():
    initList = [ItemIdToName,SkillIdToName]
    for item in initList:
        try:
            item.init()
        except Exception as e:
            print(e)

def __debug():
    print(ItemIdToName.zhToJa("凝胶"))

if __name__ == "__main__":
    __debug()

STAGE_TABLE_URL_CN = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/stage_table.json"
STAGE_TABLE_URL_JP = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/ja_JP/gamedata/excel/stage_table.json"
class StageIdToName:
    __idToStr = {}
    def init():
        allInfoCN = get_json(STAGE_TABLE_URL_CN)["stages"]
        allInfoJP = get_json(STAGE_TABLE_URL_JP)["stages"]
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
headers = {'User-Agent':'ArkPlanner'}
class ZoneIdToName:
    __idToStr = {}
    def init():
        allInfo = get_json(ZONE_TABLE_URL,headers=headers)
        ZoneIdToName.__idToStr = {}
        for items in allInfo:
            ZoneIdToName.__idToStr[items["zoneId"]] = items["zoneName_i18n"]["ja"]
    
    def getStr(id):
        if(not ZoneIdToName.__idToStr):
            ZoneIdToName.init()
        return ZoneIdToName.__idToStr.get(id,"Missing")