
import openai

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

with open("openaichat/systemPrompt.txt","r",encoding="utf-8_sig") as f:
    SYSTEM_PROMPT = f.read()

#print(SYSTEM_PROMPT)

openai.api_key = OPENAI_API_KEY

def openaichat(msgList):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content" : SYSTEM_PROMPT},
        ] + msgList
    )
    return response.choices[0]["message"]["content"].strip()
