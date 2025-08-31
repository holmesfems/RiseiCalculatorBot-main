import discord
import sys
sys.path.append('../')
from rcutils.rcReply import RCReply

def chunk_text(text: str, limit: int = 2000):
    text = text or ""
    if len(text) <= limit:
        return [text]
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + limit)
        if end < n:
            split_pos = text.rfind("\n", start, end)
            if split_pos == -1:
                split_pos = text.rfind(" ", start, end)
            if split_pos == -1 or split_pos <= start:
                split_pos = end
        else:
            split_pos = end
        chunks.append(text[start:split_pos])
        start = split_pos
        if start < n and text[start] in ("\n", " "):
            start += 1
    return chunks

async def actionToDiscord(func,msg:RCReply):
    embeds = msg.getEmbbeds()
    if(embeds):
        await func(embeds = embeds)
    if(msg.plainText or msg.files()):
        chunks = chunk_text(msg.plainText)
        if(not chunks): chunks = [""]  # メッセージが空でも最終送信でファイルを添付
        for i, chunk in enumerate(chunks):
            if(i == len(chunks - 1)):
                await func(content=chunk,files = msg.files())
            else:
                await func(content=chunk)

async def followupToDiscord(inter:discord.Interaction,msg:RCReply):
    await actionToDiscord(inter.followup.send,msg)

async def sendToDiscord(channel:discord.channel.TextChannel,msg:RCReply):
    await actionToDiscord(channel.send,msg)

async def replyToDiscord(message:discord.Message,msg:RCReply):
    await actionToDiscord(message.reply,msg)