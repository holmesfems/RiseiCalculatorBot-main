def has_duplicates(l:list)->bool:
    temp = []
    for item in l:
        if item in temp: return True
        temp.append(item)
    return False