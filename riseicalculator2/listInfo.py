from typing import List
import yaml
from collections import ChainMap

#ドロップアイテム&ステージのカテゴリ情報を入手
with open("riseicalculator2/StageCategoryDict.json","rb") as file:
    StageCategoryDict = yaml.safe_load(file)

#一部理論値と実際のクリア時間が乖離しているステージで個別修正
with open("riseicalculator2/minClearTimeInjection.json","r") as file:
    minClearTimeInjection = yaml.safe_load(file)

Item_rarity2:List[str] = [
    '固源岩组','全新装置','聚酸酯组', 
    '糖组','异铁组','酮凝集组',
    '扭转醇','轻锰矿','研磨石',
    'RMA70-12','凝胶','炽合金',
    '晶体元件','半自然溶剂','化合切削液',
    '转质盐组'
]

Item_rarity2_new:List[str] = [
    
]

Item_rarity3:List[str] = [
    '提纯源岩','改量装置','聚酸酯块', 
    '糖聚块','异铁块','酮阵列', 
    '白马醇','三水锰矿','五水研磨石',
    'RMA70-24','聚合凝胶','炽合金块',
    '晶体电路','精炼溶剂','切削原液',
    '转质盐聚块'
]

Item_rarity3_new:List[str] = [
    
]

Item_rarity4:List[str] = [
    '聚合剂', '双极纳米片', 'D32钢','晶体电子单元','烧结核凝晶'
]

Item_rarity4_new:List[str] = [
    
]

ValueTarget:List[str] = [
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
    '转质盐组','转质盐聚块',
    '聚合剂', '双极纳米片', 'D32钢','晶体电子单元','烧结核凝晶',
    '技巧概要·卷1', '技巧概要·卷2', '技巧概要·卷3',
]

ValueTarget_new:List[str] = [
    
]

#大陸版基準、グロ版基準調整用
def getGlobalOrMainland(ParamName,glob:bool):
    if glob:
        return eval(ParamName)
    else:
        return eval(ParamName) + eval(ParamName+'_new')

def getItemRarity2(glob:bool) -> List[str]:
    return getGlobalOrMainland("Item_rarity2",glob)

def getItemRarity3(glob:bool) -> List[str]:
    return getGlobalOrMainland("Item_rarity3",glob)

def getItemRarity4(glob:bool) -> List[str]:
    return getGlobalOrMainland("Item_rarity4",glob)

def getValueTarget(glob:bool) -> List[str]:
    return getGlobalOrMainland("ValueTarget",glob)

def getStageCategoryDict(glob:bool):
    if glob:
        return StageCategoryDict["main"]
    else:
        return ChainMap(StageCategoryDict["main"],StageCategoryDict["new"])