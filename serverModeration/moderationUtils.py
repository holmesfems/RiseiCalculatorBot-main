import discord
import os,sys
sys.path.append('../')
from rcutils.rcReply import RCReply
from rcutils.sendReplyToDiscord import sendToDiscord
from rcutils.getnow import getnow,JST
from typing import Union
import re

def _hasEveryone(text:str):
    return "@everyone" in text

# http/https、www、裸ドメイン(例: example.com/path)を検出
_URL_RE = re.compile(r"""
(?<![A-Za-z0-9])(
    (?:https?://|ftp://)[^\s<>'"]+              # スキーム付き
  | (?:www\.)[^\s<>'"]+                         # www.で始まるもの
  | (?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+ # 裸ドメイン
    (?:[A-Za-z]{2,})(?:/[^\s<>'"]*)?            # TLDと任意のパス
)
""", re.IGNORECASE | re.VERBOSE)

def _contains_link(text: str) -> bool:
    if not text:
        return False
    return bool(_URL_RE.search(text))

class serverModerator:
    def __init__(self, reportChannel:discord.TextChannel) -> None:
        self.reportChannel = reportChannel

    async def moderingMSG(self,message:discord.Message,userIsAdmin:bool):
        #指定したチャンネルは、追加したメッセージをすべて削除
        autoDeleted = await self.autoDeletion(message,userIsAdmin)
        autoAnniversaried = await self.autoAnniversary(message)
        #良さげなBANワードを思いついてないので、autoBanは一旦機能オフにする
        # if(not doneAny): doneAny = await self.autoBan(message)

        messageNeedDiscard = autoDeleted
        return messageNeedDiscard

    async def autoDeletion(self,message:discord.Message,userIsAdmin:bool) -> bool:
        TARGET_CHANNNEL_IDS = [
            int(os.environ["AUTODEL_1"]),
            int(os.environ["AUTODEL_2"]),
            int(os.environ["AUTODEL_3"]),
            int(os.environ["AUTODEL_4"]),
            int(os.environ["AUTODEL_5"]),
            int(os.environ["AUTODEL_6"])
        ]
        if(userIsAdmin): return False #管理者はチェックを免除
        if message.channel.id in TARGET_CHANNNEL_IDS:
            await message.delete()
            await self.autoBan_inAutoDeletion(message)
            return True
        else:
            return await self.autoNoticeAndBan(message)
    
    async def autoBan_inAutoDeletion(self,message:discord.Message) -> bool:
        #このチャンネルは人間がしゃべることを想定していないので、ここで誤検出は恐れなくてよい。
        #漏れをなるべく減らす方向でBANワードを作る
        BANWORDS = [
            "discord.gg",
            "http",
            "everyone",
            "peach"
        ]
        haslink = _contains_link(message.content)
        if haslink or any(word in message.content.lower() for word in BANWORDS):
            await message.author.ban(delete_message_days=7,reason="Auto-banned by the Astesia bot for sending spam messages")
            await self.createReport("スパムメッセージを検出したので、自動BANを実行しました。",message)
            return True
        return False

    async def autoNoticeAndBan(self,message:discord.Message) -> bool:
        #運用の結果、誤検出そこまでなさそうなため、BANをする
        text = message.content
        if(_hasEveryone(text) and _contains_link(text)):
            #@everyoneを含み、リンクがあるメッセージはBANします。
            #ここを通る時点で管理者出ないことが確定して、管理者以外がeveryone使うのはおかしい
            await message.author.ban(delete_message_days=7,reason="Auto-banned by the Astesia bot for sending spam messages")
            await self.createReport("通常チャットでスパムメッセージを検出しました。自動BANを実行しました",message)
            return True
        return False
    
    #一周年ロールを付ける機能
    async def autoAnniversary(self,message:discord.Message) -> bool:
        user = message.author
        #botには一周年ロールを付けない
        if(user.bot): return False
        #DMではロールを付けない
        if(not isinstance(user,discord.Member)): return False
        nowtime = getnow()
        joinedtime = user.joined_at
        anniRoleID = int(os.environ.get("ANNIROLEID"))
        if(joinedtime == None):
            return False
        joinedtime = joinedtime.astimezone(JST)
        #一周年ロールがある場合、付けない
        if(any([anniRoleID == role.id for role in user.roles])):
            return False
        canGetRole = (nowtime.year - joinedtime.year >= 2) or \
            (nowtime.year - joinedtime.year >= 1 and nowtime.month >= joinedtime.month)
        if(not canGetRole): return False

        anniRole = user.guild.get_role(anniRoleID)
        if(not anniRole): return False

        await user.add_roles(anniRole)
        #await self.createReport(f"{user.name} さんに一周年ロールを付けました！",None)
        return True

    async def createReport(self,report:str, message:discord.Message|None) -> None:
        content = f"{report}\n"
        if(message):
            content += f"author:{message.author.name}\n"
            content += f"content:```{message.content.replace('.','_').replace('http','ht tp')}```\n"
            content += f"channel:{message.channel.jump_url}"
        await sendToDiscord(self.reportChannel,RCReply(plainText=content))
