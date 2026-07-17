from flask import Flask, request, jsonify
from core.orchestrator import Orchestrator

app = Flask(__name__)
orchestrator = Orchestrator()


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.json
    query = data.get("query", "")
    response = orchestrator.process(query)
    return jsonify({"response": response, "status": "success"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
