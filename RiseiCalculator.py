import os, sys
import discord
from discord import app_commands,Interaction
from discord.app_commands import Choice
from discord.utils import MISSING
from discord.ext import tasks
import traceback
from recruitment.recruitment import *
import happybirthday.happybirthday as birthday
import openaichat.openaichat as chatbot
from riseicalculator2.riseicalculatorprocess import CalculatorManager,CalculateMode,getStageCategoryDict
from typing import List
import datetime

TOKEN = os.environ["BOT_TOKEN"]
ID = os.environ["BOT_ID"]
GUILD_ID = int(os.environ["GUILD_ID"])
url_botCommands = "https://discord.com/api/v8/applications/{0}/commands".format(ID)
intents=discord.Intents.default()
client = discord.Client(intents=intents,command_prefix = '/')

rc = None

def arrangementChunks(msgList, maxLength:int):
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

def createEmbedList(msg):
    maxLength = 1900
    title = "reply"
    color = 0x8be02b
    if type(msg) == type(str()):
        chunks = [msg[i:i+maxLength] for i in range(0, len(msg), maxLength)]
    elif type(msg) == type(list()):
        chunks = arrangementChunks(msg,maxLength)
    elif type(msg) == type(dict()):
        title = msg.get("title",title)
        msgList = msg.get("msgList",[])
        color = msg.get("color",0x8be02b)
        chunks = arrangementChunks(msgList,maxLength)
    embeds = []
    for item in chunks:
        embed = discord.Embed(
            title = title,
            description = item,
            color = color
        )
        embeds.append(embed)
    return embeds

async def replyToDiscord(inter:Interaction,msg):
    embeds = createEmbedList(msg)
    await inter.followup.send(embeds = embeds)
        #await inter.followup

async def showUpdateTime(inter:Interaction,csv_file):
    if rc != None:
        createdTime = "\n作成時間:\t{0}".format(rc.UpdatedTime)
        await inter.followup.send(createdTime,file = discord.File('BaseStages.csv') if csv_file else MISSING)

def showException():
    ex_type, ex_value, ex_traceback = sys.exc_info()
    # Extract unformatter stack traces as tuples
    trace_back = traceback.extract_tb(ex_traceback)

    # Format stacktrace
    stack_trace = list()

    for trace in trace_back:
        stack_trace.append("File : %s , Line : %d, Func.Name : %s, Message : %s\n" % (trace[0], trace[1], trace[2], trace[3]))
    msg = "想定外のエラー:\n"
    msg += "Exception type : %s \n" % ex_type.__name__
    msg += "Exception message : %s\n" % ex_value
    msg += "Stack trace:\n"
    for item in stack_trace:
        msg += item
    return msg

def safeCallChoiceVal(choice):
    if choice != None:
        if(isinstance(choice,Choice)):
            return choice.value
        return choice
    return None

tree = app_commands.CommandTree(client)

async def riseicalculatorMaster(inter:Interaction,target:str,target_item:str=None,
                          event_code:str = None, mode:str="sanity",min_times:int=1000,min_basetimes:int=3000,max_items:int=15,csv_file:bool = False,is_global:bool=True,cache_time:int = 30):
    msg = ""
    try:
        mode = CalculateMode(mode)
        await inter.response.defer(thinking=True)
        msg = CalculatorManager.riseicalculatorMaster(target,target_item,event_code,is_global,mode,min_basetimes,cache_time,min_times,max_items)
        await replyToDiscord(inter,msg)
        if(csv_file):
            calculator = CalculatorManager.selectCalculator(is_global)
            calculator.dumpToFile(mode)
            time = calculator.stageInfo.lastUpdated
            createdTime = "\n作成時間:\t{0}".format(time)
            await inter.followup.send(createdTime,file = discord.File('BaseStages.xlsx'))
    except Exception as e:
        msg = showException()
    finally:
        print(msg)
        #channel = inter.channel()

targetItemChoice=[Choice(name=v["to_ja"],value=x) for x,v in getStageCategoryDict(False).items()]
modeChoice = [Choice(name="Sanity",value ="sanity"),Choice(name="Time",value ="time")]

@tree.command(
    name = "riseicalculator",
    description = "理性価値表計算,設定項目が複雑なので上級者向け。代わりに/riseimetarials,/riseistages,/riseievents,/riseilistsを使ってください",
)
@app_commands.describe(
    target = "どの項目を計算してほしい？",
    target_item = "検索したい素材名",
    event_code = "マップ名の中に含まれる文字列",
    mode = "計算モード選択",
    min_times = "計算に必要な最小サンプル数",
    min_basetimes = "基準マップとして選ばれるために必要な最小サンプル数",
    max_items = "表示するマップの数",
    csv_file = "理性価値表CSVファイルを添付する",
    is_global = "True:グローバル版基準の計算、False:大陸版の新ステージと新素材を入れた計算",
    cache_time = "計算キャッシュを保持する時間(分)"
)
@app_commands.choices(
    target = [
        Choice(name = "基準マップ", value = "basemaps"),
        Choice(name = "理性価値表", value = "san_value_lists"),
        Choice(name = "昇進素材別検索(target_item指定)",value = "items"),
        Choice(name = "通常ステージ検索(event_code指定)",value = "zone"),
        Choice(name = "イベント検索(event_code指定)",value = "events"),
        Choice(name = "初級資格証効率表",value = "te2list"),
        Choice(name = "上級資格証効率表",value = "te3list"),
        Choice(name = "特別引換証効率表",value = "special_list"),
        Choice(name = "契約賞金引換効率表(CC#11)",value = "cclist"),
    ],
    target_item = targetItemChoice,
    mode = modeChoice
)
async def riseicalculator(inter:Interaction,target:Choice[str],target_item:Choice[str]=None,
                          event_code:str = None, mode:Choice[str]="sanity",min_times:int=1000,min_basetimes:int=3000,max_items:int=15,csv_file:bool = False,is_global:bool=True,cache_time:int = 30):
    _target = safeCallChoiceVal(target)
    _target_item = safeCallChoiceVal(target_item)
    _mode = safeCallChoiceVal(mode)
    await riseicalculatorMaster(inter,_target,_target_item,event_code,_mode,min_times,min_basetimes,max_items,csv_file,is_global,cache_time)

    #print(rc.convert_rules)

@tree.command(
    name="riseimaterials",
    description="昇進素材の効率の良い恒常ステージを調べます。"
)
@app_commands.describe(
    target_item = "昇進素材を選択",
    mode = "計算モード選択",
    is_global = "True:グローバル版基準の計算(デフォルト)、False:大陸版の新ステージと新素材を入れた計算"
)
@app_commands.choices(
    target_item = targetItemChoice,
    mode = modeChoice
)
async def riseimaterials(inter:Interaction,target_item:Choice[str],mode:Choice[str]="sanity",is_global:bool=True):
    _target_item = safeCallChoiceVal(target_item)
    _mode = safeCallChoiceVal(mode)
    mode = CalculateMode(_mode)
    await inter.response.defer(thinking=True)
    reply = CalculatorManager.riseimaterials(_target_item,is_global,mode)
    await replyToDiscord(inter,reply)


@tree.command(
    name="riseistages",
    description="恒常ステージの理性効率を検索します。恒常サイドストーリーも対象。"
)
@app_commands.describe(
    stage = "ステージ名を入力(例:1-7 SV-8 など)",
    mode = "計算モード選択",
    is_global = "True:グローバル版基準の計算(デフォルト)、False:大陸版の新ステージと新素材を入れた計算"
)
@app_commands.choices(
    mode = modeChoice
)
async def riseistages(inter:Interaction,stage:str,mode:Choice[str]="sanity",is_global:bool=True):
    _mode = safeCallChoiceVal(mode)
    stage = safeCallChoiceVal(stage)
    mode = CalculateMode(_mode)
    await inter.response.defer(thinking=True)
    reply = CalculatorManager.riseistages(stage,is_global,mode)
    await replyToDiscord(inter,reply)

@riseistages.autocomplete("stage")
async def mainstage_autocomplete(inter:Interaction,current:str)->List[app_commands.Choice[str]]:
    strList = CalculatorManager.calculatorForMainland.autoCompleteMainStage(current)
    return [app_commands.Choice(name = x, value = x) for x in strList]

@tree.command(
    name="riseievents",
    description="期間限定イベントの理性効率を検索します。過去の開催済みイベントや、将来の未開催イベントも対象。"
)
@app_commands.describe(
    stage = "ステージ名を入力(例:SV-8 IW-8など)",
    mode = "計算モード選択",
    is_global = "True:グローバル版基準の計算(デフォルト)、False:大陸版の新ステージと新素材を入れた計算"
)
@app_commands.choices(
    mode = modeChoice
)
async def riseievents(inter:Interaction,stage:str,mode:Choice[str]="sanity",is_global:bool=True):
    _mode = safeCallChoiceVal(mode)
    stage = safeCallChoiceVal(stage)
    mode = CalculateMode(_mode)
    await inter.response.defer(thinking=True)
    reply = CalculatorManager.riseievents(stage,is_global,mode)
    await replyToDiscord(inter,reply)

@riseievents.autocomplete("stage")
async def eventstage_autocomplete(inter:Interaction,current:str)->List[app_commands.Choice[str]]:
    strList = CalculatorManager.calculatorForMainland.autoCompleteEventStage(current)
    return [app_commands.Choice(name = x, value = x) for x in strList]

@tree.command(
    name="riseilists",
    description="理性効率表を出力します。"
)
@app_commands.describe(
    target = "表示する効率表を選んでください",
    mode = "計算モード選択",
    is_global = "True:グローバル版基準の計算(デフォルト)、False:大陸版の新ステージと新素材を入れた計算",
    csv_file = "理性価値表CSVファイルを添付する"
)
@app_commands.choices(
    target = [
        Choice(name = "基準マップ", value = "basemaps"),
        Choice(name = "理性価値表", value = "san_value_lists"),
        Choice(name = "初級資格証効率表",value = "te2list"),
        Choice(name = "上級資格証効率表",value = "te3list"),
        Choice(name = "特別引換証効率表",value = "special_list"),
        Choice(name = "契約賞金引換効率表(CC#11)",value = "cclist"),
    ],
    mode = modeChoice
)
async def riseilists(inter:Interaction,target:Choice[str],mode:Choice[str]="sanity",is_global:bool=True,csv_file:bool=False):
    _mode = safeCallChoiceVal(mode)
    _target = safeCallChoiceVal(target)
    mode = CalculateMode(_mode)
    target = CalculatorManager.ToPrint(_target)
    await inter.response.defer(thinking=True)
    reply = CalculatorManager.riseilists(target,is_global,mode)
    await replyToDiscord(inter,reply)
    if(csv_file):
        calculator = CalculatorManager.selectCalculator(is_global)
        calculator.dumpToFile(mode)
        time = calculator.stageInfo.lastUpdated
        createdTime = "\n作成時間:\t{0}".format(time)
        await inter.followup.send(createdTime,file = discord.File('BaseStages.xlsx'))

class RecruitView(discord.ui.View):
    def __init__(self,timeout=180):
        super().__init__(timeout=timeout)
        self.eliteTags = []
        self.jobTags = []
        self.otherTags = []
    
    @discord.ui.select(
        cls=discord.ui.Select,
        placeholder="エリートタグ選択",
        options=[discord.SelectOption(label = x) for x in eliteTags],
        min_values=0,max_values=2
    )
    async def elite_selected(self,inter:Interaction,select:discord.ui.Select):
        self.eliteTags = select.values
        await inter.response.defer()
    
    @discord.ui.select(
        cls=discord.ui.Select,
        placeholder="職タグ選択",
        options=[discord.SelectOption(label = x) for x in jobTags],
        min_values=0,max_values=5
    )
    async def job_selected(self,inter:Interaction,select:discord.ui.Select):
        self.jobTags = select.values
        await inter.response.defer()
        
    
    @discord.ui.select(
        cls=discord.ui.Select,
        placeholder="その他タグ選択",
        options=[discord.SelectOption(label = x) for x in otherTags],
        min_values=0,max_values=5
    )
    async def other_selected(self,inter:Interaction,select:discord.ui.Select):
        self.otherTags = select.values
        await inter.response.defer()
    
    @discord.ui.button(
        label="★4確定のみ",style=discord.ButtonStyle.primary
    )
    async def excecuteHighRare(self,inter:Interaction,button:discord.ui.Button):
        await self.execute(inter,button,4)

    @discord.ui.button(
        label="すべて表示",style=discord.ButtonStyle.secondary
    )
    async def excecuteAll(self,inter:Interaction,button:discord.ui.Button):
        await self.execute(inter,button,1)
    
    async def execute(self,inter:Interaction,button:discord.ui.Button,minstar:int):
        selectedList = self.eliteTags+self.jobTags+self.otherTags
        if(selectedList):
            await inter.response.defer(thinking=True)
            msg = recruitDoProcess(selectedList,minstar)
            await replyToDiscord(inter,msg)
        else:
            await inter.response.defer()

#recruitcal = app_commands.CommandTree(client)
@tree.command(
    name = "recruitsim",
    description = "公開求人検索 UI画面が出るのでそのままお使いください",
)
async def recruitsim(inter:Interaction):
    await inter.response.send_message(view=RecruitView(),ephemeral=True,delete_after=180.0)
    return

@tree.command(
    name = "recruitlist",
    description = "アークナイツ公開求人の高レア確定タグをすべて表示"
)
@app_commands.describe(
    star = "星の数"
)
@app_commands.choices(
    star = [Choice(name="4",value=4), Choice(name="5",value=5)]
)
async def recruitlist(inter:Interaction, star:Choice[int]):
    _star = safeCallChoiceVal(star)
    await inter.response.defer(thinking=True)
    msg = showHighStars(_star)
    await replyToDiscord(inter,msg)

CHANNEL_ID_HAPPYBIRTHDAY = int(os.environ["CHANNEL_ID_HAPPYBIRTHDAY"])

t_delta = datetime.timedelta(hours=9)  # 9時間
JST = datetime.timezone(t_delta, 'JST')  # UTCから9時間差の「JST」タイムゾーン

@tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=JST))
async def checkBirtyday():
    if(not CHANNEL_ID_HAPPYBIRTHDAY): return
    now=datetime.datetime.now(tz=JST)
    msg = birthday.checkBirthday(now)
    if(msg):
        channel = client.get_channel(CHANNEL_ID_HAPPYBIRTHDAY)
        embeds = createEmbedList(msg)
        await channel.send(embeds=embeds)

@client.event
async def on_ready():
    await tree.sync()
    checkBirtyday.start()
    print('Botでログインしました')
    
MAXLOG = 10
MAXMSGLEN = 200
OPENAI_CHANNELID = int(os.environ["OPENAI_CHANNELID"])
ISINPROCESS_AICHAT = False
@client.event
async def on_message(message:discord.Message):
    global ISINPROCESS_AICHAT
    if(message.channel.id != OPENAI_CHANNELID): return
    if(message.author.bot): return
    if(ISINPROCESS_AICHAT): return
    try:
        ISINPROCESS_AICHAT = True
        messageable = client.get_partial_messageable(OPENAI_CHANNELID)
        messages = [message async for message in messageable.history(limit = MAXLOG, after = datetime.datetime.now(tz=JST) - datetime.timedelta(minutes = 10),oldest_first=False)]
        toAI = [{"role": "assistant" if message.author.bot else "user", "content" : message.content} for message in messages]
        toAI.reverse()
        def emptyFilter(msg): #空メッセージ、長すぎるメッセージを除外
            content = msg["content"]
            if content == "": return False
            if len(content) > MAXMSGLEN: return False
            return True
        toAI = list(filter(emptyFilter,toAI))
        reply = chatbot.openaichat(toAI)
        if(reply):
            channel = client.get_channel(OPENAI_CHANNELID)
            await channel.send(content = reply)
    except Exception as e:
        msg = showException()
        print(msg)
    finally:
        ISINPROCESS_AICHAT = False

client.run(TOKEN)