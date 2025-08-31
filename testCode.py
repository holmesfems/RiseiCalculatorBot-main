
import os
import re
import time
from pathlib import Path

CODE_FENCE_RE = re.compile(r"```(?:python|py)?\\s*(.*?)```", re.IGNORECASE | re.DOTALL)

def extract_code_blocks(response_text: str):
    blocks = CODE_FENCE_RE.findall(response_text)
    # 予備: インラインの3バッククォートだけのブロックも拾う
    if not blocks:
        blocks = re.findall(r"```\\s*(.*?)```", response_text, re.DOTALL)
    return [b.strip() for b in blocks if b.strip()]

def run_code_blocks(code_blocks, work_dir: str | None = None):
    # 作業用ディレクトリを準備（残す）
    if work_dir is None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        work_dir = os.path.abspath(f"code_run_{ts}")
    Path(work_dir).mkdir(parents=True, exist_ok=True)

    # 実行
    old_cwd = os.getcwd()
    try:
        os.chdir(work_dir)
        g = {"__name__": "__main__"}
        for block in code_blocks:
            exec(compile(block, "<extracted_block>", "exec"), g, g)
    finally:
        os.chdir(old_cwd)

    # 生成物の絶対パスを収集
    created = []
    for p in Path(work_dir).rglob("*"):
        if p.is_file():
            created.append(str(p.resolve()))
    return work_dir, created

def extract_and_run(response_text: str, work_dir: str | None = None, first_only: bool = False):
    """
    response_text: code_interpreterのレスポンス全文
    work_dir: 実行先（未 指定なら code_run_YYYYmmdd_HHMMSS を作成）
    first_only: 最初のコードブロックだけを実行するなら True
    戻り値: (work_dir, [生成ファイルの絶対パス])
    """
    blocks = extract_code_blocks(response_text)
    if not blocks:
        return (work_dir or os.getcwd(), [])
    if first_only:
        blocks = [blocks[0]]
    return run_code_blocks(blocks, work_dir)

# 使い方例
if __name__ == "__main__":
    sample = """
ここにCode Interpreterのレスポンス本文…
```python
with open("hello.txt", "w", encoding="utf-8") as f:
    f.write("Hello, Doctor!")
```
"""
    wd, files = extract_and_run(sample)
    print("work_dir:", wd)
    print("created_files:")
    for f in files:
        print(f)