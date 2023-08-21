
import openai,os

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

with open("openaichat/systemPrompt.txt","r",encoding="utf-8_sig") as f:
    SYSTEM_PROMPT = f.read()

#print(SYSTEM_PROMPT)

openai.api_key = OPENAI_API_KEY

def openaichat(msgList):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content" : SYSTEM_PROMPT},
        ] + msgList
    )
    return response.choices[0]["message"]["content"].strip()

def debug():
    testmsg = [{
        "role":"user",
        "content":"夏の大三角について教えて"
    }]
    print(openaichat(testmsg))

if(__name__ == "__main__"):
    debug()