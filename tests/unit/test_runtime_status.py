from quickapi import QuickAPI


def test_runtime_status_builtin_endpoint():
    app = QuickAPI("Runtime API", ml=True, secure=True, job_workers=2)
    response = app.handle("GET", "/quick/runtime")
    data = response.to_dict()["data"]

    assert response.status == 200
    assert data["name"] == "Runtime API"
    assert data["python"]["ml"] is True
    assert data["python"]["secure"] is True
    assert data["python"]["job_workers"] == 2
    assert data["features"]["streaming_files"] is True
    assert data["features"]["job_queue"] is True
    assert data["features"]["ml_engine"] is True
    assert data["native"]["native"] is False
