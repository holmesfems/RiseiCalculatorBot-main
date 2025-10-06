from __future__ import annotations
import sys

from openai.types.responses.response_output_text import AnnotationContainerFileCitation, AnnotationFileCitation, AnnotationFilePath, AnnotationURLCitation
sys.path.append('../')
from rcutils.getnow import getnow
import openai
import yaml
import json
import os
from typing import Dict,List
from pathlib import Path
import datetime
from dataclasses import dataclass,field
from discord import Attachment
import requests
from charmaterials.charmaterials import OperatorCostsCalculator
from riseicalculator2.riseicalculatorprocess import CalculatorManager,CalculateMode
from riseicalculator2 import listInfo
from rcutils.rcReply import RCReply
from fkDatabase.fkDataSearch import fkInfo
from openaichat.assistantSession import AssistantSession,GPTError
from recruitment.recruitment import showHighStars
import base64
import traceback
from openai.types.responses.response_code_interpreter_tool_call import ResponseCodeInterpreterToolCall
import shutil

with open("openaichat/systemPrompt.txt","r",encoding="utf-8_sig") as f:
    SYSTEM_PROMPT = f.read()

with open("openaichat/toolList.yaml","rb") as f:
    TOOL_LIST = yaml.safe_load(f)

@dataclass
class ChatFile:
    bytesData:bytes
    filename:str = ""

@dataclass
class ChatReply:
    msg:str = ""
    fileList:List[ChatFile] = field(default_factory=list)
    rcReplies:List[RCReply] = field(default_factory=list)

def toolCalling(functionName:str,functionArgs:Dict[str,str]) -> RCReply:
    operator_typo_correction_dict = {
        "メラニート":"メラナイト"
    }
    def operator_typo_correction(operatorName:str):
        return operator_typo_correction_dict.get(operatorName,operatorName)

    if(functionName == "riseiMaterials"):
        #素材の理性効率を求める
        target = functionArgs["target"]
        targetEstimated = listInfo.estimateCategoryFromJPName(target)
        return CalculatorManager.riseimaterials(targetEstimated,True,CalculateMode.SANITY,maxItems=5)
    
    elif(functionName == "riseiStages"):
        #恒常ステージの理性効率を求める
        targetEstimated = functionArgs["target"]
        autoComplete = CalculatorManager.calculatorForMainland.autoCompleteMainStage(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        return CalculatorManager.riseistages(targetEstimated,True,CalculateMode.SANITY,maxItems=5)
    
    elif(functionName == "riseiLists"):
        #理性価値表等
        targetEstimated = functionArgs["target"]
        targetDict = {
            "Base stage table":"basemaps",
            "Sanity-Value table":"san_value_lists",
            "Commendation Certificate Efficiency table":"te2list",
            "Distinction Certificate Efficiency table":"te3list",
            "Special Exchange Order Efficiency table":"special_list",
            "Contract Bounty Efficiency table": "cclist",
            "Crystal Exchange Efficiency table": "polist",
            "Pinch-out Exchange Efficiency table": "polist",
        }
        printTarget = targetDict.get(targetEstimated,None)
        if(printTarget):
            toPrint = CalculatorManager.ToPrint(printTarget)
            return CalculatorManager.riseilists(toPrint,True,CalculateMode.SANITY)
        else:
            return RCReply(responseForAI=f"Error: list not found: {targetEstimated}")
        
    elif(functionName == "operatorEliteCost"):
        #オペレーター昇進コスト
        targetEstimated = functionArgs["target"]
        autoComplete = OperatorCostsCalculator.autoCompleteForEliteCost(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        targetEstimated = operator_typo_correction(targetEstimated)
        return OperatorCostsCalculator.operatorEliteCost(targetEstimated)
    
    elif(functionName == "operatorSkillInfo"):
        #スキル特化コスト
        targetEstimated = functionArgs["target"]
        number = functionArgs["skillnum"]
        autoComplete = OperatorCostsCalculator.autoCompleteForMasterCost(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        targetEstimated = operator_typo_correction(targetEstimated)
        # if(functionArgs["infoType"] == "Description"):
        #     return OperatorCostsCalculator.operatorSkillInfo(targetEstimated,number)
        # else:
        return OperatorCostsCalculator.skillMasterCost(targetEstimated,number)

    elif(functionName == "operatorModuleCost"):
        #モジュールコスト
        targetEstimated = functionArgs["target"]
        autoComplete = OperatorCostsCalculator.autoCompleteForModuleCost(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        targetEstimated = operator_typo_correction(targetEstimated)
        return OperatorCostsCalculator.operatorModuleCost(targetEstimated)
    
    elif(functionName == "operatorFKInfo"):
        #FK情報
        targetEstimated = functionArgs["target"]
        number = functionArgs.get("skillnum","")
        autoComplete = fkInfo.autoComplete(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        targetEstimated = operator_typo_correction(targetEstimated)
        return fkInfo.getReply(targetEstimated,number)
    
    elif(functionName == "getRecruitmentList"):
        #公開求人タグ検索
        star = functionArgs.get("star")
        isGlobal = functionArgs.get("isGlobal")
        return showHighStars(minStar=star,isGlobal=isGlobal)

    #全部ヒットしない場合、メソッド未実装である
    return RCReply(responseForAI=f"Error: function is not implemented: {functionName}")

class ChatSession:
    MODEL = "gpt-5"
    __client = openai.Client(api_key=os.environ["OPENAI_API_KEY"])
    def __init__(self,name:str, timeout = datetime.timedelta(minutes=10)):
        self.timeout = timeout
        self.name = name
        self.assistantSessionList:Dict[str,AssistantSession] = {}
    
    #セッションを復元
    def __loadSession(self,sessionId:str) -> AssistantSession:
        session = self.assistantSessionList.get(sessionId)
        if(session): return session
        session = AssistantSession(ChatSession.__client,ChatSession.MODEL,SYSTEM_PROMPT,TOOL_LIST)
        self.assistantSessionList[sessionId] = session
        return session
    
    __CLEARCOMMANDS = ["reset","clear"]
    __RETRYCOMMANDS = ["retry"]
    __CONTINUECOMMANDS = ["continue"]

    async def doChat(self, msg:str, threadName:str, attachments:List[Attachment]):
        session = self.__loadSession(threadName)
        now = getnow()
        if(msg in ChatSession.__CLEARCOMMANDS):
            session.reset()
            return ChatReply(msg="会話履歴をリセットしたわ。")
        elif(msg in ChatSession.__CONTINUECOMMANDS):
            session.touch()
            return ChatReply(msg="会話を延長したわ。")
        # 10分過ぎたら記憶をクリアする
        if(now - session.lastUpdated > self.timeout):
            session.reset()
        try:
            content = []
            if(msg not in ChatSession.__RETRYCOMMANDS):
                content.append({
                    "type": "input_text",
                    "text": msg
                })
                restAttachments = []
                #画像を添付
                for item in attachments:
                    if(item.width != None):
                        content.append({
                            "type": "input_image",
                            "image_url": item.url
                        })
                    else:
                        restAttachments.append(item)
                #残りのファイルを載せる
                attachmentIds= ChatSession.__uploadFile(restAttachments)
                for attachmentId in attachmentIds:
                    content.append({
                        "type": "input_file",
                        "file_id": attachmentId
                    })
                session.submitUserMsg(content)
            rcReplies = await ChatSession.__completeRun(session)
            ret = await ChatSession.__extractMsg(session)
            ret.rcReplies = rcReplies
            return ret
        except GPTError as e:
            return ChatReply(msg=e.text)
        except Exception as e:
            print(traceback.format_exc())
            return ChatReply(msg=f"ごめんなさい、エラーが発生したみたい。\n{e}")
    
    @staticmethod
    def __uploadFile(attachments:List[Attachment])->List[str]:
        if not attachments: return []
        print(f"detected attatchments: {attachments=}")
        return [ChatSession.__client.files.create(
            file=requests.get(item.url).content,
            purpose="user_data",
        ).id for item in attachments]

    @staticmethod
    async def __extractMsg(session:AssistantSession):
        msgList = session.responseHistory
        ret:List[str] = []
        files:List[ChatFile] = []
        interpreters:List[ResponseCodeInterpreterToolCall] = []
        for item in msgList:
            if(item.type == "message"):
                contents = item.content
                for content in contents:
                    if(content.type == "output_text"):
                        ret.append(content.text)
                        if(getattr(content,"annotations",None)):
                            annotations: List[AnnotationFileCitation | AnnotationURLCitation | AnnotationContainerFileCitation | AnnotationFilePath] = content.annotations
                            for annotation in annotations:
                                if(annotation.type == "container_file_citation"):
                                    containerId = annotation.container_id
                                    fileId = annotation.file_id
                                    cited_file = ChatSession.__client.containers.files.content.retrieve(file_id=fileId,container_id=containerId)
                                    files.append(ChatFile(cited_file.content,annotation.filename))

                                elif(annotation.type == "url_citation"):
                                    ret.append(f"url:[{annotation.title}]({annotation.url})")

                                elif(annotation.type == "file_citation"):
                                    fileId = annotation.file_id
                                    cited_file = ChatSession.__client.files.content(file_id=fileId)
                                    files.append(ChatFile(cited_file.content,annotation.filename))

                                elif(annotation.type == "file_path"):
                                    fileId = annotation.file_id
                                    cited_file = ChatSession.__client.files.content(file_id=fileId)
                                    files.append(ChatFile(cited_file.content,"file"))
                                else:
                                    print(f"Unknown Annotation:{annotation}")
                    elif(content.type == "refusal"):
                        ret.append(content.refusal)

            elif(item.type == "image_generation_call"):
                image_base64 = base64.b64decode(item.result)
                files.append(ChatFile(image_base64,"image.png"))
            elif(item.type == "code_interpreter_call"):
                interpreters.append(item)
        #interpreterのファイルが正しくannotateされなかった場合、ローカルで実行してファイルにする
        def readFile(path:str):
            with open(path,"rb") as f:
                content= f.read()
            return content
        def filename(path:str):
            return os.path.basename(path)
        if(len(interpreters) > 0 and len(files) == 0):
            print("expected file annotation, but has no file. try to exec code_interpreter locally")
            for interpreterItem in interpreters:
                print(f"try interpreter: {interpreterItem.id}")
                try:
                    work_dir = os.path.abspath(f"./{interpreterItem.id}")
                    Path(work_dir).mkdir(parents=True,exist_ok=True)
                    code = interpreterItem.code.replace("/mnt/data",work_dir)
                    g = {"__name__": "__main__"}
                    exec(compile(code, interpreterItem.id, "exec"),g,g)
                    foundFiles = []
                    for p in Path(work_dir).rglob("*"):
                        if(p.is_file()):
                            files.append(ChatFile(readFile(p),filename(p)))
                            foundFiles.append(p.name)
                    print(f"succeed: files={foundFiles}")
                    shutil.rmtree(work_dir)
                    print("temporary files have been deleted.")

                except Exception as e:
                    print(f"error occured while running {interpreterItem.id}: {e}")

        return ChatReply(msg = "\n".join(ret), fileList=files)
        
    @staticmethod
    async def __completeRun(session:AssistantSession):
        ret = []
        response = await session.requestByHistory(isUser=True)
        while(True):
            hasFunction = False
            for output in response:
                if(output.type == "function_call"):
                    hasFunction = True
                    functionId = output.call_id
                    functionName = output.name
                    print(f"function detected: {functionName}, {output.arguments}")
                    functionArgs = json.loads(output.arguments)
                    functionResult = toolCalling(functionName=functionName,functionArgs=functionArgs)
                    ret.append(functionResult)
                    print(f"function result: {functionResult.responseForAI}")
                    session.submitToolResponse(functionResult.responseForAI,functionId)
            if(hasFunction):
                response = await session.requestByHistory(isUser=False)
            else: break
        return ret
    
class ChatSessionManager:
    __process = ChatSession("astesia_assistant")
    @staticmethod
    async def doChat(threadName:str,msg:str,attachments:List[Attachment]):
        reply = await ChatSessionManager.__process.doChat(msg,threadName,attachments)
        return reply