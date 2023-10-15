def has_duplicates(l:list)->bool:
    temp = set()
    for item in l:
        if item in temp: return True
        temp.add(item)
    return False