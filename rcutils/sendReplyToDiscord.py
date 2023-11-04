import discord
import sys
sys.path.append('../')
from rcutils.rcReply import RCReply

async def actionToDiscord(func,msg:RCReply):
    embeds = msg.getEmbbeds()
    if(embeds):
        await func(embeds = embeds)
    if(msg.plainText or msg.files()):
        await func(content=msg.plainText,files=msg.files())

async def followupToDiscord(inter:discord.Interaction,msg:RCReply):
    await actionToDiscord(inter.followup.send,msg)

async def sendToDiscord(channel:discord.channel.TextChannel,msg:RCReply):
    await actionToDiscord(channel.send,msg)

async def replyToDiscord(message:discord.Message,msg:RCReply):
    await actionToDiscord(message.reply,msg)