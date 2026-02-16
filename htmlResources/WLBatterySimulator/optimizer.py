from pydantic import BaseModel
from typing import List, Tuple
from .batterySim import searchFitPlan
import numpy

class OptimizationResult(BaseModel):
    required_power: int
    setting_value: int
    time_series: List[int]          # 例: 分
    remaining_series: List[float]   # 例: 残電量(任意単位)
    tobit: str
    lowest_storage: int


def validate_required_power(x: int) -> None:
    if x < 5 or x > 1595 or (x % 5) != 0:
        raise ValueError("必要電力は 5〜1595 の 5刻み整数で入力してください。")


def optimize(required_power: int, storage_margin:int) -> OptimizationResult:
    validate_required_power(required_power)
    fitPlan = searchFitPlan(requiredPower=required_power,storageMargin=storage_margin)
    setting = fitPlan.needPower
    ts, rs = (fitPlan.simResult.time,fitPlan.simResult.value)
    return OptimizationResult(
        required_power=required_power,
        setting_value=setting,
        time_series=ts,
        remaining_series=rs,
        tobit = fitPlan.bitStr,
        lowest_storage=numpy.min(fitPlan.simResult.value)
    )