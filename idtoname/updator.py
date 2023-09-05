import inspect
import idtoname.idtoname

def initall():
    initList = [member for name,member in inspect.getmembers(idtoname.idtoname) if inspect.isclass(member)]
    for item in initList:
        try:
            item.init()
        except Exception as e:
            print(e)