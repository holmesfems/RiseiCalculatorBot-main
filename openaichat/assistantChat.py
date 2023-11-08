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

from charmaterials.charmaterials import OperatorCostsCalculator
from riseicalculator2.riseicalculatorprocess import CalculatorManager,CalculateMode
from riseicalculator2 import listInfo
from rcutils.rcReply import RCReply

with open("openaichat/systemPrompt.txt","r",encoding="utf-8_sig") as f:
    SYSTEM_PROMPT = f.read()



def toolCalling(functionName:str,functionArgs:Dict[str,str]) -> RCReply:
    if(functionName == "riseimaterials"):
        target = functionArgs["target"]
        targetEstimated = listInfo.estimateCategoryFromJPName(target)
        return CalculatorManager.riseimaterials(targetEstimated,True,CalculateMode.SANITY,maxItems=5)
    elif(functionName == "riseistages"):
        targetEstimated = functionArgs["target"]
        autoComplete = CalculatorManager.calculatorForMainland.autoCompleteMainStage(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        return CalculatorManager.riseistages(targetEstimated,True,CalculateMode.SANITY,maxItems=5)
    elif(functionName == "riseilists"):
        targetEstimated = functionArgs["target"]
        targetDict = {
            "基準マップ":"basemaps",
            "理性価値表":"san_value_lists",
            "初級資格証効率表":"te2list",
            "初級効率表":"te2list",
            "上級資格証効率表":"te3list",
            "上級効率表":"te3list",
            "特別引換証効率表":"special_list",
            "特別効率表":"special_list",
            "契約賞金引換効率表": "cclist",
            "契約賞金効率表": "cclist",
        }
        printTarget = targetDict.get(targetEstimated,None)
        if(printTarget):
            toPrint = CalculatorManager.ToPrint(printTarget)
            return CalculatorManager.riseilists(toPrint,True,CalculateMode.SANITY)
        else:
            return RCReply(responseForAI=f"Error: list not found: {targetEstimated}")
    elif(functionName == "operatorelitecost"):
        targetEstimated = functionArgs["target"]
        autoComplete = OperatorCostsCalculator.autoCompleteForEliteCost(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        return OperatorCostsCalculator.operatorEliteCost(targetEstimated)
    elif(functionName == "operatormastercost"):
        targetEstimated = functionArgs["target"]
        number = functionArgs["skillnum"]
        autoComplete = OperatorCostsCalculator.autoCompleteForMasterCost(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        return OperatorCostsCalculator.skillMasterCost(targetEstimated,number)
    elif(functionName == "operatormodulecost"):
        targetEstimated = functionArgs["target"]
        autoComplete = OperatorCostsCalculator.autoCompleteForModuleCost(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        return OperatorCostsCalculator.operatorModuleCost(targetEstimated)
    return RCReply(responseForAI=f"Error: function is not implemented: {functionName}")

class ChatSession:
    MODEL = "gpt-4-1106-preview"
    __client = openai.Client(api_key=os.environ["OPENAI_API_KEY"])
    def __init__(self,name:str, timeout = datetime.timedelta(minutes=10)):
        self.timeout = timeout
        self.name = name
        self.assistantSession = self.loadSession()
        self.threads:Dict[str,Thread] = {}
        self.lastRepliedTime:Dict[str,datetime.datetime] = {}
    
    #セッションを復元
    def loadSession(self) -> Assistant:
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
    
    async def doChat(self, msg:str, threadName:str) -> Tuple[List[str],List[RCReply]]:
        thread = self.threads.get(threadName,ChatSession.newThread())
        now = getnow()
        lastReplied = self.lastRepliedTime.get(threadName,now)

        if(now - lastReplied > self.timeout):
            # 10分過ぎたら記憶をクリアして新しいセッションを始める
            thread = self.newThread()
        message = ChatSession.__client.beta.threads.messages.create(
            thread_id=thread.id,
            role = "user",
            content=msg
        )
        run = ChatSession.__client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistantSession.id
        )
        rcReplies = await ChatSession.__completeRun(run)
        if(run.status != "completed"):
            print(f"status is not completed: {run=}")
            return ["failed"]
        
        ret = await ChatSession.__extractMsg(thread)
        self.threads[threadName] = thread
        self.lastRepliedTime[threadName] = getnow()
        return (ret,rcReplies)
        
    @staticmethod
    async def __extractMsg(thread:Thread):
        msgList = ChatSession.__client.beta.threads.messages.list(thread_id=thread.id)
        messages = msgList.data
        new_messages:List[ThreadMessage] = []
        for item in messages:
            if(item.role == "user"): break
            new_messages.append(item)
        ret:List[str] = []
        for item in new_messages:
            msgValue = item.content[0].text.value
            annotations = item.content[0].text.annotations
            citations = []
            for index, annotation in enumerate(annotations):
                msgValue = msgValue.replace(annotation.text, f' [{index}]')

                if (file_citation := getattr(annotation, 'file_citation', None)):
                    cited_file = ChatSession.__client.files.retrieve(file_citation.file_id)
                    citations.append(f'[{index}] {file_citation.quote} from {cited_file.filename}')
                elif (file_path := getattr(annotation, 'file_path', None)):
                    cited_file = ChatSession.__client.files.retrieve(file_path.file_id)
                    citations.append(f'[{index}] Click <here> to download {cited_file.filename}')
            ret.append(msgValue + "\n" + "\n".join(citations))
        return ret
        
    @staticmethod
    async def __waitRun(run:Run):
        while True:
            run = ChatSession.__client.beta.threads.runs.retrieve(run.id,thread_id=thread.id)
            if(run.status not in ["queued", "in_progress"]):
                return
            await asyncio.sleep(1)

    @staticmethod
    async def __completeRun(run:Run) -> List[RCReply]:
        ret = []
        while True:
            await ChatSession.__waitRun(run)
            if(run.status in ["completed","failed","cancelled","expired"]): return ret
            if(run.status == "requires_action"):
                actions = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                for action in actions:
                    functionName = action.function.name
                    functionArgs = json.loads(action.function.arguments)
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

    @staticmethod
    def newThread() -> Thread:
        return ChatSession.__client.beta.threads.create()
    
class ChatSessionManager:
    __process = ChatSession("astesia_assistant")
    async def doChat(threadName:str,msg:str):
        reply = await ChatSessionManager.__process.doChat(msg,threadName)
        return reply