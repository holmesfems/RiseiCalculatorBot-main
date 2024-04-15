import discord
import os
async def moderingMSG(message:discord.Message):
    #指定したチャンネルは、追加したメッセージをすべて削除
    doneAny = False
    doneAny |= await autoBan(message)
    doneAny |= await autoDeletion(message)
    return doneAny

async def autoDeletion(message:discord.Message) -> bool:
    TARGET_CHANNNEL_IDS = [
        os.environ["AUTODEL_1"]
    ]
    if message.channel.id in TARGET_CHANNNEL_IDS:
        message.delete()
        return True
    return False

async def autoBan(message:discord.Message) -> bool:
    BANWORDS = [
        "discord.gg/sexycontent"
    ]
    if any(word in message.content for word in BANWORDS):
        message.author.ban(delete_message_days=7)
        return True
    return False