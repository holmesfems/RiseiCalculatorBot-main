import openai,os
import enum
from enum import StrEnum
import sys
sys.path.append('../')
from charmaterials.charmaterials import OperatorCostsCalculator
from riseicalculator2.riseicalculatorprocess import CalculatorManager,CalculateMode
import yaml
from riseicalculator2 import listInfo

with open("openaichat/functionList.yaml","rb") as f:
    functionList = yaml.safe_load(f)

#print(SYSTEM_PROMPT)
class ChatType(StrEnum):
    TEXT = enum.auto()
    FUNCTION = enum.auto()

class ChatReply:
    def __init__(self,type:ChatType, content:dict = {}, plainText:str = ""):
        self.type = type
        self.content = content
        self.plainText = plainText
    def __repr__(self):
        ret = f"ChatReply: Type = {self.type}\n"
        ret += f"{self.content=}\n"
        ret += f"{self.plainText=}\n"
        return ret

def functionCalling(functionName:str,functionArgs:dict) -> ChatReply:
    if(functionName == "riseimaterials"):
        target = functionArgs["target"]
        targetEstimated = listInfo.estimateCategoryFromJPName(target)
        return ChatReply(ChatType.FUNCTION,content=CalculatorManager.riseimaterials(targetEstimated,True,CalculateMode.SANITY),plainText=f"{target}の周回ステージを表示します：")
    elif(functionName == "riseistages"):
        targetEstimated = functionArgs["target"]
        autoComplete = CalculatorManager.calculatorForMainland.autoCompleteMainStage(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        return ChatReply(ChatType.FUNCTION,content=CalculatorManager.riseistages(targetEstimated,True,CalculateMode.SANITY),plainText=f"ステージ{targetEstimated}の理性効率を表示します：")
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
            return ChatReply(ChatType.FUNCTION,content=CalculatorManager.riseilists(toPrint,True,CalculateMode.SANITY),plainText=f"{targetEstimated}を表示します：")
        else:
            return ChatReply(ChatType.TEXT,plainText=f"{targetEstimated}の取得に失敗しました。名前が違うみたいですわ。")
    elif(functionName == "operatorelitecost"):
        targetEstimated = functionArgs["target"]
        autoComplete = OperatorCostsCalculator.autoCompleteForEliteCost(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        return ChatReply(ChatType.FUNCTION,content=OperatorCostsCalculator.operatorEliteCost(targetEstimated),plainText=f"{targetEstimated}の昇進必要素材を表示します：")
    elif(functionName == "operatormastercost"):
        targetEstimated = functionArgs["target"]
        number = functionArgs["number"]
        autoComplete = OperatorCostsCalculator.autoCompleteForMasterCost(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        return ChatReply(ChatType.FUNCTION,content=OperatorCostsCalculator.skillMasterCost(targetEstimated,number),plainText=f"{targetEstimated}スキル{number}の特化に必要素材を表示します：")
    elif(functionName == "operatormodulecost"):
        targetEstimated = functionArgs["target"]
        autoComplete = OperatorCostsCalculator.autoCompleteForModuleCost(targetEstimated)
        if(autoComplete):
            targetEstimated = autoComplete[0][1]
        return ChatReply(ChatType.FUNCTION,content=OperatorCostsCalculator.operatorModuleCost(targetEstimated),plainText=f"{targetEstimated}のモジュール強化に必要な素材を表示します：")

def openaichat(msgList) -> ChatReply:
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    openai.api_key = OPENAI_API_KEY
    with open("openaichat/systemPrompt.txt","r",encoding="utf-8_sig") as f:
        SYSTEM_PROMPT = f.read()
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content" : SYSTEM_PROMPT},
        ] + msgList,
        functions = functionList,
        function_call = "auto"
    )
    response_message = response["choices"][0]["message"]
    if not response_message.get("function_call"):
        return ChatReply(ChatType.TEXT,plainText=response_message["content"].strip())
    function_name = response_message["function_call"]["name"]
    function_args = yaml.safe_load(response_message["function_call"]["arguments"])
    print("function detected:")
    print(f"{function_name=}")
    print(f"{function_args=}")
    return functionCalling(function_name,function_args)

# def debug():
#     testmsg = [{
#         "role":"user",
#         "content":"夏の大三角について教えて"
#     }]
#     print(openaichat(testmsg))

# if(__name__ == "__main__"):
#     debug()