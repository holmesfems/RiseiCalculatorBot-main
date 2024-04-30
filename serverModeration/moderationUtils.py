import discord
import os,sys
sys.path.append('../')
from rcutils.rcReply import RCReply
from rcutils.sendReplyToDiscord import sendToDiscord
class serverModerator:
    def __init__(self, reportChannel:discord.TextChannel) -> None:
        self.reportChannel = reportChannel

    async def moderingMSG(self,message:discord.Message):
        #指定したチャンネルは、追加したメッセージをすべて削除
        doneAny = await self.autoDeletion(message)
        #良さげなBANワードを思いついてないので、autoBanは一旦機能オフにする
        # if(not doneAny): doneAny = await self.autoBan(message)
        return doneAny

    async def autoDeletion(self,message:discord.Message) -> bool:
        TARGET_CHANNNEL_IDS = [
            int(os.environ["AUTODEL_1"]),
            int(os.environ["AUTODEL_2"]),
            int(os.environ["AUTODEL_3"]),
            int(os.environ["AUTODEL_4"]),
            int(os.environ["AUTODEL_5"]),
            int(os.environ["AUTODEL_6"])
        ]
        if message.channel.id in TARGET_CHANNNEL_IDS:
            await message.delete()
            await self.autoBan_inAutoDeletion(message)
            return True
        return False
    
    async def autoBan_inAutoDeletion(self,message:discord.Message) -> bool:
        #このチャンネルは人間がしゃべることを想定していないので、ここで誤検出は恐れなくてよい。
        #漏れをなるべく減らす方向でBANワードを作る
        BANWORDS = [
            "discord.gg",
            "http",
            "everyone",
            "peach"
        ]
        if any(word in message.content.lower() for word in BANWORDS):
            await message.author.ban(delete_message_days=7)
            await self.createReport("スパムメッセージを検出したので、自動BANを実行しました。",message)
            return True
        return False

    async def autoBan(self,message:discord.Message) -> bool:
        #人間もしゃべる可能性があるので、誤検出は避けたい
        #最低限のBANワードを入れる
        BANWORDS = [
            "discord.gg/sexycontent",
            "onlyfan leaks",
            "onlyfans leaks"
        ]
        if any(word in message.content.lower() for word in BANWORDS):
            await message.author.ban(delete_message_days=7)
            await self.createReport("スパムメッセージを検出したので、自動BANを実行しました。",message)
            return True
        return False
    


    async def createReport(self,report:str, message:discord.Message) -> None:
        content = f"{report}\n"
        content += f"author:{message.author.name}\n"
        content += f"content:```{message.content.replace('.','_').replace('http','ht tp')}```"
        await sendToDiscord(self.reportChannel,RCReply(plainText=content))
