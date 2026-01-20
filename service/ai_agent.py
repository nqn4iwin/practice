from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI  # openai==1.52.2

app = FastAPI()

client = OpenAI(
    api_key="",
    base_url="https://api.upstage.ai/v1"
)

class TextRequest(BaseModel):
    text: str

@app.post("/summary")
def summary(req: TextRequest):
    prompt = f"""{req.text}"""

    response = client.chat.completions.create(
        model="solar-pro2",
        messages=[{"role": "user", "content": prompt}],
    )

    summary_text = response.choices[0].message.content.strip()

    return {"summary": summary_text}
