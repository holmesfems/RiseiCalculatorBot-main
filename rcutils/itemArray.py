from __future__ import annotations
import sys
import yaml
sys.path.append('../')
from infoFromOuterSource.idtoname import ItemIdToName
from typing import Dict
from riseicalculator2 import listInfo
EPSILON = 0.0001
_ORDERCRITERIA = listInfo.getValueTarget(False)
_INDEX_INFINITY = 10000

class ItemArray:
    def __init__(self,itemIdToCountDict:Dict[str,float]={}):
        if(not itemIdToCountDict):
            self.__dict:Dict[str,float] = {}
        else:
            self.__dict = itemIdToCountDict.copy()
        self.__normalized = False
    
    def copy(self)->ItemArray:
        copy = ItemArray()
        copy.__dict = self.__dict.copy()
        copy.__normalized = self.__normalized
        return copy
    
    def __iadd__(self,other:ItemArray):
        for key,value in other.__dict.items():
            if(self.__dict.get(key)):
                self.__dict[key] += value
            else:
                self.__dict[key] = value
            self.__normalized = False
        return self

    def __add__(self,other:ItemArray)->ItemArray:
        copy = self.copy()
        copy += other
        return copy
    
    def __isub__(self,other:ItemArray):
        self += (other * -1)
        return self
    
    def __sub__(self,other:ItemArray)->ItemArray:
        copy = self.copy()
        copy -= other
        return copy
    
    def __imul__(self,factor:float):
        for key in self.__dict.keys():
            self.__dict[key] *= factor
        return self
    
    def __mul__(self,factor:float):
        copy = self.copy()
        copy *= factor
        return copy
    
    def isEmpty(self) -> bool:
        if(not self.__dict): return True
        for value in self.__dict.values():
            if(value): return False
        return True
    
    def normalizeGold(self):
        goldId = ItemIdToName.jaToId("龍門幣")
        if(not self.__dict.get(goldId)): return

        goldId1000 = ItemIdToName.jaToId("龍門幣1000")
        value = self.__dict[goldId]/1000
        if(self.__dict.get(goldId1000)):
            self.__dict[goldId1000] += value
        else:
            self.__dict[goldId1000] = value
        
        #龍門幣1倍を削除
        del self.__dict[goldId]
        return self

    #龍門幣を龍門幣1000に変換したうえで、0項目を削除、順番も変える
    def normalize(self):
        if not self.__normalized:
            self.normalizeGold()
            def sortKey(x):
                zhstr = ItemIdToName.getZH(x[0])
                if zhstr in _ORDERCRITERIA:
                    return _ORDERCRITERIA.index(zhstr)
                else:
                    return _INDEX_INFINITY
            sortedDictItems = sorted(self.__dict.items(),key=sortKey)
            self.__dict = {key:value for key,value in sortedDictItems if abs(value)>EPSILON}
            self.__normalized = True
        return self

    def getById(self,idStr:str) -> float:
        return self.__dict.get(idStr,0)

    def getByZH(self,zhStr:str) -> float:
        id = ItemIdToName.zhToId(zhStr)
        return self.getById(id)
    
    def toIdCountDict(self) -> Dict[str,float]:
        self.normalize()
        return self.__dict.copy()
    
    def toNameCountDict(self)->Dict[str,float]:
        self.normalize()
        return {ItemIdToName.getStr(key):value for key,value in self.__dict.items()}

    
    def toZHStrCountDict(self)->Dict[str,float]:
        self.normalize()
        return {ItemIdToName.getZH(key) : value for key,value in self.__dict.items()}
    
    def filterById(self,idList:Dict[str]) -> ItemArray:
        ret = ItemArray()
        ret.__dict = {key:value for key,value in self.__dict.items() if key in idList}
        ret.__normalized = self.__normalized
        return ret
    
    def filterByZH(self,zhList:Dict[str]) -> ItemArray:
        return self.filterById([ItemIdToName.zhToId(zh) for zh in zhList])
    