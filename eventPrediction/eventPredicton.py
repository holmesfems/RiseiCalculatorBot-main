from __future__ import annotations
import sys
sys.path.append('../')
from typing import List,Dict
from pydantic import BaseModel
from rcutils import netutil,getnow,rcReply
from datetime import datetime,timedelta
URL = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData_YoStar/refs/heads/main/ja_JP/gamedata/excel/activity_table.json"
get_json = netutil.get_json
CACHE_HOURS = 2

class EventInfo(BaseModel):
    id:str
    type:str
    displayType:str
    name:str
    startTime:int
    endTime:int
    rewardEndTime:int
    displayOnHome:bool
    hasStage:bool
    templateShopId:str|None
    medalGroupId:str|None
    ungroupedMedalIds:List[str]|None
    isReplicate:bool
    needFixedSync:bool
    trapDomainId:str|None
    recType:str
    isPageEntry:bool
    isMagnify:bool

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
    def isSideStory(self):
        return self.type.startswith("TYPE_ACT")

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
        elif(self.isSideStory):
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
    eventInfoDict = {key:EventInfo.model_validate(value) for key,value in basicInfo.items()}
    lastUpdated = getnow.getnow()

def getFutureEvents():
    __initIfNeed()
    now = getnow.getnow()
    title = "イベント予測"
    msgChunks = []
    nowEvents = {key:value for key,value in eventInfoDict.items() if value.startTime_datetime <= now and value.endTime_datetime >= now}
    sortedNowEvents = sorted([item for item in nowEvents.values()],key=lambda x: x.startTime)
    if(not sortedNowEvents):
        msgChunks.append("現在開催中のイベントはありません。\n")
    else:
        msgChunks.append("現在開催中のイベント：")
        for item in sortedNowEvents:
            msgChunks.append(item.toStrBlock())
    msgChunks.append("\n")
    futureEvents = {key:value for key,value in eventInfoDict.items() if value.startTime_datetime >= now}
    sortedFutureEvents = sorted([item for item in futureEvents.values()],key=lambda x: x.startTime)
    if(not sortedFutureEvents):
        msgChunks.append("開催確定のイベントはまだありません。\n")
    else:
        msgChunks.append("イベント予測情報:")
        for item in sortedFutureEvents:
            msgChunks.append(item.toStrBlock())
    return rcReply.RCReply(embbedTitle=title,embbedContents=msgChunks)

#特定の月でなんのイベントがあったかを調べる
def searchEventByStartDate(startYear:int|None, startMonth:int|None, sidestoryOnly:bool = True):
    __initIfNeed()
    now = getnow.getnow()
    if(startYear is None): startYear = now.year
    if(startMonth is None): startMonth = now.month
    filteredEvents = {key:value for key,value in eventInfoDict.items() if value.startTime_datetime.year == startYear and value.startTime_datetime.month == startMonth}
    if(sidestoryOnly): filteredEvents = {key:value for key,value in filteredEvents.items() if value.isSideStory}
    sortedEvents = sorted([item for item in filteredEvents.values()], key=lambda x: x.startTime)
    title = f"イベント検索：{startYear}年{startMonth}月"
    msgChunks = []
    if(not sortedEvents):
        msgChunks.append("該当時期のイベントは見つかりませんでした")
    else:
        msgChunks.append("以下のイベントが見つかりました:")
        for item in sortedEvents:
            msgChunks.append(item.toStrBlock())
    return rcReply.RCReply(embbedTitle=title,embbedContents=msgChunks)