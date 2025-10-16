from flask import Flask, request, jsonify
from llama_cpp import Llama

app = Flask(__name__)

llm = Llama(model_path="models/llama-2-7b-chat.Q2_K.gguf", n_ctx=4096, n_threads=8)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    prompt = data.get("message", "")

    response = llm(f"User: {prompt}\nAssistant:", max_tokens=256, temperature=0.7)
    text = response["choices"][0]["text"].strip()

    return jsonify({"reply": text})

if __name__ == "__main__":
    app.run(debug=True)
