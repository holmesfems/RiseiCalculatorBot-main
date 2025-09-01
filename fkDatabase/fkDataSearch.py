from __future__ import annotations
import os
import sys
import json
sys.path.append("../")
from rcutils.netutil import get_json
from charmaterials.charmaterials import OperatorCostsCalculator
from infoFromOuterSource.idtoname import SkillIdToName
from rcutils.getnow import getnow
from typing import List,Dict,Tuple
from rcutils.rcReply import RCReply,RCMsgType
from datetime import datetime

SSKEY = os.environ["SSAPI"]
SSID = os.environ["SSID"]
SSNAME = "スキル一覧"

class SkillFKInfo:
    def __init__(self,operatorName:str,skillNum:str,fkNum:str,fkErr:str,detail:str,lastEdited:str,state:str):
        self.skillNum = skillNum
        self.skillName:str = ""
        while(True):
            if(not operatorName): break
            operatorSkills = OperatorCostsCalculator.operatorInfo.getOperatorCostFromName(operatorName)
            if(not operatorSkills): break
            idDict = {str(index+1):value for index,value in enumerate(operatorSkills.skillIds)}
            skillId = idDict.get(skillNum,"")
            if(not skillId): break
            skillName = SkillIdToName.getStr(skillId)
            self.skillName = skillName
            break
        self.fkNum = fkNum
        self.fkErr = fkErr
        self.detail = detail
        self.lastEdited = lastEdited
        self.state = state

    def isAvailable(self):
        return self.lastEdited != ""
    
    def nameOrNum(self):
        return self.skillName if self.skillName else self.skillNum

class OperatorFKInfo:
    def __init__(self,name):
        self.name = name
        self.skills:List[SkillFKInfo] = []

    def addSkill(self,skillFKInfo:SkillFKInfo):
        self.skills.append(skillFKInfo)

    def getSkillFromNum(self,skillNum:str):
        ret = [x for x in self.skills if x.skillNum == skillNum]
        if(ret): return ret[0]
        else:return None

    def hasOnlyOneSkill(self):
        return len(self.skills) == 1

class FKInfo:
    def __init__(self):
        self.fkData:Dict[str,OperatorFKInfo] = ...
        self.lastUpdated:datetime = ...
        self.update()

    def update(self):
        fkJson = get_json(f"https://sheets.googleapis.com/v4/spreadsheets/{SSID}/values/{SSNAME}",
               {"key":SSKEY})
        fkList:List[str] = fkJson["values"][2:]
        self.fkData = {}
        for item in fkList:
            if(len(item)<12): continue
            name = item[4]
            newSkillFKInfo = SkillFKInfo(
                operatorName = name,
                skillNum     = item[6],
                fkNum        = item[7],
                fkErr        = item[8],
                detail       = item[9],
                lastEdited   = item[10],
                state        = item[11]
            )
            if(not newSkillFKInfo.isAvailable()):continue
            if(not self.fkData.get(name)):
                self.fkData[name] = OperatorFKInfo(name)
            self.fkData[name].addSkill(newSkillFKInfo)
        self.lastUpdated = getnow()

    def autoComplete(self,name:str,limit:int = 25) -> List[Tuple[str,str]]:
        return [(value.name,value.name) for key,value in self.fkData.items() if name in value.name][:limit]
    
    def getInfoFromName(self,name):
        timeDiff = getnow() - self.lastUpdated
        if(timeDiff.total_seconds() >= 3600): self.update()
        return self.fkData.get(name,None)
    
    def getReply(self,name:str,skillNum:str):
        info = self.getInfoFromName(name)
        title = "FK情報検索"
        if(not info): return RCReply(
            embbedTitle=title,
            embbedContents=["指定のオペレーターのFK情報は見つかりませんでした"],
            msgType=RCMsgType.ERR,
            responseForAI="There is no FK info for this operator")
        if(skillNum.strip() == "" and not info.hasOnlyOneSkill()):
            skillDict = {x.skillNum: x.nameOrNum() for x in info.skills}
            return RCReply(
                embbedTitle=title,
                embbedContents=[f"複数のFKスキルがあります: {skillDict}",
                                f"どのスキルか選んでください"],
                msgType=RCMsgType.ERR,
                responseForAI=f"Please ask user to select a skill from following choices: {skillDict}")

        skillInfo = info.skills[0] if info.hasOnlyOneSkill() and skillNum.strip() == "" else info.getSkillFromNum(str(skillNum))
        if(not skillInfo): 
            candidates = [{
                "skillNum": x.skillNum,
                "skillName": x.skillName
            } for x in info.skills]
            return RCReply(
            embbedTitle=title,
            embbedContents=[f"指定のスキルのFK情報は見つかりませんでした。以下の候補がありますので、一つ選択してください: {str(candidates)}"],
            msgType=RCMsgType.ERR,
            responseForAI=f"This skill is not a FK skill. Available skills for this operator is as following: {json.dumps(candidates)}")
        return RCReply(
            embbedTitle=title,
            embbedContents=[
                f"スキル名: {skillInfo.skillName}\n" if skillInfo.skillName else f"スキル指定: {skillNum}\n",
                f"最短FK数: {skillInfo.fkNum}\n",
                f"FK誤差: {skillInfo.fkErr}\n",
                f"詳細情報: \n```\n{skillInfo.detail}\n```"
            ],
            responseForAI=json.dumps({
                "skillName": skillInfo.skillName,
                "fkNum": skillInfo.fkNum,
                "fkErr": skillInfo.fkErr,
                "detail": skillInfo.detail
            },ensure_ascii=False)
        )
    
fkInfo = FKInfo()