import yaml
#理性価値が固定値であるものを列挙、計算する

LMDVALUE_1000 = 3.6 #幣1000の理性価値
EXPVALUE_1000 = 3.44448 #経験値1000(中級作戦記録)の理性価値

valueDict = {
    "合成玉":0.75,
    "スカウト券":450.0,
    "初級理性回復剤+":80.0,
    "初級SoC":18*(1-12*LMDVALUE_1000/1000),
    "中級SoC":36*(1-12*LMDVALUE_1000/1000),
    "SoC強化剤":90*(30*(1-12*LMDVALUE_1000/1000)/21),
    "特級素材交換券": 90,
    "高級素材交換券": 26,
}
valueDict["上級SoC"] = 2*valueDict["中級SoC"] + valueDict["SoC強化剤"]
valueDict["モジュールデータ"]=120*(30*(1-12*LMDVALUE_1000/1000)/21)
valueDict["純正源石"] = 135
valueDict["コーデ交換券"] = valueDict["純正源石"]*18
valueDict["SoCセルフプリンター"] = valueDict["初級SoC"]*5
valueDict["中級SoCセルフプリンター"] = valueDict["中級SoC"]*8+valueDict["初級SoC"]*5
valueDict["★6印交換券"] = valueDict["スカウト券"]*69.2
valueDict["10回スカウト券"] = valueDict["スカウト券"]*10
valueDict["エリート特訓装置"] = EXPVALUE_1000*495 + LMDVALUE_1000*447.378
valueDict["上級エリート特訓装置"] = EXPVALUE_1000*750 + LMDVALUE_1000*744.955
valueDict["テンニンカ指名契約"] = valueDict["スカウト券"]
valueDict["★5特訓招待状"] = 371.947*LMDVALUE_1000 + 239.4*EXPVALUE_1000 + 4*valueDict["初級SoC"] + 3*valueDict["上級SoC"] + 1100
valueDict["★6特訓招待状"] = 589.841*LMDVALUE_1000 + 361.4*EXPVALUE_1000 + 5*valueDict["初級SoC"] + 4*valueDict["上級SoC"] + 1700
valueDict["18石コーデ"] = 18*valueDict["純正源石"]

print(valueDict)

with open("riseicalculator2/constValues.yaml","wb") as f:
    yaml.safe_dump(valueDict,f,allow_unicode=True,encoding="utf-8",sort_keys=False)