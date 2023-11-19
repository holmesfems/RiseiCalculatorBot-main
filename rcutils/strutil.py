from typing import Dict

# 置換ルールを辞書に沿って行うメソッドを定義する
def replace_byDict(input_string:str, replacement_dictionary:Dict[str,str])->str:
    for key, value in replacement_dictionary.items():
        input_string = input_string.replace(key, value)
    return input_string