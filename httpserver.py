from recruitment import recruitment,recruitFromOCR
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class OCRRawData(BaseModel):
    text: str

@app.post('/recruitment/')
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