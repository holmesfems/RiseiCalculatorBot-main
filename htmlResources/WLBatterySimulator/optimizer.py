from pydantic import BaseModel
from typing import List, Tuple
from .batterySim import searchFitPlanForAllClock,searchFitPlanForOneClock,searchPlanForClockCircuit
import re,numpy

class OptimizationResult(BaseModel):
    required_power: int
    setting_value: float
    time_series: List[int]          # 例: 分
    remaining_series: List[float]   # 例: 残電量(任意単位)
    tobit: str
    lowest_storage: int
    use_margin_under_5: bool
    save_battery: float
    clock:str|None


def validate_required_power(x: int, blueprintId: str) -> None:
    if (blueprintId in ["CTL_1", "CTL_2", "CTL_3"]):
        if x < 5 or x > 1595 or (x % 5) != 0:
            raise ValueError("必要電力は 5〜1595 の 5刻み整数で入力してください。")
    elif (blueprintId in ["CTL_4"]):
        if x < 5 or x > 3195 or (x % 5) != 0:
            raise ValueError("必要電力は 5〜3195 の 5刻み整数で入力してください。")
    else:
        raise ValueError("存在しない図面です")

def separateClock(clock:int):
    base = [32,16,8,4,2]
    res = []
    remain = clock-40
    if(remain <= 0): return res
    for value in base:
        if(remain >= value):
            res.append(value)
            remain -= value
            if(remain == 0): return res
    return res

def optimize(required_power: int, storage_margin:int, use_margin_under_5:bool,blueprintId:str) -> OptimizationResult:
    validate_required_power(required_power, blueprintId)
    mergerLeft = '<img src="/WLBatterySimulator/static/merger.png"/>'
    mergerRight = '<img src="/WLBatterySimulator/static/merger.png" style="transform: rotate(180deg);"/>'

    if(blueprintId == "CTL_1"):
        #PMW回路
        fitPlan = searchFitPlanForOneClock(requiredPower=required_power,storageMargin=storage_margin,useMarginUnder5=use_margin_under_5,clock=40)
        fitClock = None
        merger = mergerLeft
    elif(blueprintId == "CTL_2"):
        #周期→PMW回路
        fitPlan = searchFitPlanForAllClock(requiredPower=required_power,storageMargin=storage_margin,useMarginUnder5=use_margin_under_5)
        sc = separateClock(fitPlan.clock)
        fitClock = f"{fitPlan.clock}s"
        merger = mergerLeft
        if(sc):
            sc.reverse()
            fitClock += " ("
            fitClock += " ".join([f"+{item}" for item in sc])
            fitClock += ")"
    elif(blueprintId == "CTL_3"):
        #周期回路(武陵小電池)
        fitPlan = searchPlanForClockCircuit(requiredPower=required_power,
                                            storageMargin=storage_margin,
                                            batteryPower=1600)
        fitClock = f"{fitPlan.clock}"
        merger = mergerRight
    
    elif(blueprintId == "CTL_4"):
        #周期回路(武陵中電池)
        fitPlan = searchPlanForClockCircuit(requiredPower=required_power,
                                            storageMargin=storage_margin,
                                            batteryPower=3200)
        fitClock = f"{fitPlan.clock}"
        merger = mergerRight

    else: raise Exception("Unknown blueprintId")
    setting = fitPlan.needPower
    ts, rs = (fitPlan.simResult.time,fitPlan.simResult.value)
    save_battery = 1.5*60*24*(1 - fitPlan.needPower/fitPlan.maxPower)
    return OptimizationResult(
        required_power=required_power,
        setting_value=setting,
        time_series=ts,
        remaining_series=rs,
        tobit = re.sub(
            r'[01]',
            lambda m: merger if m.group(0) == '0' else '<img src="/WLBatterySimulator/static/crosser.png"/>',
            fitPlan.bitStr
        ),
        lowest_storage=numpy.min(fitPlan.simResult.value),
        use_margin_under_5 = use_margin_under_5,
        save_battery=save_battery,
        clock=fitClock
    )