from dotenv import load_dotenv
load_dotenv()
import os, anthropic

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
r = client.messages.create(
    model='claude-haiku-4-5-20251001',
    max_tokens=500,
    system='You are a maths teacher. Return only JSON: {"steps":[{"type":"intro","label":"test","speak":"test reply","display":"test"}]}',
    messages=[{'role':'user','content':'10x+x=8'}]
)
print(r.content[0].text)