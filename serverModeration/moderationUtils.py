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
        doneAny = False
        doneAny |= await self.autoBan(message)
        doneAny |= await self.autoDeletion(message)
        return doneAny

    async def autoDeletion(self,message:discord.Message) -> bool:
        TARGET_CHANNNEL_IDS = [
            int(os.environ["AUTODEL_1"])
        ]
        if message.channel.id in TARGET_CHANNNEL_IDS:
            await message.delete()
            return True
        return False

    async def autoBan(self,message:discord.Message) -> bool:
        BANWORDS = [
            "discord.gg/sexycontent"
        ]
        if any(word in message.content for word in BANWORDS):
            await message.author.ban(delete_message_days=7)
            await self.createReport("スパムメッセージを検出したので、自動BANを実行しました。",message)
            return True
        return False

    async def createReport(self,report:str, message:discord.Message) -> None:
        content = f"{report}\n"
        content += f"author:{message.author.name}\n"
        content += f"content:{message.content}"
        await sendToDiscord(self.reportChannel,RCReply(plainText=content))
