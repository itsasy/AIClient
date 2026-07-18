from flask import Flask, request, jsonify
from core.orchestrator import Orchestrator
from core.standards_learner import StandardsLearner

app = Flask(__name__)
orchestrator = Orchestrator()
learner = StandardsLearner()


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.json
    query = data.get("query", "")
    response = orchestrator.process(query)
    return jsonify({"response": response})


@app.route("/api/learn", methods=["POST"])
def learn():
    data = request.json
    learner.learn(data.get("key"), data.get("value"))
    return jsonify({"status": "learned"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
