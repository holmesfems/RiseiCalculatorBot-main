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
    print(text)
    matchTag = recruitFromOCR.matchTag(text)
    if(matchTag.isEmpty()): return "タグがありません"
    reply = recruitment.recruitDoProcess(matchTag.matches,4,matchTag.isGlobal)
    return {"reply":reply.getEmbbedText(),"title":reply.embbedTitle}

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port)