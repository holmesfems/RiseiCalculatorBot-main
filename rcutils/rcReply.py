from typing import List,Any
from enum import StrEnum
from discord import Embed,Colour,File
import enum
from os import PathLike

class RCMsgType(StrEnum):
    OK = enum.auto()
    ERR = enum.auto()

    def type(self) -> str:
        return str(self)
    def colour(self) -> Colour:
        if self is RCMsgType.OK:
            return Colour.from_str("0x8be02b")
        elif self is RCMsgType.ERR:
            return Colour.magenta()
        #default
        return Colour.from_str("0x8be02b")

def arrangementChunks(msgList:List[str], maxLength:int):
    chunks = []
    for item in msgList:
        if len(chunks) == 0:
            chunks.append(item)
        else:
            if(len(chunks[-1])+len(item)) <= maxLength:
                chunks[-1] += item
            else:
                chunks.append(item)
    return chunks

#アステシアちゃんbotの出力に使うデータクラス
#スパゲッティ化防止のため、いままでDictで応答を出力していたものを全てこれに置き換える
class RCReply:
    def __init__(self,plainText:str = "",embbedTitle:str = "",embbedContents:List[str] = [],responseForAI:str = "",attatchments:List[PathLike[Any]] | PathLike[Any] = None,msgType:RCMsgType = RCMsgType.OK):

        #plainText: 普通に表示するメッセージ
        self.plainText = plainText

        #embbedを作るときのタイトル
        self.embbedTitle = embbedTitle

        #embbedの内容
        #なるべく一つのページにまとまってほしいstrの塊のリスト
        self.embbedContents = embbedContents

        #ChatGPTから呼び出された場合、提供するResponse
        self.responseForAI = responseForAI

        #ファイル添付
        self.attatchments = attatchments

        #embbedの色をTypeで決める
        self.msgType = msgType

    def __repr__(self) -> str:
        ret = f"RCReply: {self.embbedTitle=}\n"
        ret += f"{self.plainText=}\n"
        ret += f"{self.embbedContents=}\n"
        ret += f"{self.responseForAI=}\n"
        ret += f"{self.attatchments=}\n"
        ret += f"{self.msgType=}"
        return ret
    
    def getEmbbeds(self)->List[Embed]:
        if(not self.embbedContents):
            return []
        title = self.embbedTitle
        if(not title):
            title = "Reply"
        
        MAXLENGTH = 1900
        chunks = arrangementChunks(self.embbedContents,MAXLENGTH)
        return [Embed(
            title = title,
            description=item,
            colour = self.msgType.colour()
        ) for item in chunks]
    
    def files(self) -> List[File]:
        if not self.attatchments:
            return []
        if(type(self.attatchments) is list):
            return [File(item) for item in self.attatchments]
        else: return [File(self.attatchments)]

    def isMSGEmpty(self) -> bool:
        return not self.plainText and not self.embbedContents and not self.attatchments