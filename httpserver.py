from recruitment import recruitment,recruitFromOCR
from fastapi import FastAPI
from pydantic import BaseModel,Field

description = """
現在開放中の機能は以下の通り:
- 公開求人検索(recruitment)
"""

app = FastAPI(
    title="F鯖アステシアちゃんbot 外部API",
    description=description,
    summary="F鯖アステシアちゃんbotの外部用API。",
    version="0.0.1",
    contact={
        "name": "ふぉめ holmesfems",
        "url": "https://youtube.com/@holmesfems",
        "email": "holmesfems@gmail.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/license/mit",
    },
)

class OCRRawData(BaseModel):
    text: str = Field(description="The raw data of OCR result. Each tag should be separated by line breaks")

class TagReplyData(BaseModel):
    title: str = Field(description="The recognized tags")
    reply: str = Field(description="The result to be displayed on screen")

@app.post('/recruitment/',response_model=TagReplyData,description="Extract tags of arknights public recruitment from raw OCR data, and calculate high-rare tag combination")
def doRecruitment(data:OCRRawData):
    text= data.text
    matchTag = recruitFromOCR.matchTag(text)
    if(matchTag.isEmpty()): return {"reply":"タグがありません","title":"エラー"}
    matches = matchTag.matches
    if(len(matches) > 8):
        matches = list(matches)[:8]
    reply = recruitment.recruitDoProcess(matches,4,matchTag.isGlobal)
    return {"reply":reply.responseForAI, "title":reply.embbedTitle}

print("Server started")