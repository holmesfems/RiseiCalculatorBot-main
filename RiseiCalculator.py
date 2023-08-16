import os, sys
import discord
from discord import app_commands,Integration
from discord.app_commands import Choice
import traceback
from riseiCalculatorProcess import *
from recruitment.recruitment import *

TOKEN = os.environ["BOT_TOKEN"]
ID = os.environ["BOT_ID"]
url_botCommands = "https://discord.com/api/v8/applications/{0}/commands".format(ID)
intents=discord.Intents.default()
client = discord.Client(intents=intents,command_prefix = '/')
slash = app_commands.CommandTree(client)

test_guilds = [int(os.environ["GUILD_ID"])]
rc = None

async def replyToDiscord(inter,msg):
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
    await inter.followup(embeds = embeds)
        #await inter.followup

async def showUpdateTime(inter,csv_file):
    if rc != None:
        createdTime = "\n作成時間:\t{0}".format(rc.UpdatedTime)
        await inter.followup(createdTime,file = discord.File('BaseStages.csv') if csv_file else None)

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

"""
@slash.command(
    name = 'riseicalculator',
    description = '理性価値表計算',
    parameters = [
        Parameter(
            name = "target",
            description = "どの項目を計算してほしい？",
            autocomplete = True,
            required = True,
            choices = [
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
            type = AppCommandOptionType.string
        ),
        Parameter(
            name = "target_item",
            description = "検索したい素材名",
            autocomplete = True,
            choices = [Choice(name=get_StageCategoryDict(False)[x]["to_ja"],value=x) for x in get_StageCategoryDict(False).keys()],
            type = AppCommandOptionType.string
        ),
        Parameter(
            name = "event_code",
            description = "マップ名の中に含まれる文字列",
            type = AppCommandOptionType.string
        ),
        Parameter(
            name = "mode",
            description = "計算モード選択",
            autocomplete = True,
            choices = [Choice(name="Sanity",value ="Sanity"),Choice(name="Time",value ="Time")],
            type = AppCommandOptionType.string
        ),
        Parameter(
            name = "min_times",
            description = "計算に必要な最小サンプル数",

        )
    ]
)
@discord.app_commands.describe(
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
@discord.app_commands.choices(
    target = 
    target_item = [Choice(name=get_StageCategoryDict(False)[x]["to_ja"],value=x) for x in get_StageCategoryDict(False).keys()]
)
    options = [
        Option("target","どの項目を計算してほしい？",3,True,choices = [
            OptionChoice("基準マップ","basemaps"),
            OptionChoice("理性価値表","sanValueLists"),
            OptionChoice("昇進素材別検索(target_item指定)","items"),
            OptionChoice("通常ステージ検索(event_code指定)","zone"),
            OptionChoice("イベント検索(event_code指定)","events"),
            OptionChoice("初級資格証効率表","te2List"),
            OptionChoice("上級資格証効率表","te3List"),
            OptionChoice("特別引換証効率表","specialList"),
            OptionChoice("契約賞金引換効率表(CC#11)","ccList"),
        ]),
        Option("target_item","検索したい素材名",3,choices = \
            [OptionChoice(get_StageCategoryDict(False)[x]["to_ja"],x) for x in get_StageCategoryDict(False).keys()]
        ),
        Option("event_code","マップ名の中に含まれる文字列",3),
        Option("mode","計算モード選択",3,choices = [OptionChoice("Sanity","Sanity"),OptionChoice("Time","Time")]),
        Option("min_times","計算に必要な最小サンプル数",4),
        Option("min_basetimes","基準マップとして選ばれるために必要な最小サンプル数",4),
        Option("max_items","表示するマップの数",4),
        Option("csv_file",'理性価値表CSVファイルを添付する',5),
        
        #Option("ls_ce","LS,CEステージの番号",3,choices=[
        #    OptionChoice('6','6')
        #]),
        Option("is_global","True:グローバル版基準の計算、False:大陸版の新ステージと新素材を入れた計算",5),

        Option("cache_time","計算キャッシュを保持する時間(分)",4)
    ],
@discord.app_commands.guilds(
    test_guilds
)
"""
@slash.command(
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
async def riseicalculator(inter:discord.Interaction,target:Choice[str],target_item:Choice[str]=None,
                          event_code:str = None, mode="Sanity",min_times=1000,min_basetimes=3000,max_items=15,csv_file = False,is_global=True,cache_time = 30):
    msg = ""
    ls_ce = '6'
    global rc
    try:
        if(target == "items"):
            if target_item == "":
                msg = "アイテム名を指定してください"
                return
        elif(target in ["zone","events"]):
            if event_code == "":
                msg = "ステージ名を指定してください"
                return
        await inter.reply("target={0},mode={1},min_times={2},min_basetimes={3},max_items={4},csv_file={5},ls_ce={6}\n".format(\
            target,mode,min_times,min_basetimes,max_items,csv_file,ls_ce)+\
        "計算開始、しばらくお待ちください...")
        if rc == None or cache_time < 0:
            #print(rc)
            rc = RiseiCalculator(minTimes = min_times, baseMinTimes = min_basetimes,LS_CE=ls_ce,Mode=mode,Global=is_global)
        msg = rc.Calc(to_print=target,target_forPrint={"items":target_item,"zone":event_code,"events":event_code}[target] if target in ["items","zone","events"] else "",\
            cacheTime=cache_time,parameters={"mode":mode,"min_times":min_times,"min_basetimes":min_basetimes,"max_items":max_items,"ls_ce":ls_ce,"is_global":is_global})
        return
    except Exception as e:
        msg = showException()
    finally:
        #channel = inter.channel()
        await replyToDiscord(inter,msg)
        await showUpdateTime(inter,csv_file)
        

    #print(rc.convert_rules)
"""
@slash.command(
    name = 'riseimaterials',
    description = '昇進素材別検索(target_item指定)',
    options = [
        Option("target_item","検索したい素材名",3,True,choices = \
            [OptionChoice(get_StageCategoryDict(False)[x]["to_ja"],x) for x in get_StageCategoryDict(False).keys()]
        ),
        Option("mode","計算モード選択",3,choices = [OptionChoice("Sanity","Sanity"),OptionChoice("Time","Time")]),
        Option("min_times","計算に必要な最小サンプル数",4),
        Option("min_basetimes","基準マップとして選ばれるために必要な最小サンプル数",4),
        Option("max_items","表示するマップの数",4),
        Option("csv_file",'理性価値表CSVファイルを添付する',5),
        
        #Option("ls_ce","LS,CEステージの番号",3,choices=[
        #    OptionChoice('6','6')
        #]),
        Option("is_global","True:グローバル版基準の計算、False:大陸版の新ステージと新素材を入れた計算",5),
        Option("cache_time","計算キャッシュを保持する時間(分)",4)
    ],
    guild_ids = test_guilds
)

async def riseimaterials(inter,target_item, mode="Sanity",min_times=1000,min_basetimes=3000,max_items=15,csv_file = False,is_global=True,cache_time = 30):
    msg = ""
    ls_ce = '6'
    global rc
    target = "items"
    try:
        await inter.reply("target={0},mode={1},min_times={2},min_basetimes={3},max_items={4},csv_file={5},ls_ce={6}\n".format(\
            target,mode,min_times,min_basetimes,max_items,csv_file,ls_ce)+\
        "計算開始、しばらくお待ちください...")
        if rc == None or cache_time < 0:
            #print(rc)
            rc = RiseiCalculator(minTimes = min_times, baseMinTimes = min_basetimes,LS_CE=ls_ce,Mode=mode,Global=is_global)
        msg = rc.Calc(to_print=target,target_forPrint=target_item,\
            cacheTime=cache_time,parameters={"mode":mode,"min_times":min_times,"min_basetimes":min_basetimes,"max_items":max_items,"ls_ce":ls_ce,"is_global":is_global})
        return
    except Exception as e:
        msg = showException()
    finally:
        #channel = inter.channel()
        await replyToDiscord(inter,msg)
        await showUpdateTime(inter,csv_file)

@slash.command(
    name = 'recruitCalculator',
    description = '公開求人検索',
    options = [
        Option("tag1","1個めのタグ",3,True,choices = \
            [OptionChoice(x,x) for x in tagNameList]
        ),
        Option("tag2","2個めのタグ",3,choices = \
            [OptionChoice(x,x) for x in tagNameList]
        ),
        Option("tag3","3個めのタグ",3,choices = \
            [OptionChoice(x,x) for x in tagNameList]
        ),
        Option("tag4","4個めのタグ",3,choices = \
            [OptionChoice(x,x) for x in tagNameList]
        ),
        Option("tag5","5個めのタグ",3,choices = \
            [OptionChoice(x,x) for x in tagNameList]
        ),
        Option("min_star","星〇以上確定のみを表示",4,choices = \
            [OptionChoice(str(x+1),x+1) for x in range(6)]
        )
    ],
    guild_ids = test_guilds
)
async def recruitCalculator(inter, tag1, tag2="", tag3="", tag4="", tag5="",min_star = 1):
    try:
        await inter.reply("計算開始、しばらくお待ちください")
        msg = recruitDoProcess(tag1,tag2,tag3,tag4,tag5,min_star)
        return
    except:
        msg = showException()
    finally:
        await replyToDiscord(inter,msg)
"""
@client.event
async def on_ready():
    print('Botでログインしました')
    await slash.sync()

client.run(TOKEN)