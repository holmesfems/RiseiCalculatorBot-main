import datetime

t_delta = datetime.timedelta(hours=9)  # 9時間
JST = datetime.timezone(t_delta, 'JST')  # UTCから9時間差の「JST」タイムゾーン
def getnow():
    return datetime.datetime.now(tz=JST)
