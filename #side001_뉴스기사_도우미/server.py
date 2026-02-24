from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests

app = Flask(__name__)
CORS(app)

# 🔴 여기에 OpenAI API 키 입력
OPENAI_API_KEY = ""

@app.route("/paraphrase", methods=["POST"])
def paraphrase():
    data = request.json
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "no text"}), 400

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4.1-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "너는 시사 전문가이고, 지금부터 주어지는 뉴스 기사를 중학생이 이해할 수 있을 정도로 풀어서 설명해야 된다."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            "temperature": 0
        }
    )

    result = response.json()
    output = result["choices"][0]["message"]["content"]
    return jsonify({"output": output})

if __name__ == "__main__":
    app.run(port=8000)
