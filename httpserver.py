from recruitment import recruitment,recruitFromOCR
import os

from flask import Flask,request
import json

port = int(os.environ["PORT"])
print(f"Server port = {port}")

app = Flask(__name__)

@app.route('/recruitment/', methods=['POST'])
def doRecruitment():
    text= json.loads(request.data.decode("utf-8"))["text"]
    #text = request.args.get("text")
    #print(text)
    matchTag = recruitFromOCR.matchTag(text)
    if(matchTag.isEmpty()): return {"reply":"タグがありません","title":"エラー"}
    matches = matchTag.matches
    if(len(matches) > 8):
        matches = list(matches)[:8]

    reply = recruitment.recruitDoProcess(matches,4,matchTag.isGlobal)
    return {"reply":reply.responseForAI, "title":reply.embbedTitle}

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port)