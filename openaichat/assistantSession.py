from __future__ import annotations
import sys
from typing import List

from openai.types.responses.response_code_interpreter_tool_call import ResponseCodeInterpreterToolCall
from openai.types.responses.response_computer_tool_call import ResponseComputerToolCall
from openai.types.responses.response_custom_tool_call import ResponseCustomToolCall
from openai.types.responses.response_file_search_tool_call import ResponseFileSearchToolCall
from openai.types.responses.response_function_tool_call import ResponseFunctionToolCall
from openai.types.responses.response_function_web_search import ResponseFunctionWebSearch
from openai.types.responses.response_output_item import ImageGenerationCall, LocalShellCall, McpApprovalRequest, McpCall, McpListTools
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_reasoning_item import ResponseReasoningItem
sys.path.append('../')
import openai
import os
import asyncio
from rcutils.getnow import getnow

class GPTError(Exception):
    def __init__(self, text=""):
        self.text = text

class AssistantSession:
    def __init__(self,client:openai.OpenAI,model:str,instruction:str,tools:dict):
        self.model = model
        self.instruction = instruction
        self.tools = tools
        self.msgHistory = list()
        self.responseHistory:List[ResponseOutputMessage|ResponseCodeInterpreterToolCall|ImageGenerationCall] = list()
        self.lastID:str = None
        self.client = client
        self.lastUpdated = getnow()

    def __updateTime(self):
        self.lastUpdated = getnow()

    def submitToolResponse(self,msg:str,toolId:str):
        self.msgHistory.append({
            "type": "function_call_output",
            "call_id": toolId,
            "output": msg
        })
    
    def submitUserMsg(self,content):
        self.msgHistory.append({
            "role": "user",
            "content": content
        })

    def reset(self):
        self.msgHistory.clear()
        self.responseHistory.clear()
        self.lastID = None
        self.__updateTime()

    def touch(self):
        self.__updateTime()

    async def requestByHistory(self,isUser = True):
        if(isUser): self.responseHistory.clear()
        response = self.client.responses.create(
            model=self.model,
            input=self.msgHistory,
            tools=self.tools,
            instructions=self.instruction,
            previous_response_id=self.lastID,
            background=True
        )
        waited:int = 0
        while response.status in {"queued", "in_progress"}:
            await asyncio.sleep(1)
            waited +=1
            response=self.client.responses.retrieve(response_id=response.id)
            if(waited%5==0):
                print(f"waited for {waited}s, now status = {response.status}")
        self.__updateTime()
        self.msgHistory.clear()
        self.lastID = response.id
        if(response.status != "completed"):
            raise GPTError(f"response is not completed: {response.error.message}")
        output: List[ResponseOutputMessage | ResponseFileSearchToolCall | ResponseFunctionToolCall | ResponseFunctionWebSearch | ResponseComputerToolCall | ResponseReasoningItem | ImageGenerationCall | ResponseCodeInterpreterToolCall | LocalShellCall | McpCall | McpListTools | McpApprovalRequest | ResponseCustomToolCall]= response.output
        for item in output:
            if(item.type in ["message","image_generation_call","code_interpreter_call"]):
                self.responseHistory.append(item)
        return output
