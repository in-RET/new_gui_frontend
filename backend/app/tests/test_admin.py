from starlette.testclient import TestClient

from backend.app.main import app


client = TestClient(app)

def test_admin_root():
    response = client.get("/admin")
    assert response.status_code == 418
    assert response.json() == {"detail": "I'm a teapot."}
