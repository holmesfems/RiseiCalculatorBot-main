from ast import List
import os, sys
import discord
from discord import app_commands,Interaction
from discord.app_commands import Choice
from discord.utils import MISSING
import traceback
from riseiCalculatorProcess import *
from recruitment.recruitment import *

TOKEN = os.environ["BOT_TOKEN"]
ID = os.environ["BOT_ID"]
GUILD_ID = int(os.environ["GUILD_ID"])
url_botCommands = "https://discord.com/api/v8/applications/{0}/commands".format(ID)
intents=discord.Intents.default()
client = discord.Client(intents=intents,command_prefix = '/')

rc = None

async def replyToDiscord(inter:Interaction,msg):
    print(msg)
    max_length = 1900
    title = "reply"
    color = 0x8be02b
    if type(msg) == type(str()):
        chunks = [msg[i:i+max_length] for i in range(0, len(msg), max_length)]
    elif type(msg) == type(list()):
        chunks = []
        for item in msg:
            if len(chunks) == 0:
                chunks.append(item)
            else:
                if(len(chunks[-1])+len(item)) <= max_length:
                    chunks[-1] += item
                else:
                    chunks.append(item)
    elif type(msg) == type(dict()):
        title = msg["title"]
        chunks = msg["msgList"]
        try:
            color = msg["color"] 
        except:
            color = 0x8be02b
    embeds = []
    for item in chunks:
        embed = discord.Embed(
            title = title,
            description = item,
            color = color
        )
        embeds.append(embed)
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

@tree.command(
    name = "riseicalculator",
    description = '理性価値表計算',
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
        Choice(name = "理性価値表", value = "sanValueLists"),
        Choice(name = "昇進素材別検索(target_item指定)",value = "items"),
        Choice(name = "通常ステージ検索(event_code指定)",value = "zone"),
        Choice(name = "イベント検索(event_code指定)",value = "events"),
        Choice(name = "初級資格証効率表",value = "te2List"),
        Choice(name = "上級資格証効率表",value = "te3List"),
        Choice(name = "特別引換証効率表",value = "specialList"),
        Choice(name = "契約賞金引換効率表(CC#11)",value = "ccList"),
    ],
    target_item = [Choice(name=get_StageCategoryDict(False)[x]["to_ja"],value=x) for x in get_StageCategoryDict(False).keys()],
    mode = [Choice(name="Sanity",value ="Sanity"),Choice(name="Time",value ="Time")]
)
async def riseicalculator(inter:Interaction,target:Choice[str],target_item:Choice[str]=None,
                          event_code:str = None, mode:Choice[str]="Sanity",min_times:int=1000,min_basetimes:int=3000,max_items:int=15,csv_file:bool = False,is_global:bool=True,cache_time:int = 30):
    msg = ""
    ls_ce = '6'
    global rc
    _target = safeCallChoiceVal(target)
    _target_item = safeCallChoiceVal(target_item)
    _mode = safeCallChoiceVal(mode)
    try:
        if(target == "items"):
            if target_item == "":
                msg = "アイテム名を指定してください"
                return
        elif(target in ["zone","events"]):
            if event_code == "":
                msg = "ステージ名を指定してください"
                return
        await inter.response.send_message("target={0},mode={1},min_times={2},min_basetimes={3},max_items={4},csv_file={5},ls_ce={6}\n".format(\
            _target,_mode,min_times,min_basetimes,max_items,csv_file,ls_ce)+\
        "計算開始、しばらくお待ちください...")
        if rc == None or cache_time < 0:
            #print(rc)
            rc = RiseiCalculator(minTimes = min_times, baseMinTimes = min_basetimes,LS_CE=ls_ce,Mode=mode,Global=is_global)
        msg = rc.Calc(to_print=_target,target_forPrint={"items":_target_item,"zone":event_code,"events":event_code}[_target] if _target in ["items","zone","events"] else "",\
            cacheTime=cache_time,parameters={"mode":_mode,"min_times":min_times,"min_basetimes":min_basetimes,"max_items":max_items,"ls_ce":ls_ce,"is_global":is_global})
        return
    except Exception as e:
        msg = showException()
    finally:
        #channel = inter.channel()
        await replyToDiscord(inter,msg)
        await showUpdateTime(inter,csv_file)
        

    #print(rc.convert_rules)

def autoGuide(current:str):
    if current == "": return ["エリートタグ","職タグ","その他タグ"]
    if current == "エリートタグ": return eliteTags
    if current == "職タグ": return jobTags
    if current == "その他タグ": return otherTags
    return [x for x in tagNameList if current in x]

def createChoice(list):
    return [Choice(name = item,value=item) for item in list]

async def tagAutoComplete(inter:Interaction,current:str):
    return createChoice(autoGuide(current))

#recruitcal = app_commands.CommandTree(client)
@tree.command(
    name = "recruitsim",
    description = '公開求人検索',
)
async def recruitsim(inter:Interaction):
    try:
        view = discord.ui.View
        view.add_item(item=discord.ui.Select(options=[discord.SelectOption(label = x) for x in tagNameList]))
        await inter.response.send_message(view=view)
        #safeList = [safeCallChoiceVal(x) for x in [tag1,tag2,tag3,tag4,tag5]]
        #_min_star = safeCallChoiceVal(min_star)
        #msg = recruitDoProcess(safeList,_min_star)
        return
    except:
        msg = showException()
    finally:
        await replyToDiscord(inter,msg)

@client.event
async def on_ready():
    await tree.sync()
    print('Botでログインしました')
    
client.run(TOKEN)