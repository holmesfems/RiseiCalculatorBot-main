import numpy as np
import numpy.linalg as LA
import urllib.request, json, time, os, copy, sys
import random
import pandas as pd
import math
import datetime
import discord
from discord.ext import commands
import traceback
from io import StringIO
from discord.ext import commands
from dislash import slash_commands, Option, OptionType,OptionChoice
import unicodedata
from collections import ChainMap

def left(digit, msg):
    for c in msg:
        if unicodedata.east_asian_width(c) in ('F', 'W', 'A'):
            digit -= 2
        else:
            digit -= 1
    return msg + ' '*digit

penguin_url = 'https://penguin-stats.io/PenguinStats/api/v2/'
headers = {'User-Agent':'ArkPlanner'}
LanguageMap = {'CN': 'zh', 'US': 'en', 'JP': 'ja', 'KR': 'ko'}

#初級&上級資格証
Price = dict()
with open('price.txt', 'r', encoding='utf8') as f:
    for line in f.readlines():
        name, value = line.split()
        Price[name] = int(value)

#特別引換証
Price_Special = dict()
with open('price_special.txt', 'r', encoding='utf8') as f:
    for line in f.readlines():
        name, value = line.split()
        Price_Special[name] = float(value)

Item_rarity2 = [
    '固源岩组','全新装置','聚酸酯组', 
    '糖组','异铁组','酮凝集组',
    '扭转醇','轻锰矿','研磨石',
    'RMA70-12','凝胶','炽合金',
    '晶体元件','半自然溶剂','化合切削液',
    '转质盐组'
]

Item_rarity2_new = [
    
]

Item_rarity3 = [
    '提纯源岩','改量装置','聚酸酯块', 
    '糖聚块','异铁块','酮阵列', 
    '白马醇','三水锰矿','五水研磨石',
    'RMA70-24','聚合凝胶','炽合金块',
    '晶体电路','精炼溶剂','切削原液',
    '转质盐聚块'
]

Item_rarity3_new = [
    
]

ValueTarget = [
    '基础作战记录', '初级作战记录', '中级作战记录', '高级作战记录', 
    '赤金','龙门币1000',
    '源岩', '固源岩', '固源岩组', '提纯源岩', 
    '破损装置', '装置', '全新装置', '改量装置', 
    '酯原料', '聚酸酯', '聚酸酯组', '聚酸酯块', 
    '代糖', '糖', '糖组', '糖聚块', 
    '异铁碎片', '异铁', '异铁组', '异铁块', 
    '双酮', '酮凝集', '酮凝集组', '酮阵列', 
    '扭转醇', '白马醇',
    '轻锰矿', '三水锰矿',
    '研磨石', '五水研磨石',
    'RMA70-12', 'RMA70-24',
    '凝胶', '聚合凝胶',
    '炽合金', '炽合金块',
    '晶体元件', '晶体电路',
    '半自然溶剂','精炼溶剂',
    '化合切削液','切削原液',
    '转质盐组','转质盐聚块','烧结核凝晶',
    '聚合剂', '双极纳米片', 'D32钢','晶体电子单元',
    '技巧概要·卷1', '技巧概要·卷2', '技巧概要·卷3',
]

ValueTarget_new = [
    
]

#ドロップアイテム&ステージのカテゴリ情報を入手
StageCategoryDict = json.load(open("StageCategoryDict.json","r"))

#一部理論値と実際のクリア時間が乖離しているステージで個別修正
minClearTimeInjection = json.load(open("minClearTimeInjection.json","r"))

#大陸版実装済み、グロ版未実装のステージまとめ 実装次第削除してOK
new_zone = [
#    'main_11', #11章
    'main_12', #12章
    'permanent_sidestory_10_zone1', #NL
    'permanent_sidestory_11_zone1', #BI
    'permanent_sidestory_12_zone1', #IW
]

#大陸版基準、グロ版基準調整用
def get_Global_Mainland(ParamName,glob):
    if glob:
        return eval(ParamName)
    else:
        return eval(ParamName) + eval(ParamName+'_new')

def get_Item_rarity2(glob):
    return get_Global_Mainland("Item_rarity2",glob)

def get_Item_rarity3(glob):
    return get_Global_Mainland("Item_rarity3",glob)

def get_ValueTarget(glob):
    return get_Global_Mainland("ValueTarget",glob)

def get_StageCategoryDict(glob):
    if glob:
        return StageCategoryDict["main"]
    else:
        return ChainMap(StageCategoryDict["main"],StageCategoryDict["new"])

#カテゴリを中国語から日本語へ変換
#stage_Category_zh_to_ja = json.load(open("stage_Category_zh_to_ja.json","r"))
        
def get_json(s,AdditionalReq=None):
    if not AdditionalReq == None:
        s += "?" + "&".join(['%s=%s'%(x,AdditionalReq[x]) for x in AdditionalReq])
        print("request:"+s)
    req = urllib.request.Request(penguin_url + s, None, headers)
    with urllib.request.urlopen(req, timeout=10) as response: #謎に一回目だけTimeout なぜ
        return json.loads(response.read().decode())

class RiseiCalculator(object):
    def __init__(self,
                 TargetServer = 'CN',
                 ConvertionDR=0.18,
                 minTimes = 1000,
                 baseMinTimes = 3000,
                 LS_CE='6',
                 Mode = 'Sanity',
                 Global = True,
                 ):
        """
        Object initialization.
        Args:
            filter_freq: int or None. The lowest frequence that we consider.
                No filter will be applied if None.
            url_stats: string. url to the dropping rate stats data.
            url_rules: string. url to the composing rules data.
            path_stats: string. local path to the dropping rate stats data.
            path_rules: string. local path to the composing rules data.
        """
        self.get_item_id()
        self.ConvertionDR = ConvertionDR
        self.minTimes = minTimes
        self.baseMinTimes = baseMinTimes
        self.TargetServer = TargetServer
        self.Mode = Mode
        self.LS_CE = LS_CE
        self.Global = Global
        

        
        #self._GetMatrixNFormula()
        #self._getValidStageList()
        self.UpdatedTime = datetime.datetime.now()
        #self.update(force=update)

    def get_item_id(self):
        items = get_json('items')
        item_array, item_id_to_name = [], {}
        item_name_to_id = {'id': {},
                           'zh': {},
                           'en': {},
                           'ja': {},
                           'ko': {}}

        additional_items = [
                            {'itemId': '4001', 'name_i18n': {'ko': '용문폐', 'ja': '龍門幣', 'en': 'LMD', 'zh': '龙门币'}},
                            {'itemId': '0010', 'name_i18n': {'ko': '작전기록', 'ja': '作戦記録', 'en': 'Battle Record', 'zh': '作战记录'}}
                           ]
        for x in items + additional_items:
            item_array.append(x['itemId'])
            item_id_to_name.update({x['itemId']: {'id': x['itemId'],
                                                  'zh': x['name_i18n']['zh'],
                                                  'en': x['name_i18n']['en'],
                                                  'ja': x['name_i18n']['ja'],
                                                  'ko': x['name_i18n']['ko']}})
            item_name_to_id['id'].update({x['itemId']:          x['itemId']})
            item_name_to_id['zh'].update({x['name_i18n']['zh']: x['itemId']})
            item_name_to_id['en'].update({x['name_i18n']['en']: x['itemId']})
            item_name_to_id['ja'].update({x['name_i18n']['ja']: x['itemId']})
            item_name_to_id['ko'].update({x['name_i18n']['ko']: x['itemId']})

        self.item_array = item_array
        self.item_id_to_name = item_id_to_name
        self.item_name_to_id = item_name_to_id
        self.item_zh_to_ja = {k: item_id_to_name[item_name_to_id['zh'][k]]['ja'] for k in item_name_to_id['zh'].keys()}
        self.item_zh_to_ja.update(
            {
                '基础作战记录':'入門作戦記録',
                '初级作战记录':'初級作戦記録',
                '中级作战记录':'中級作戦記録',
                '高级作战记录':'上級作戦記録',
                '赤金':'純金',
                '龙门币1000':'龍門幣1000',
                '技巧概要·卷1':'アーツ学I',
                '技巧概要·卷2':'アーツ学II',
                '技巧概要·卷3':'アーツ学III',
                '转质盐组':'転化塩',
                '转质盐聚块':'上級転化塩',
                '烧结核凝晶':'焼結核凝晶'
            }
        )

        self.item_dct_rv = {v: k for k, v in enumerate(item_array)} # from id to idx
        self.item_name_rv = {item_id_to_name[v]['zh']: k for k, v in enumerate(item_array)} # from (zh) name to id

    def _GetMatrixNFormula(self):
        """
        import formula data and matrix data
        """
        self.name_to_index = {x:get_ValueTarget(self.Global).index(x) for x in get_ValueTarget(self.Global)}
        self.id_to_index = {x:self.name_to_index[self.item_id_to_name[x]["zh"]] for x in [self.item_name_to_id["zh"][y] for y in get_ValueTarget(self.Global)]}
        self.TotalCount = len(get_ValueTarget(self.Global))
        
        AllStageList = get_json("stages")

        #minClearTimeInjection
        for i in range(len(AllStageList)):
            inject = minClearTimeInjection.get(AllStageList[i]["code"])
            if inject != None:
                AllStageList[i]["minClearTime"] = inject*1000

        #イベントステージを除外
        ExclusionList = new_zone if self.Global else []
        MainStageList = [x for x in AllStageList if x["stageType"] in ["MAIN","SUB"] and x["zoneId"] not in ExclusionList and "tough" not in x["zoneId"]]
        #常設イベントステージ
        MainStageList += [x for x in AllStageList if x["stageType"] in ["ACTIVITY"] and "permanent" in x["zoneId"] and x["zoneId"] not in ExclusionList]
        EventStageList = [x for x in AllStageList if x["stageType"] in ["ACTIVITY"] \
            and "permanent" not in x["zoneId"] \
            and "act" in x["zoneId"] \
            and "gacha" not in x["stageId"] \
            #ウルサスの子供を除外
            and "act10d5" not in x["zoneId"] 
        ]
        #print(MainStageList)
        MainStageIdList = [x["stageId"] for x in MainStageList]
        EventStageIdList = [x["stageId"] for x in EventStageList]
        #itemFilter = ",".join([self.item_name_to_id["zh"][x] for x in get_ValueTarget(self.Global)])
        #additionalHeader = {"itemFilter":itemFilter,"server":self.TargetServer,"show_closed_zones":"true"}

        itemFilter = [self.item_name_to_id["zh"][x] for x in get_ValueTarget(self.Global)]
        additionalHeader = {"server":self.TargetServer,"show_closed_zones":"true"}
        #ドロップデータ取得
        matrix = get_json('result/matrix',additionalHeader) #一回目ここで死んでる
        #合成レシピ 副産物確率取得
        formula = get_json('formula')
        zones = get_json('zones')
        self.matrix = [x for x in matrix["matrix"] if x["stageId"] in MainStageIdList + EventStageIdList and x["itemId"] in itemFilter]
        #print(self.matrix)
        self.formula = formula
        self.stages = MainStageList
        self.stageIds = MainStageIdList
        self.eventStages = EventStageList
        self.eventIds = EventStageIdList
        self.allStages = MainStageList+EventStageList
        self.allIds = MainStageIdList+EventStageIdList
        self.stageId_to_name = {x["stageId"]:x["code_i18n"]["zh"] for x in self.allStages}
        self.stageName_to_Id = {x["code_i18n"]["zh"]:x["stageId"] for x in MainStageList}
        self.stageName_to_stage = {x["code_i18n"]["zh"]:x for x in MainStageList}
        self.zoneIds = list(dict.fromkeys([x["zoneId"] for x in MainStageList]))
        self.zoneId_to_stages = {x:[y for y in self.stages if y["zoneId"] == x] for x in self.zoneIds}
        self.zoneId_to_Name_ja = {x["zoneId"]:x["zoneName_i18n"]["ja"] for x in zones}

        #print(self.item_id_to_name[matrix["matrix"][0]["itemId"]])
        #print(self.item_name_to_id["zh"].keys())
        #print(self.name_to_index)
        #print(self.id_to_index)

    def _GetConvertionMatrix(self):
        """
        Get convertion part of value_matrix
        """
        arraylist = []
        # 経験値換算
        # 基础作战记录*2=初级作战记录
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["基础作战记录"]] = -2
        arr[self.name_to_index["初级作战记录"]] = 1
        arraylist.append(arr)

        # 初级作战记录*2.5=中级作战记录
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["初级作战记录"]] = -2.5
        arr[self.name_to_index["中级作战记录"]] = 1
        arraylist.append(arr)

        # 中级作战记录*2=高级作战记录
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["中级作战记录"]] = -2
        arr[self.name_to_index["高级作战记录"]] = 1
        arraylist.append(arr)

        # 赤金*2 = 龙门币1000
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["赤金"]] = -2
        arr[self.name_to_index["龙门币1000"]] = 1
        arraylist.append(arr)
    
        # 素材合成換算
        for item in self.formula:
            if item["name"] not in get_ValueTarget(self.Global):
                continue
            arr = np.zeros(self.TotalCount)
            arr[self.name_to_index[item["name"]]] = -1
            arr[self.name_to_index["龙门币1000"]] = item["goldCost"]/1000
            for costItem in item["costs"]:
                arr[self.name_to_index[costItem["name"]]] = costItem["count"]

            #副産物を考慮
            exarr = np.zeros(self.TotalCount)
            for exItem in item["extraOutcome"]:
                if exItem["name"] not in get_ValueTarget(self.Global):
                    continue
                exarr[self.name_to_index[exItem["name"]]] = exItem["weight"]/item["totalWeight"]
            
            arraylist.append(arr-exarr*self.ConvertionDR)
        
        # 本の合成
        # 技1*3=技2
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["技巧概要·卷1"]] = 3
        arr[self.name_to_index["技巧概要·卷2"]] = -1-self.ConvertionDR
        arraylist.append(arr)

        # 技2*3=技3
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["技巧概要·卷2"]] = 3
        arr[self.name_to_index["技巧概要·卷3"]] = -1-self.ConvertionDR
        arraylist.append(arr)

        divlist = np.zeros(shape=(len(arraylist),self.TotalCount))
        return (np.array(arraylist),np.zeros(len(arraylist)),divlist)
    
    def _GetStageClearTime(self,stageName):
        stage = self.stageName_to_stage[stageName]
        #print(stageName,stage)
        return stage["minClearTime"]/1000.0

    def _GetConstStageMatrix(self):
        arraylist = []
        riseilist = []
        if(self.LS_CE == '5'):
            #LS-5
            arr = np.zeros(self.TotalCount)
            arr[self.name_to_index["初级作战记录"]] = 1
            arr[self.name_to_index["中级作战记录"]] = 1
            arr[self.name_to_index["高级作战记录"]] = 3
            arr[self.name_to_index["龙门币1000"]] = 0.36
            arraylist.append(arr)
            riseilist.append({"Sanity":30,"Time":174.5}[self.Mode])

            #CE-5
            arr = np.zeros(self.TotalCount)
            arr[self.name_to_index["龙门币1000"]] = 7.5
            arraylist.append(arr)
            riseilist.append({"Sanity":30,"Time":196.0}[self.Mode])
        elif(self.LS_CE == '6'):
             #LS-6
            arr = np.zeros(self.TotalCount)
            arr[self.name_to_index["初级作战记录"]] = 0
            arr[self.name_to_index["中级作战记录"]] = 2
            arr[self.name_to_index["高级作战记录"]] = 4
            arr[self.name_to_index["龙门币1000"]] = 0.432
            arraylist.append(arr)
            riseilist.append({"Sanity":36,"Time":183.0}[self.Mode])

            #CE-6
            arr = np.zeros(self.TotalCount)
            arr[self.name_to_index["龙门币1000"]] = 10
            arraylist.append(arr)
            riseilist.append({"Sanity":36,"Time":172.0}[self.Mode])

        #CA-5
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["技巧概要·卷1"]] = 1.5
        arr[self.name_to_index["技巧概要·卷2"]] = 1.5
        arr[self.name_to_index["技巧概要·卷3"]] = 2
        arr[self.name_to_index["龙门币1000"]] = 0.36
        arraylist.append(arr)
        riseilist.append({"Sanity":30,"Time":173.0}[self.Mode])
        
        divlist = np.zeros(shape=(len(arraylist),self.TotalCount))
        return (np.array(arraylist),np.array(riseilist),divlist)

    def _getValidStageList(self):
        #ステージのカテゴリ化
        #スマートなやり方が分からなかったので手打ちで
        #'Stages' 'Items'の他に、試行回数条件を満たしたステージIdのみを入れる'ValidIds'も追加される
        #カテゴリキー 基準選びはカテゴリ毎に一つだけ抽選される
        #self.stage_Category_keys = list(StageCategoryDict.keys())

        """
        stage dict:ステージごとの情報を取得する
        Key:stageId
        Value:{
            array: ndarray,各素材のドロップ率をValueTarget順に記載
            apCost: int, 理性消費
            name: str,ステージ名
            minTimes: int, 各素材の内、報告の最小試行回数
        }
        """
        #global StageCategoryDict
        stage_dict = {}
        for item in self.matrix:
            #print(item)
            if item["itemId"] not in self.id_to_index.keys():
                continue
            if item["stageId"] not in self.stageIds + self.eventIds:
                continue
            if item["times"] < self.minTimes:
                continue
            if not item["stageId"] in stage_dict.keys():
                #initialize
                stage_info = {}
                stage_info["array"] = np.zeros(self.TotalCount)
                stage_info["divArray"] = np.zeros(self.TotalCount)
                #print(item["stageId"])
                stage_info["apCost"] = self.allStages[self.allIds.index(item["stageId"])]["apCost"]
                stage_info["name"] = self.stageId_to_name[item["stageId"]]
                if self.allStages[self.allIds.index(item["stageId"])]["minClearTime"] is None:
                    stage_info["timeCost"] = None
                else:
                    stage_info["timeCost"] = self.allStages[self.allIds.index(item["stageId"])]["minClearTime"]/1000.0
                stage_info["array"][self.name_to_index["龙门币1000"]] = stage_info["apCost"] *0.012
                stage_info["minTimes"] = 0
                stage_info["maxTimes"] = 0
                #目的の消費値がNoneの場合、計算に入れない
                selection = {"Sanity":"apCost","Time":"timeCost"}[self.Mode]
                if stage_info[selection] is None:
                    continue
                stage_dict[item["stageId"]] = stage_info
            
            prob = item["quantity"]/item["times"]
            fprob = math.modf(prob)[0]
            stage_dict[item["stageId"]]["array"][self.id_to_index[item["itemId"]]] += prob
            #ドロップ数が二種類しか出ない仮定
            stage_dict[item["stageId"]]["divArray"][self.id_to_index[item["itemId"]]] += fprob*(1 - fprob) / item["times"]

            if stage_dict[item["stageId"]]["minTimes"] == 0 or item["times"] < stage_dict[item["stageId"]]["minTimes"]:
                stage_dict[item["stageId"]]["minTimes"] = item["times"]
            if stage_dict[item["stageId"]]["maxTimes"] == 0 or item["times"] > stage_dict[item["stageId"]]["maxTimes"]:
                stage_dict[item["stageId"]]["maxTimes"] = item["times"]
            
        #print(stage_dict)
        #試行回数条件を満たしているステージのみ出力&Id順にソートしておく
        self.stage_dict_all = {key:value for key,value in sorted(stage_dict.items(),key=lambda x:x[0])}
        self.stage_dict = {key:value for key,value in sorted(stage_dict.items(),key=lambda x:x[0]) if value["maxTimes"] >= self.minTimes and key in self.stageIds}
        self.stage_baseDict = {key:value for key,value in sorted(stage_dict.items(),key=lambda x:x[0]) if value["maxTimes"] >= self.baseMinTimes and key in self.stageIds}
        self.event_dict = {key:value for key,value in sorted(stage_dict.items(),key=lambda x:x[0]) if key in self.eventIds}
        self.valid_stages = list(self.stage_dict.keys())
        self.valid_stages_getindex = {x:self.valid_stages.index(x) for x in self.valid_stages}
        self.valid_baseStages = list(self.stage_baseDict.keys())
        self.valid_baseStages_getindex = {x:self.valid_stages.index(x) for x in self.valid_baseStages}
        self.event_stages = list(self.event_dict.keys())
        #self.event_stages_getindex = {x:self.event_stages.index(x) for x in self.event_stages}
        #add 'ValidIds' for StageCategory
        self.category_ValidIds = {x:[y for y in self.valid_stages if self.stage_dict[y]["name"] in get_StageCategoryDict(self.Global)[x]['Stages']] for x in get_StageCategoryDict(self.Global).keys()}
        self.category_BaseIds = {x:[y for y in self.valid_baseStages if self.stage_baseDict[y]["name"] in get_StageCategoryDict(self.Global)[x]['Stages']] for x in get_StageCategoryDict(self.Global).keys()}

        #for item in StageCategoryDict.keys():
        #    StageCategoryDict[item]['ValidIds'] = [x for x in self.valid_stages if self.stage_dict[x]["name"] in StageCategoryDict[item]['Stages']]
        #    StageCategoryDict[item]['BaseIds'] = [x for x in self.valid_baseStages if self.stage_baseDict[x]["name"] in StageCategoryDict[item]['Stages']]

    #seedsからステージのドロ率行列を取得
    #seedsは選ぶ基準ステージのvalid_stages内のindexを意味している
    def _getStageMatrix(self,seeds):
        arraylist = []
        riseilist = []
        divlist = []
        for index in seeds:
            arraylist.append(self.stage_dict[self.valid_stages[index]]["array"])
            selection = {"Sanity":"apCost","Time":"timeCost"}[self.Mode]
            riseilist.append(self.stage_dict[self.valid_stages[index]][selection])
            divlist.append(self.stage_dict[self.valid_stages[index]]["divArray"])
        return (np.array(arraylist),np.array(riseilist),np.array(divlist))
    
    def _detMatrix(self,vstackTuple):
        return LA.det(np.vstack(vstackTuple))
    
    def _seed2StageName(self,seeds):
        return [self.stageId_to_name[self.valid_stages[x]] for x in seeds]

    def _getValues(self,vstackTuple,riseiArrayList):
        #線型方程式で理性価値を解く
        return LA.solve(np.vstack(vstackTuple),np.concatenate(riseiArrayList))

    def _getMaterialDiv(self,vstackTuple,divStackTuple,metarialValues):
        probMatrix = np.vstack(vstackTuple)
        probMatrix_inv = np.linalg.inv(probMatrix)
        #probMatrix_invSquare = np.dot(probMatrix_inv,probMatrix_inv)
        #riseiArray = np.concatenate(riseiArrayList)
        divMatrix = np.vstack(divStackTuple)
        #print(divMatrix.tolist())
        div_X = np.dot(np.dot(probMatrix_inv**2,divMatrix),metarialValues**2)
        
        return div_X
    
    def _divToSD95(self,xDivArray):
        return xDivArray**0.5*2

    def _getStageValues(self,valueArray):
        selection = {"Sanity":"apCost","Time":"timeCost"}[self.Mode]
        return {x:np.dot(valueArray,self.stage_dict[x]["array"].T)/self.stage_dict[x][selection] for x in self.valid_stages}

    def _getEventValues(self,valueArray):
        selection = {"Sanity":"apCost","Time":"timeCost"}[self.Mode]
        return {x:np.dot(valueArray,self.event_dict[x]["array"].T)/self.event_dict[x][selection] for x in self.event_stages}

    def _getBaseStageValues(self,valueArray):
        #解いた理性価値を使い、ステージごとの理性効率を求める
        #理性効率=Sum(理性価値×ドロ率)/理性消費
        #効率が1より上回るステージがあれば、まだ最適ではないと言える
        selection = {"Sanity":"apCost","Time":"timeCost"}[self.Mode]
        return {x:np.dot(valueArray,self.stage_dict[x]["array"].T)/self.stage_dict[x][selection] for x in self.valid_baseStages}
    
    def _getStageValueSD95(self,vstackTuple,divStackTuple,valueArray,seeds):
        probMatrix = np.vstack(vstackTuple)
        probMatrix_inv = np.linalg.inv(probMatrix)
        #probMatrix_invSquare = np.dot(probMatrix_inv,probMatrix_inv)
        #riseiArray = np.concatenate(riseiArrayList)
        divMatrix = np.vstack(divStackTuple)
        res = {}
        for x in self.valid_stages:
            if self.valid_stages_getindex[x] in seeds:
                res[x] = 0.0
            else:
            #stageArray = self.stage_dict[x]["array"]
                stageDiv = self.stage_dict[x]["divArray"]
                stageArr = self.stage_dict[x]["array"]
                selection = {"Sanity":"apCost","Time":"timeCost"}[self.Mode]
                res[x] = (np.dot(stageDiv,valueArray**2)+np.dot(np.dot(np.dot(stageArr,probMatrix_inv)**2,divMatrix),valueArray**2))**0.5/self.stage_dict[x][selection]*2
        return res
        
    def _getCategoryFromStageId(self,stageId):
        return [x for x in get_StageCategoryDict(self.Global).keys() if self.stageId_to_name[stageId] in get_StageCategoryDict(self.Global)[x]['Stages']]

    def Calc(self,to_print = "",target_forPrint = "",cacheTime = 30,parameters = {}):
        need_reCalculate = False
        self.nowTime = datetime.datetime.now()
        try:
            if (self.nowTime - self.UpdatedTime > datetime.timedelta(minutes=cacheTime) and cacheTime > 0) or \
            (self.minTimes,self.Mode,self.baseMinTimes,self.Global) != (parameters["min_times"],parameters["mode"],parameters["min_basetimes"],parameters["is_global"]):
            #若干ロジック上の問題があるかもしれない
                need_reCalculate = True
                    
            else:
                #read cache
                ConvertionMatrix,ConvertionRisei,ConvertionDiv = (self.ConvertionMatrix,self.ConvertionRisei,self.ConvertionDiv)
                ConstStageMatrix,ConstStageRisei,ConstStageDiv = (self.ConstageMatrix,self.ConstStageRisei,self.ConstStageDiv)
                stageMatrix,stageRisei,stageDiv = (self.stageMatrix,self.stageRisei,self.stageDiv)
                seeds = self.seeds
        except:
            # self.Convertion等未定義などの場合はここに飛ぶ
            need_reCalculate = True
        if need_reCalculate:
            ParamBackup = (self.minTimes,self.Mode,self.baseMinTimes,self.Global)
            self.minTimes,self.Mode,self.baseMinTimes,self.Global = (parameters["min_times"],parameters["mode"],parameters["min_basetimes"],parameters["is_global"])
            try:
                self._GetMatrixNFormula()
                self._getValidStageList()
            except Exception as e:
                self.minTimes,self.Mode,self.baseMinTimes,self.Global = ParamBackup
                raise e
            self.UpdatedTime = self.nowTime
            ConvertionMatrix,ConvertionRisei,ConvertionDiv = self._GetConvertionMatrix()
            self.ConvertionMatrix,self.ConvertionRisei,self.ConvertionDiv = (ConvertionMatrix,ConvertionRisei,ConvertionDiv) #cache
            ConstStageMatrix,ConstStageRisei,ConstStageDiv = self._GetConstStageMatrix()
            self.ConstageMatrix,self.ConstStageRisei,self.ConstStageDiv = (ConstStageMatrix,ConstStageRisei,ConstStageDiv) #cache

            #print(self.matrix)
            #print(self.stage_dict)
            #理性計算に必要なステージ数
            stages_need = self.TotalCount - len(ConvertionMatrix) - len(ConstStageMatrix)
            print("必要ステージ数:",stages_need)
            det = 0
            #stageMatrix = []
            #stageRisei = []
            while(abs(det) < 50):
                seeds = [-1]*stages_need
                for i in range(stages_need):
                    nowCategory = list(get_StageCategoryDict(self.Global).keys())[i]
                    print(i,get_StageCategoryDict(self.Global)[nowCategory])
                    randomStageId = random.choice(self.category_BaseIds[nowCategory])
                    seeds[i] = self.valid_stages_getindex[randomStageId]
                stageMatrix, stageRisei,stageDiv = self._getStageMatrix(seeds)
                det = self._detMatrix((ConvertionMatrix,ConstStageMatrix,stageMatrix))
            
            print("Seed Stages:",self._seed2StageName(seeds),"det=",det)
            seedValues = self._getValues((ConvertionMatrix,ConstStageMatrix,stageMatrix),[ConvertionRisei,ConstStageRisei,stageRisei])
            print("Seed Values:",seedValues)
            #print(self._getStageValues(seedValues))
            stageValues = self._getBaseStageValues(seedValues)
            #理性効率の最大を求める これを1にするように後で調整
            maxValue = max(stageValues.items(),key=lambda x: x[1])
            if maxValue[1] > 1+1e-5:
                print(maxValue,'基準より高い効率を検出:',self.stageId_to_name[maxValue[0]])

            while(maxValue[1] > 1+1e-5):
                #理性効率が最大になるステージを、同カテゴリのステージと差し替える
                #カテゴリが複数該当する場合、全て試してみたのち理性効率が小さい方を選ぶ
                #最大理性効率が1でなければ、これを繰り返す
                targetCategories = self._getCategoryFromStageId(maxValue[0])
                print('基準マップ差し替え：ターゲットカテゴリ',targetCategories)
                if len(targetCategories) == 0:
                    msg = 'カテゴリから外れたマップを検出、計算を中断します\n'
                    msg += 'マップ'+self.stageId_to_name[maxValue[0]]+'は、何を稼ぐステージですか？\n'
                    return msg
                maxValuesDict = {}
                for item in targetCategories:
                    newSeeds = np.copy(seeds)
                    targetIndex = list(get_StageCategoryDict(self.Global).keys()).index(item)
                    newSeeds[targetIndex] = self.valid_stages_getindex[maxValue[0]]
                    #print(newSeeds)
                    newMatrix,newRisei,newDiv = self._getStageMatrix(newSeeds)
                    det = self._detMatrix((ConvertionMatrix,ConstStageMatrix,newMatrix))
                    #print(det)
                    if(abs(det) < 1):
                        continue
                    newSeedValues = self._getValues((ConvertionMatrix,ConstStageMatrix,newMatrix),[ConvertionRisei,ConstStageRisei,newRisei])
                    newStageValues = self._getBaseStageValues(newSeedValues)
                    newMaxValue = max(newStageValues.items(),key=lambda x:x[1])
                    maxValuesDict[item]=newMaxValue
                #最大理性効率が最も小さいものが、一番良い差し替え
                print('差し替え後、最大効率一覧:',maxValuesDict)
                best_maxValue = min(maxValuesDict.items(),key = lambda x:x[1][1])
                targetIndex = list(get_StageCategoryDict(self.Global).keys()).index(best_maxValue[0])
                seeds[targetIndex] = self.valid_stages_getindex[maxValue[0]]
                print('差し替え完了、現在の最大効率マップ:',best_maxValue)
                maxValue = best_maxValue[1]
            #最適なseedを使い再度効率計算
            #場合によっては無駄になるけど考えるのがめんどくさくなったから計算の暴力で
            stageMatrix,stageRisei,stageDiv = self._getStageMatrix(seeds)
            self.stageMatrix,self.stageRisei,self.stageDiv = (stageMatrix,stageRisei,stageDiv) #save Cache
            self.seeds = seeds
            #計算成功後、前回の入力パラメータを保存
            #self.minTimes,self.Mode,self.baseMinTimes,self.Global = (parameters["min_times"],parameters["mode"],parameters["min_basetimes"],parameters["is_global"])

        seedValues = self._getValues((ConvertionMatrix,ConstStageMatrix,stageMatrix),[ConvertionRisei,ConstStageRisei,stageRisei])
        stageValues = self._getStageValues(seedValues)
        sorted_stageValues = sorted(stageValues.items(),key=lambda x:x[1],reverse=True)

        #誤差項計算
        xDivs = self._getMaterialDiv((ConvertionMatrix,ConstStageMatrix,stageMatrix),(ConvertionDiv,ConstStageDiv,stageDiv),seedValues)
        xSD95 = self._divToSD95(xDivs)
        stageSD95 = self._getStageValueSD95((ConvertionMatrix,ConstStageMatrix,stageMatrix),(ConvertionDiv,ConstStageDiv,stageDiv),seedValues,seeds)
        name_to_Value = {get_ValueTarget(self.Global)[x]:(seedValues[x],xSD95[x]) for x in range(self.TotalCount)}                
        exclude_Videos_Values = seedValues[4:]

        #print("*******計算結果*********")
        try:
            modeWord = {"Sanity":"理性","Time":"時間"}[self.Mode]
            selection = {"Sanity":"apCost","Time":"timeCost"}[self.Mode]
            if(to_print == "basemaps"):
                basemaps = "基準マップ一覧:`{0}`".format({get_StageCategoryDict(self.Global)[x]["to_ja"]:self._seed2StageName(seeds)[list(get_StageCategoryDict(self.Global).keys()).index(x)] for x in get_StageCategoryDict(self.Global).keys()})
                return basemaps
            #print("基準マップ分散:")
            #for i in range(len(StageCategoryDict.keys())):
            #    print("{0} : {1}".format(StageCategoryDict.keys()[i],stageDiv[i]))
            elif(to_print == "sanValueLists"):
                sanValueLists = StringIO()
                sys.stdout = sanValueLists
                print("{0}価値一覧:".format(modeWord))
                print('```')
                for key,value in name_to_Value.items():
                    print("{0}: {1:.3f} ± {2:.3f}".format(left(15,self.item_zh_to_ja[key]),value[0],value[1]))
                #print("各マップの理性効率:",{self.stageId_to_name[key]:(value,stageSD95[key]) for key,value in stageValues.items()})
                print('```')
                sys.stdout = sys.__stdout__
                sanValueLists = sanValueLists.getvalue()
                return sanValueLists
            elif(to_print == "items"):
                if target_forPrint not in get_StageCategoryDict(self.Global).keys():
                    return "無効なカテゴリ:" + target_forPrint
            #print("\n***********************\n")
            #print(sorted_stageValues)
            #print("カテゴリ別効率順:")
                category = target_forPrint
                Header = get_StageCategoryDict(self.Global)[category]["to_ja"] + ": 理性価値(中級)={0:.3f}±{1:.3f}\n".format(name_to_Value[get_StageCategoryDict(self.Global)[category]['MainItem']][0],name_to_Value[get_StageCategoryDict(self.Global)[category]['MainItem']][1])
                stage_toPrint = [x for x in sorted_stageValues if x[0] in self.category_ValidIds[category]]
                targetItemIndex = [get_ValueTarget(self.Global).index(x) for x in get_StageCategoryDict(self.Global)[category]["Items"]]
                targetItemValues = seedValues[targetItemIndex]
                cnt = 0
                msg_list = [Header]
                for item in stage_toPrint:
                    cnt+=1
                    toPrint_item = [
                        ["```マップ名       : ",self.stageId_to_name[item[0]],],
                        ["{1}効率       : {0:.1f}%".format(100*item[1],modeWord)],
                        ["理性消費       : ".format(modeWord),str(self.stage_dict[item[0]]["apCost"])],
                        ["時間消費       : ".format(modeWord),str(self.stage_dict[item[0]]["timeCost"])],
                        ["95%信頼区間(2σ): {0:.1f}%".format(100*stageSD95[item[0]])],
                        ["主素材効率     : {0:.1f}%".format(100*np.dot(targetItemValues,self.stage_dict[item[0]]["array"][targetItemIndex])/self.stage_dict[item[0]][selection])],
                        ["昇進効率       : {0:.1f}%".format(100*np.dot(exclude_Videos_Values,self.stage_dict[item[0]]["array"][4:])/self.stage_dict[item[0]][selection])],
                        ["試行数         : ",str(self.stage_dict[item[0]]["maxTimes"])],
                        ["最小試行数     : ",str(self.stage_dict[item[0]]["minTimes"]),"```"],
                    ]
                    msg_list.append("\n".join(["".join(x) for x in toPrint_item]))
                    if(parameters["max_items"]>0 and cnt>=parameters["max_items"]):
                        break
                    #print(targetItemValues)
                    #print(self.stage_dict[item[0]]["array"][targetItemIndex])
                #print("********************************")
                return msg_list
            elif(to_print == "zone"):
                #章別検索
                stage_toPrint = [x for x in stageValues.items() if target_forPrint in self.stageId_to_name[x[0]]]
                if len(stage_toPrint) == 0:
                    return "無効なステージ指定："+target_forPrint
                Header = "検索内容 = " + target_forPrint
                msg_list = [Header]
                for item in stage_toPrint:
                    dropItemCategoryList = [x for x in get_StageCategoryDict(self.Global).keys() if self.stageId_to_name[item[0]] in get_StageCategoryDict(self.Global)[x]['Stages']]
                    toPrint_item = [
                        ["```マップ名       : ",self.stageId_to_name[item[0]]],
                        ["総合{1}効率    : {0:.1f}%".format(100*item[1],modeWord)],
                        ["95%信頼区間(2σ): {0:.1f}%".format(100*stageSD95[item[0]])],
                    ]
                    if len(dropItemCategoryList) == 0:
                        toPrint_item.append(["主ドロップ情報未登録"])
                    else:
                        for dropItemCategory in dropItemCategoryList:
                            targetItemIndex = [get_ValueTarget(self.Global).index(x) for x in get_StageCategoryDict(self.Global)[dropItemCategory]["Items"]]
                            targetItemValues = seedValues[targetItemIndex]
                            toPrint_item.append(["{0}: {1:.1f}%".format(left(15,get_StageCategoryDict(self.Global)[dropItemCategory]["to_ja"]+"効率"),\
                                100*np.dot(targetItemValues,self.stage_dict[item[0]]["array"][targetItemIndex])/self.stage_dict[item[0]][selection])])
                    toPrint_item += [
                        ["理性消費       : ".format(modeWord),str(self.stage_dict[item[0]]["apCost"])],
                        ["時間消費       : ".format(modeWord),str(self.stage_dict[item[0]]["timeCost"])],
                        ["昇進効率       : {0:.1f}%".format(100*np.dot(exclude_Videos_Values,self.stage_dict[item[0]]["array"][4:])/self.stage_dict[item[0]][selection])],
                        ["試行数         : ",str(self.stage_dict[item[0]]["maxTimes"])],
                        ["最小試行数     : ",str(self.stage_dict[item[0]]["minTimes"]),"```"],
                    ]
                    msg_list.append("\n".join(["".join(x) for x in toPrint_item]))
                    cnt = len(msg_list)-1
                    if(parameters["max_items"]>0 and cnt>=parameters["max_items"]):
                        break
                return msg_list
            #イベント検索
            elif(to_print == "events"):
                eventValues = self._getEventValues(seedValues)
                #sorted_eventValues = sorted(eventValues.items(),key=lambda x:x[1],reverse=True)
                #print("event_search = ",self.event_search)
                #print("eventValues=",eventValues)
                #print("event_stages",self.event_stages)
                #print("eventIds",self.eventIds)

                if target_forPrint == "":
                    return "検索の内容を指定してください"

                es_toPrint = [x for x in eventValues.items() if target_forPrint in self.stageId_to_name[x[0]]]
                msg_list = []
                for item in es_toPrint:
                    try:
                        maxIndex = np.argmax(self.event_dict[item[0]]["array"])
                        dropItemCategory = self.item_zh_to_ja[get_ValueTarget(self.Global)[maxIndex]]
                    except IndexError as e:
                        dropItemCategory = "不明"
                    toPrint_item = [
                        ["```マップ名       : ",self.stageId_to_name[item[0]]+("(Re)" if "re_" in self.eventStages[self.eventIds.index(item[0])]["zoneId"] else "")],
                        ["イベント名     : ",self.zoneId_to_Name_ja[self.eventStages[self.eventIds.index(item[0])]["zoneId"]]],
                        ["総合{1}効率   : {0:.1f}%".format(100*item[1],modeWord)],
                        ["主ドロップ     : ",dropItemCategory],
                        ["ドロップ率     : {0:.2f}%".format(100*self.event_dict[item[0]]["array"][maxIndex])],
                        ["試行数         : ",str(self.event_dict[item[0]]["maxTimes"])],
                        ["理性消費       : ",str(self.event_dict[item[0]]["apCost"])],
                    ]
                    if self.event_dict[item[0]]["timeCost"] != None:
                        toPrint_item += [
                            ["時間消費(倍速) : ", str(self.event_dict[item[0]]["timeCost"]/2.0)],
                            #ドロップアイテム推定
                            ["分間入手数     : {0:.2f}".format(self.event_dict[item[0]]["array"][maxIndex]/self.event_dict[item[0]]["timeCost"]*120)],
                        ]
                    toPrint_item += ["```"]
                    msg_list.append("\n".join(["".join(x) for x in toPrint_item]))
                    cnt = len(msg_list)
                    if(parameters["max_items"]>0 and cnt>=parameters["max_items"]):
                        break
                return msg_list
            elif(to_print == "te2List"):
            #資格証効率計算
            #初級資格証
                ticket_efficiency2 = {x:name_to_Value[x][0]/Price[x] for x in get_Item_rarity2(self.Global)}
                ticket_efficiency2_sorted = {key:(value,xSD95[self.name_to_index[key]]/Price[key]) for key,value in sorted(ticket_efficiency2.items(),key=lambda x:x[1],reverse=True)}

                te2List = "初級資格証効率：```"
                to_print = []
                for key,value in ticket_efficiency2_sorted.items():
                    to_print.append("{0}:\t{1:.3f} ± {2:.3f}".format(left(15,self.item_zh_to_ja[key]),value[0],value[1]))
                te2List += "\n".join(to_print) + "```"
                return te2List

            elif(to_print == "te3List"):
                #上級資格証
                ticket_efficiency3 = {x:name_to_Value[x][0]/Price[x] for x in get_Item_rarity3(self.Global)}
                ticket_efficiency3_sorted = {key:(value,xSD95[self.name_to_index[key]]/Price[key]) for key,value in sorted(ticket_efficiency3.items(),key=lambda x:x[1],reverse=True)}

                te3List = "上級資格証効率：```"
                to_print = []
                for key,value in ticket_efficiency3_sorted.items():
                    to_print.append("{0}: {1:.3f} ± {2:.3f}".format(left(15,self.item_zh_to_ja[key]),value[0],value[1]))
                te3List += "\n".join(to_print) + "```"
                return te3List

            elif(to_print == "specialList"):
                #特別引換証
                ticket_efficiency_special = {x:name_to_Value[x][0]/Price_Special[x] for x in get_Item_rarity2(self.Global) + get_Item_rarity3(self.Global)}
                ticket_efficiency_special_sorted = {key:(value,xSD95[self.name_to_index[key]]/Price_Special[key]) for key,value in sorted(ticket_efficiency_special.items(),key=lambda x:x[1],reverse=True)}

                specialList = "特別引換証効率：```"
                to_print = []
                for key,value in ticket_efficiency_special_sorted.items():
                    to_print.append("{0}: {1:.3f} ± {2:.3f}".format(left(15,self.item_zh_to_ja[key]),value[0],value[1]))
                specialList += "\n".join(to_print) + "```"
                return specialList
            elif(to_print == "ccList"):
                #契約賞金引換証
                ccNumber = '11'
                Price_CC = list()
                try:
                    with open('price_cc{0}.txt'.format(ccNumber), 'r', encoding='utf8') as f:
                        for line in f.readlines():
                            name, value ,quantity = line.split()
                            Price_CC.append([name,float(value),quantity])
                except FileNotFoundError as e:
                    return "CC#{0}の交換値段が未設定です！".format(ccNumber)
                ccList  = "契約賞金引換効率(CC#{0})：```".format(ccNumber)
                ticket_efficiency_CC = [[x[0],(name_to_Value[x[0]][0]/x[1],xSD95[self.name_to_index[x[0]]]/x[1]),x[2]] for x in Price_CC if x[0] in get_ValueTarget(self.Global)]
                ticket_efficiency_CC_sorted = sorted(ticket_efficiency_CC,key=lambda x:x[1][0],reverse=True)
                to_print = []
                for item in ticket_efficiency_CC_sorted:
                    value = item[1]
                    to_print.append("{0}: {1:.3f} ± {2:.3f}".format(left(20,self.item_zh_to_ja[item[0]]+'({0})'.format(item[2])),value[0],value[1]))
                ccList += "\n".join(to_print) + "```"
                return ccList

            else:
                return "未知のコマンド:" + to_print
        finally:
            if need_reCalculate:
                #メインデータの書き出し
                Columns_Name = [self.item_zh_to_ja[x] for x in get_ValueTarget(self.Global)] + ['理性消費']
                Rows_Name_Convertion = ['経験値換算1','経験値換算2','経験値換算3','純金換算'] +\
                    ['合成-'+self.item_zh_to_ja[x['name']] for x in self.formula if x['name'] in get_ValueTarget(self.Global)] +\
                    ['スキル本換算1','スキル本換算2']
                Rows_Name_ConstStage = {'5':['LS-5','CE-5','CA-5'],'6':['LS-6','CE-6','CA-5']}[self.LS_CE]
                Rows_Name_Stages = [get_StageCategoryDict(self.Global)[list(get_StageCategoryDict(self.Global).keys())[x]]["to_ja"] + self._seed2StageName(seeds)[x] for x in range(stages_need)]
                Rows_Name = Rows_Name_Convertion+Rows_Name_ConstStage+Rows_Name_Stages + ['理性価値']
                #print(Columns_Name)
                #print(Rows_Name)
                main_data = np.vstack((ConvertionMatrix,ConstStageMatrix,stageMatrix,seedValues))
                main_data = np.hstack((main_data,np.concatenate([ConvertionRisei,ConstStageRisei,stageRisei,[0]]).reshape(-1,1)))
                #print("Main_Data:",main_data)
                #print("Columns_Name:",Columns_Name)
                #print("Rows_Name:",Rows_Name)
                df = pd.DataFrame(main_data,columns=Columns_Name,index=Rows_Name)
                df.to_csv('BaseStages.csv',encoding='utf-8-sig')
                print("基準マップデータをBaseStages.csvに保存しました")

TOKEN = os.environ["BOT_TOKEN"]
ID = os.environ["BOT_ID"]
url_botCommands = "https://discord.com/api/v8/applications/{0}/commands".format(ID)

client = commands.Bot(command_prefix = '/')

slash = slash_commands.SlashClient(client)
test_guilds = [int(os.environ["GUILD_ID"])]
rc = None
@slash.command(
    name = 'riseicalculator',
    description = '理性価値表計算',
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
    guild_ids = test_guilds
)

async def riseicalculator(inter,target,target_item = "",event_code = "", mode="Sanity",min_times=1000,min_basetimes=3000,max_items=15,csv_file = False,is_global=True,cache_time = 30):
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
    finally:
        #channel = inter.channel()
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
        if rc != None:
            createdTime = "\n作成時間:\t{0}".format(rc.UpdatedTime)
            await inter.followup(createdTime,file = discord.File('BaseStages.csv') if csv_file else None)

    #print(rc.convert_rules)

@client.event
async def on_ready():
    print('Botでログインしました')

client.run(TOKEN)