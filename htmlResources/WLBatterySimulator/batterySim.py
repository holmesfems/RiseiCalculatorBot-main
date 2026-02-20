import numpy
from pydantic import BaseModel
from typing import List
from abc import ABC, abstractmethod
from queue import Queue

maxStorage = 100000

def last_true_index(lst: list[bool]) -> int:
    for i in range(len(lst) - 1, -1, -1):
        if lst[i]:
            return i
    return -1  # Trueが一つもない場合

class PowerController(ABC):
    def __init__(self):
        self.switchOnOff: list[bool] = ...
        self.switchState: list[int] = ...
        self.maxPower: int = ...
        self.switchValue: list[float] = ...
        self.delay: list[int] = ...

    @abstractmethod
    def fit(self,requiredPower:int):
        result = [False]*len(self.switchValue)
        remain = requiredPower
        for i in range(len(self.switchValue)):
            if(remain >= self.switchValue[i]):
                remain -= self.switchValue[i]
                result[i] = True
            if(remain == 0): break
        if(remain > 0): result[-1] = True
        self.switchOnOff = result

class PowerControllerWuling(PowerController):
    switchValue = [800,400,200,100,50,25,5,5,5,5,5]
    class LoopIndex:
        def __init__(self, loop:List[int]):
            self.loop = loop
        def __getitem__(self, index:int):
            return self.loop[index]

    def __init__(self):
        super().__init__()
        self.switchState = [0,0,0,0,0,0,0]
        self.switchValue = [800,400,200,100,50,25,5,5,5,5,5]
        self.delay = [0,0,0,0,0,0,16,12,12,8,8]
        self.switchOnOff = [False]*len(self.switchValue)
        self.maxPower = 1600
        self.loopbackDelay = 8
        self.loopbackTarget = 0
        self.loopIndex:PowerControllerWuling.LoopIndex = ...
        self.remainLoop:Queue[PowerControllerWuling.LoopIndex] = Queue()

    def fit(self,requiredPower:int):
        super().fit(requiredPower)
        fiveOnOff = self.switchOnOff[6:]
        onNum = len([x for x in fiveOnOff if x])
        self.remainLoop = Queue()
        if(onNum <= 2):
            self.switchOnOff[6:] = [self.switchOnOff[7],self.switchOnOff[6],False,False,False]
            self.loopIndex = PowerControllerWuling.LoopIndex([2,0,3,1,4])
        elif(onNum==3): #2の部分は順序が影響を与えない
            self.switchOnOff[6:] = [False,False,True,True,True]
            allLoop = [
                [2,0,3,1,4],
                [2,0,4,1,3],
                [3,0,2,1,4],
                [3,0,4,1,2],
                [4,0,2,1,3],
                [4,0,3,1,2]
            ]
            for loop in allLoop:
                self.remainLoop.put(PowerControllerWuling.LoopIndex(loop))
            self.loopIndex = self.remainLoop.get()
        elif(onNum >= 4):
            self.switchOnOff[6:] = [self.switchOnOff[10], self.switchOnOff[9], True,True,True]
            allLoop = [
                [2,0,3,1,4],
                [2,0,4,1,3],
                [3,0,2,1,4],
                [3,0,4,1,2],
                [4,0,2,1,3],
                [4,0,3,1,2],
                [2,1,3,0,4],
                [2,1,4,0,3],
                [3,1,2,0,4],
                [3,1,4,0,2],
                [4,1,2,0,3],
                [4,1,3,0,2],
            ]
            for loop in allLoop:
                self.remainLoop.put(PowerControllerWuling.LoopIndex(loop))
            self.loopIndex = self.remainLoop.get()

    def needRetry(self):
        return not self.remainLoop.empty()
    
    def retry(self):
        self.loopIndex = self.remainLoop.get()
        self.resetState()

    def resetState(self): 
        self.switchState = [0,0,0,0,0,0,0]
    def increasePower(self):
        power = self.nowPower()
        power = power+5
        self.fit(power)
        self.resetState()
    def next(self): 
        #2分割部分
        for i in range(6):
            if(self.switchState[i] == 0):
                self.switchState[i] = 1
                return (self.switchOnOff[i],self.delay[i])
            else:
                self.switchState[i] = 0
        #5分割部分
        index = 6+self.loopIndex[self.switchState[6]]
        result = self.switchOnOff[index]
        delay = self.delay[index]
        if(self.switchState[6] == 0): delay += self.loopbackDelay
        self.switchState[6] = (self.switchState[6] + 1)%5
        return (result,delay)
    
    def period(self):
        switchDepth = last_true_index(self.switchOnOff)
        if(switchDepth < 0): return -1
        period = self.maxPower / PowerControllerWuling.switchValue[switchDepth]
        return int(period)
    
    def isMax(self):
        return numpy.all(self.switchOnOff)
    
    def nowPower(self)->int:
        return numpy.sum(
            [PowerControllerWuling.switchValue[i] * 1 if self.switchOnOff[i] else 0
             for i in range(len(PowerControllerWuling.switchValue))]
        )
    
    def toBit(self)->str:
        result = ""
        for onOff in self.switchOnOff:
            if(onOff): result += "1"
            else: result +="0"
        return result
    
    def isUnder5(self):
        return numpy.any(self.switchOnOff[6:])

class BatterySimResult(BaseModel):
    time: List[int]
    value: List[int]
    isValid: bool

def simulate(requiredPower:int, controller:PowerControllerWuling):
    powerRemain = maxStorage
    period = controller.period()
    clock = 40
    t = []
    v = []
    nowt = 0
    nowd = 0
    isFirst = True
    def doOnce():
        nonlocal nowt,powerRemain,isFirst,nowd
        (isAccept,delay) = controller.next()
        if(isFirst): 
            t.append(nowt)
            v.append(powerRemain)
        nowt += clock
        isFirst = False
        if(isAccept):
            #遅延を考慮したシミュレーション
            if(nowd >= delay):
                delay = nowd
            else:
                t.append(nowt+delay-clock)
                powerRemain = powerRemain - requiredPower * (delay-nowd)
                if(powerRemain < 0): powerRemain = 0
                v.append(powerRemain)
                if(powerRemain==0): return False
            t.append(nowt+delay)
            powerRemain = powerRemain + (controller.maxPower - requiredPower)*40
            if(powerRemain > maxStorage): powerRemain = maxStorage
            v.append(powerRemain)
            nowd = delay
        else:
            powerRemain = powerRemain - requiredPower * (40-nowd)
            if(powerRemain < 0): powerRemain = 0
            nowd = 0
            t.append(nowt)
            v.append(powerRemain)
            if(powerRemain == 0): return False
        return True

    #二周期分シミュレートする
    for i in range(2*period+1):
        if( not doOnce()):
            return BatterySimResult(time=t,value=v,isValid=False)
    if(controller.needRetry()):
        controller.retry()
        return simulate(requiredPower,controller)
    return BatterySimResult(time=t,value=v,isValid=True)

class FitPlan(BaseModel):
    needPower: int
    maxPower: int
    bitStr: str
    simResult: BatterySimResult

def searchFitPlan(requiredPower:int,storageMargin:int,useMarginUnder5:bool):
    controller = PowerControllerWuling()
    controller.fit(requiredPower=requiredPower)
    while True:
        simResult = simulate(requiredPower,controller)
        if(simResult.isValid):

            if((useMarginUnder5 and not controller.isUnder5()) or numpy.min(simResult.value) >= storageMargin ):
                return FitPlan(needPower=controller.nowPower(),bitStr=controller.toBit(),simResult=simResult, maxPower=controller.maxPower)
        controller.increasePower()
        if(controller.isMax()):
            return FitPlan(needPower=controller.nowPower(),bitStr=controller.toBit(),simResult=simResult, maxPower=controller.maxPower)