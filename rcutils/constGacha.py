import yaml
#ガチャに関係するアイテムを集めてガチャ数を計算する

gachaDict = {}
gachaDict["合成玉"] = 1/600
gachaDict["純正源石"] = 180/600
gachaDict["スカウト券"] = 1
gachaDict["10回スカウト券"] = 10
gachaDict["イベントスカウト券"] = 1
gachaDict["イベント10回スカウト券"] = 10

with open("rcutils/constGacha.yaml","wb") as f:
    yaml.safe_dump(gachaDict,f,allow_unicode=True,encoding="utf-8",sort_keys=False)