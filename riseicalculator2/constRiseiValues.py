import yaml

LMDVALUE_1000 = 3.6

valueDict = {
    "合成玉":0.75,
    "寻访凭证":450.0,
    "应急理智加强剂":80.0,
    "芯片":18*(1-12*LMDVALUE_1000/1000),
    "芯片组":36*(1-12*LMDVALUE_1000/1000),
    "芯片助剂":90*(30*(1-12*LMDVALUE_1000/1000)/21),
    "模组数据块":120*(30/21*(1-0.012*LMDVALUE_1000/1000))
}
costomValueDict = {
    "双芯片": 2*valueDict["芯片组"] + valueDict["芯片助剂"]
}

valueDict = {**valueDict,**costomValueDict}
print(valueDict)

with open("riseicalculator2/constValues.yaml","wb") as f:
    yaml.safe_dump(valueDict,f,allow_unicode=True,encoding="utf-8",sort_keys=False)