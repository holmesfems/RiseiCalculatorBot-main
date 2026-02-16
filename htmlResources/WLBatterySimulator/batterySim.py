import numpy
from pydantic import BaseModel
from typing import List

maxStorage = 100000

def last_true_index(lst: list[bool]) -> int:
    for i in range(len(lst) - 1, -1, -1):
        if lst[i]:
            return i
    return -1  # Trueが一つもない場合

class PowerControllerWuling():
    switchValue = [800,400,200,100,50,25,5,5,5,5,5]
    def __init__(self):
        self.switchOnOff = [False]*len(PowerControllerWuling.switchValue)
        self.switchState = [0,0,0,0,0,0,0]
        self.maxPower = 1600
    def fit(self,requiredPower:int):
        result = [False]*len(PowerControllerWuling.switchValue)
        remain = requiredPower
        for i in range(len(PowerControllerWuling.switchValue)):
            if(remain >= PowerControllerWuling.switchValue[i]):
                remain -= PowerControllerWuling.switchValue[i]
                result[i] = True
        self.switchOnOff = result
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
                return self.switchOnOff[i]
            else:
                self.switchState[i] = 0
        #5分割部分
        result = self.switchOnOff[6+self.switchState[6]]
        self.switchState[6] = (self.switchState[6] + 3)%5
        return result
    
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

class BatterySimResult(BaseModel):
    time: List[int]
    value: List[int]
    isValid: bool

def simulate(requiredPower:int, controller:PowerControllerWuling):
    powerRemain = maxStorage
    period = controller.period()
    t = []
    v = []
    nowt = 0
    #一週目
    def doOnce():
        nonlocal nowt,powerRemain
        isAccept = controller.next()
        nowt += 40
        if( isAccept):
            powerRemain = powerRemain + (controller.maxPower - requiredPower)*40
            if(powerRemain > maxStorage): powerRemain = maxStorage
        else:
            powerRemain = powerRemain - requiredPower * 40
            if(powerRemain < 0): powerRemain = 0

        t.append(nowt)
        v.append(powerRemain)
        return powerRemain > 0

    for i in range(period):
        if( not doOnce()):
            return BatterySimResult(time=t,value=v,isValid=False)
    #二周目
    for i in range(period):
        if( not doOnce()):
            return BatterySimResult(time=t,value=v,isValid=False)
    return BatterySimResult(time=t,value=v,isValid=True)

class FitPlan(BaseModel):
    needPower: int
    bitStr: str
    simResult: BatterySimResult

def searchFitPlan(requiredPower:int,storageMargin:int):
    controller = PowerControllerWuling()
    controller.fit(requiredPower=requiredPower)
    while True:
        simResult = simulate(requiredPower,controller)
        if(simResult.isValid):
            if(numpy.min(simResult.value) >= storageMargin):
                return FitPlan(needPower=controller.nowPower(),bitStr=controller.toBit(),simResult=simResult)
        controller.increasePower()
        if(controller.isMax()):
            return FitPlan(needPower=controller.nowPower(),bitStr=controller.toBit(),simResult=simResult)