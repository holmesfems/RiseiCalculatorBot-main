import yaml

LMDVALUE_1000 = 3.6

valueDict = {
    "合成玉":0.75,
    "スカウト券":450.0,
    "初級理性回復剤+":80.0,
    "初級SoC":18*(1-12*LMDVALUE_1000/1000),
    "中級SoC":36*(1-12*LMDVALUE_1000/1000),
    "SoC強化剤":90*(30*(1-12*LMDVALUE_1000/1000)/21),
}
valueDict["上級SoC"] = 2*valueDict["中級SoC"] + valueDict["SoC強化剤"]
valueDict["モジュールデータ"]=120*(30*(1-12*LMDVALUE_1000/1000)/21)
valueDict["純正源石"] = 135
valueDict["コーデ交換券"] = valueDict["純正源石"]*18
valueDict["中級SoCセルフプリンター"] = valueDict["中級SoC"]
valueDict["★6印交換券"] = valueDict["スカウト券"]*69.2
valueDict["10回スカウト券"] = valueDict["スカウト券"]*10
print(valueDict)

with open("riseicalculator2/constValues.yaml","wb") as f:
    yaml.safe_dump(valueDict,f,allow_unicode=True,encoding="utf-8",sort_keys=False)