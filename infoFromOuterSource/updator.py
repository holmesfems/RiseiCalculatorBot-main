import inspect
import infoFromOuterSource.idtoname

def initall():
    initList = [member for name,member in inspect.getmembers(infoFromOuterSource.idtoname) if inspect.isclass(member)]
    for item in initList:
        try:
            item.init()
        except Exception as e:
            print(e)