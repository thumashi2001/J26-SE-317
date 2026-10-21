from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_mindmap_api():
    payload = {
        "analysis_request": {
            "question_id": "Q-MAP",
            "question_text": "What is AI?",
            "student_answer": "AI is artificial intelligence.",
            "expected_concepts": ["artificial intelligence", "machine learning"],
            "answer_type": "short"
        }
    }
    response = client.post("/mindmap/generate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["question_id"] == "Q-MAP"
    assert data["root_node_id"] == "root_q-map"
    assert len(data["nodes"]) == 3
    assert data["summary"]["total_nodes"] == 3
