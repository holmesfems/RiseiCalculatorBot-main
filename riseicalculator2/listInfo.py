from typing import List,Dict,Union
import yaml
import sys
from dataclasses import dataclass,field
sys.path.append('../')
from infoFromOuterSource.idtoname import ItemIdToName

@dataclass
class StageCategoryInfo:
    Stages: List[str]
    Items: List[str]
    MainItem: str
    to_ja: str
    SubItem: List[str] = field(default_factory=list)
    SubOrder: List[int] = field(default_factory=list)

#ドロップアイテム&ステージのカテゴリ情報を入手
with open("riseicalculator2/StageCategoryDict.json","rb") as file:
    StageCategoryDict:Dict = yaml.safe_load(file)
    MainCategoryDict:Dict[str,StageCategoryInfo] = {key:StageCategoryInfo(**value) for key,value in StageCategoryDict['main'].items()}
    NewCategoryDict:Dict[str,StageCategoryInfo] = {key:StageCategoryInfo(**value) for key,value in StageCategoryDict['new'].items()}

#一部理論値と実際のクリア時間が乖離しているステージで個別修正
with open("riseicalculator2/minClearTimeInjection.yaml","rb") as file:
    minClearTimeInjection:Dict = yaml.safe_load(file)

Item_rarity2:List[str] = [
    '固源岩组','全新装置','聚酸酯组', 
    '糖组','异铁组','酮凝集组',
    '扭转醇','轻锰矿','研磨石',
    'RMA70-12','凝胶','炽合金',
    '晶体元件','半自然溶剂','化合切削液',
    '转质盐组','褐素纤维', '环烃聚质'
]

Item_rarity2_new:List[str] = [
    
]

Item_rarity3:List[str] = [
    '提纯源岩','改量装置','聚酸酯块', 
    '糖聚块','异铁块','酮阵列', 
    '白马醇','三水锰矿','五水研磨石',
    'RMA70-24','聚合凝胶','炽合金块',
    '晶体电路','精炼溶剂','切削原液',
    '转质盐聚块','固化纤维板','环烃预制体'
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
    '褐素纤维','固化纤维板',
    '环烃聚质','环烃预制体',
    '聚合剂', '双极纳米片', 'D32钢','晶体电子单元','烧结核凝晶',
    '技巧概要·卷1', '技巧概要·卷2', '技巧概要·卷3',
]

ValueTarget_new:List[str] = [
    
]

#契約賞金引換証
__ccNumber = '2'
class CCExchangeItem:
    def __init__(self,dictItem:dict):
        self.name = dictItem["name"]
        self.quantity = dictItem["quantity"]
        self.value = dictItem["value"]

    def __repr__(self)->str:
        return f"{self.fullname()}:{self.value}"
    
    def fullname(self)->str:
        jaName = ItemIdToName.zhToJa(self.name)
        if(self.quantity == "∞"):
            return f"{jaName}({self.quantity})"
        else:
            return f"{jaName}"

with open(f"riseicalculator2/price_cc{__ccNumber}.yaml","rb") as f:
    __price_CC = yaml.safe_load(f)
    __price_CC:List[CCExchangeItem] = [CCExchangeItem(item) for item in __price_CC]
    #print(__price_CC)

with open(f"riseicalculator2/price_pinchout.yaml","rb") as f:
    __price_PO = yaml.safe_load(f)
    __price_PO:List[CCExchangeItem] = [CCExchangeItem(item) for item in __price_PO]
    #print(__price_CC)

def getCCList() -> List[CCExchangeItem]:
    return __price_CC

def getPOList() -> List[CCExchangeItem]:
    return __price_PO

def getCCNumber() -> str:
    return __ccNumber

with open("riseicalculator2/price_kakin.yaml","rb") as f:
    kakinList_JP:Dict[str,Dict[str,Union[float,Dict[str,float]]]] = yaml.safe_load(f)

with open("riseicalculator2/price_kakin_cn.yaml","rb") as f:
    kakinList_CN:Dict[str,Dict[str,Union[float,Dict[str,float]]]] = yaml.safe_load(f)

def getKakinList(glob:bool)->Dict[str,Dict[str,Union[float,Dict[str,float]]]]:
    if glob: return kakinList_JP
    else: return kakinList_CN

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
        return MainCategoryDict
    else:
        return {**MainCategoryDict,**NewCategoryDict}
    
def estimateCategoryFromJPName(current:str):
    with open("riseicalculator2/categoryEnToZh.yaml","rb") as f:
        categoryEnToZh:Dict[str,str] = yaml.safe_load(f)
    if zh := categoryEnToZh.get(current,None):
        return zh
    categoryDict = getStageCategoryDict(glob=False)
    if(estimatedValue:=next(filter(lambda x: current in x[1].to_ja or x[1].to_ja in current,categoryDict.items()),None)):
        return estimatedValue[0]
    return current
    