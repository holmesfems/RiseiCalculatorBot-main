from __future__ import annotations
import sys
sys.path.append('../')
from rcutils.getnow import getnow
import openai
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread
from openai.types.beta.threads import ThreadMessage,Run
import yaml
import asyncio
import json
import os
from typing import Dict,List,Tuple
import datetime
from dataclasses import dataclass,field
from discord import Attachment
import requests,pathlib
from charmaterials.charmaterials import OperatorCostsCalculator
from riseicalculator2.riseicalculatorprocess import CalculatorManager,CalculateMode
from riseicalculator2 import listInfo
from rcutils.rcReply import RCReply

with open("openaichat/systemPrompt.txt","r",encoding="utf-8_sig") as f:
    SYSTEM_PROMPT = f.read()

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

    elif(functionName == "operatormodulecost"):
        #モジュールコスト
        targetEstimated = functionArgs["target"]
        autoComplete = OperatorCostsCalculator.autoCompleteForModuleCost(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        targetEstimated = operator_typo_correction(targetEstimated)
        return OperatorCostsCalculator.operatorModuleCost(targetEstimated)
    
    #全部ヒットしない場合、メソッド未実装である
    return RCReply(responseForAI=f"Error: function is not implemented: {functionName}")

class ChatSession:
    MODEL = "gpt-4-1106-preview"
    __client = openai.Client(api_key=os.environ["OPENAI_API_KEY"])
    def __init__(self,name:str, timeout = datetime.timedelta(minutes=10)):
        self.timeout = timeout
        self.name = name
        self.assistantSession = self.__loadSession()
        self.threads:Dict[str,Thread] = {}
        self.lastRepliedTime:Dict[str,datetime.datetime] = {}
    
    #セッションを復元
    def __loadSession(self) -> Assistant:
        assistantList = ChatSession.__client.beta.assistants.list(order="desc")
        assistant = next(filter(lambda x: x.name == self.name,assistantList),None)

        with open("openaichat/toolList.yaml","rb") as f:
            toolList = yaml.safe_load(f)

        if assistant is None:
            print("create new assistant")
            return ChatSession.__client.beta.assistants.create(
                model=ChatSession.MODEL,
                name=self.name,
                instructions=SYSTEM_PROMPT,
                tools=toolList,
            )
        print("load existing assistant")
        ChatSession.__client.beta.assistants.update(
            assistant_id=assistant.id,
            model=ChatSession.MODEL,
            instructions=SYSTEM_PROMPT,
            tools=toolList
        )
        return assistant
    
    def __deleteThread(self,threadName:str):
        if(self.threads.get(threadName)):
            del self.threads[threadName]
        if(self.lastRepliedTime.get(threadName)):
            del self.lastRepliedTime[threadName]
    
    __CLEARCOMMANDS = ["reset","clear"]

    async def doChat(self, msg:str, threadName:str, attachments:List[Attachment]) -> ChatReply:
        if(msg in ChatSession.__CLEARCOMMANDS):
            self.__deleteThread(threadName)
            return ChatReply(msg="会話履歴をリセットしたわ。")
        thread = self.threads.get(threadName,ChatSession.__newThread())
        now = getnow()
        lastReplied = self.lastRepliedTime.get(threadName,now)
        # 10分過ぎたら記憶をクリアして新しいセッションを始める
        if(now - lastReplied > self.timeout):
            thread = self.__newThread()
        
        #添付ファイルがある場合はそれを載せる
        message = ChatSession.__client.beta.threads.messages.create(
            thread_id=thread.id,
            role = "user",
            content=msg,
            file_ids=ChatSession.__uploadFile(attachments)
        )
        run = ChatSession.__client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistantSession.id
        )
        run,rcReplies = await ChatSession.__completeRun(run,thread)
        if(run.status != "completed"):
            print(f"status is not completed: {run=}")
            return ChatReply(msg="failed")
        
        ret = await ChatSession.__extractMsg(thread)
        self.threads[threadName] = thread
        self.lastRepliedTime[threadName] = getnow()
        ret.rcReplies = rcReplies
        return ret
    
    @staticmethod
    def __uploadFile(attachments:List[Attachment]):
        if not attachments: return []
        print(f"detected attatchments: {attachments=}")
        return [ChatSession.__client.files.create(
            file=requests.get(item.url).content,
            purpose="assistants",
        ).id for item in attachments]

    @staticmethod
    async def __extractMsg(thread:Thread):
        msgList = ChatSession.__client.beta.threads.messages.list(thread_id=thread.id)
        messages = msgList.data
        new_messages:List[ThreadMessage] = []
        for item in messages:
            if(item.role == "user"): break
            new_messages.append(item)
        ret:List[str] = []
        files:List[ChatFile] = []
        for item in new_messages:
            msgContent = item.content[0]
            if(msgContent.type == "image_file"):
                image = ChatSession.__client.files.with_raw_response.retrieve_content(msgContent.image_file.file_id)
                files.append(ChatFile(image.content,"image.png"))
                continue
            msgValue = msgContent.text.value
            annotations = item.content[0].text.annotations
            citations = []
            for index, annotation in enumerate(annotations):
                if (file_citation := getattr(annotation, 'file_citation', None)):
                    msgValue = msgValue.replace(annotation.text, f' [{index}]')
                    cited_file = ChatSession.__client.files.retrieve(file_citation.file_id)
                    citations.append(f'[{index}] {file_citation.quote} from {cited_file.filename}')
                elif (file_path := getattr(annotation, 'file_path', None)):
                    cited_file = ChatSession.__client.files.retrieve(file_path.file_id)
                    file = ChatSession.__client.files.with_raw_response.retrieve_content(cited_file.id)
                    msgValue = msgValue.replace(annotation.text, f'{file.url}')
                    files.append(ChatFile(file.content,pathlib.Path(cited_file.filename).name))
            ret.append(msgValue + "\n" + "\n".join(citations))
        return ChatReply(msg = "\n".join(ret), fileList=files)
        
    @staticmethod
    async def __waitRun(run:Run,thread:Thread):
        i = 0
        while True:
            run = ChatSession.__client.beta.threads.runs.retrieve(run.id,thread_id=thread.id)
            if(i%5 == 0):
                print(f"waiting, now = {i} seconds")
            if(run.status not in ["queued", "in_progress"]):
                break
            i += 1
            await asyncio.sleep(1)
        return run

    @staticmethod
    async def __completeRun(run:Run,thread:Thread):
        ret = []
        while True:
            run = await ChatSession.__waitRun(run,thread)
            if(run.status in ["completed","failed","cancelled","expired"]): break
            if(run.status == "requires_action"):
                actions = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                for action in actions:
                    functionName = action.function.name
                    functionArgs = json.loads(action.function.arguments)
                    print(f"function detected: {functionName=}, {functionArgs=}")
                    functionRes = toolCalling(functionName,functionArgs)
                    if(not functionRes.isMSGEmpty()):ret.append(functionRes)
                    tool_outputs.append({
                        "tool_call_id": action.id,
                        "output": functionRes.responseForAI
                    })
                run = ChatSession.__client.beta.threads.runs.submit_tool_outputs(
                    run.id,
                    thread_id=run.thread_id,
                    tool_outputs=tool_outputs
                )
        return (run,ret)

    @staticmethod
    def __newThread() -> Thread:
        return ChatSession.__client.beta.threads.create()
    
class ChatSessionManager:
    __process = ChatSession("astesia_assistant")
    async def doChat(threadName:str,msg:str,attachments:List[Attachment]):
        reply = await ChatSessionManager.__process.doChat(msg,threadName,attachments)
        return reply