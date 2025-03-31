from __future__ import annotations
import sys
sys.path.append('../')
from typing import List,Dict
from dataclasses import dataclass
from rcutils import netutil,getnow,rcReply
from datetime import datetime,timedelta
URL = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData_YoStar/refs/heads/main/ja_JP/gamedata/excel/activity_table.json"
get_json = netutil.get_json
CACHE_HOURS = 2

@dataclass
class EventInfo:
    id:str
    type:str
    displayType:str
    name:str
    startTime:int
    endTime:int
    rewardEndTime:int
    displayOnHome:bool
    hasStage:bool
    templateShopId:str
    medalGroupId:str
    ungroupedMedalIds:List[str]
    isReplicate:bool
    needFixedSync:bool
    trapDomainId:str
    recType:str
    isPageEntry:bool

    @property
    def startTime_datetime(self):
        return datetime.fromtimestamp(self.startTime,tz = getnow.JST)
    
    @property
    def endTime_datetime(self):
        return datetime.fromtimestamp(self.endTime,tz = getnow.JST)
    
    @property
    def rewardEndTime_datetime(self):
        return datetime.fromtimestamp(self.rewardEndTime,tz = getnow.JST)
    
    @property
    def eventType(self):
        if(self.type == "CHECKIN_ONLY"):
            return "スタンプラリー"
        elif(self.type == "APRIL_FOOL"):
            return "エイプリルフール"
        elif(self.type == "COLLECTION"):
            return "期間限定任務"
        elif(self.type == "LOGIN_ONLY"):
            return "ログインボーナス"
        elif(self.type.startswith("TYPE_ACT")):
            return "サイドストーリー"
        elif(self.type == "MINISTORY"):
            return "オムニバス"
        else:
            return "その他"

    def toStrBlock(self):
        return "```\n"+\
            f"イベント名  : {self.name}\n" +\
            f"開始時間    : {self.startTime_datetime.strftime('%Y/%m/%d %H:%M:%S')}\n" +\
            f"終了時間    : {self.endTime_datetime.strftime('%Y/%m/%d %H:%M:%S')}\n" +\
            f"報酬受取期限: {self.rewardEndTime_datetime.strftime('%Y/%m/%d %H:%M:%S')}\n" +\
            f"イベント形式: {self.eventType}" + "```"
    
    def __repr__(self):
        return self.toStrBlock()

eventInfoDict:Dict[str,EventInfo] = {}
lastUpdated:datetime = ...
def __initIfNeed():
    global eventInfoDict,lastUpdated
    now = getnow.getnow()
    if(eventInfoDict and now - lastUpdated <= timedelta(hours=CACHE_HOURS)): return
    basicInfo = get_json(URL)["basicInfo"]
    eventInfoDict = {key:EventInfo(**value) for key,value in basicInfo.items()}
    lastUpdated = getnow.getnow()

def getFutureEvents():
    __initIfNeed()
    now = getnow.getnow()
    futureEvents = {key:value for key,value in eventInfoDict.items() if value.startTime_datetime >= now}
    sortedEvents = sorted([item for item in futureEvents.values()],key=lambda x: x.startTime)
    title = "イベント予測"
    msgChunks = []
    if(not sortedEvents):
        msgChunks.append("開催が確定されたイベントは現在ありません")
    else:
        msgChunks.append("イベント予測情報:")
        for item in sortedEvents:
            msgChunks.append(item.toStrBlock())
    return rcReply.RCReply(embbedTitle=title,embbedContents=msgChunks)