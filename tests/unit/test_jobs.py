from quickapi import QuickAPI


def test_submit_job_returns_status_url():
    app = QuickAPI(job_workers=1)

    accepted = app.submit_job(lambda: {"ok": True}, name="demo")
    job_id = accepted["data"]["job_id"]
    response = app.handle("GET", f"/quick/jobs/{job_id}")

    assert accepted["status"] == 202
    assert response.status == 200
    assert response.to_dict()["data"]["id"] == job_id
    assert response.to_dict()["data"]["name"] == "demo"
    app.lifecycle.shutdown()


def test_job_not_found_response():
    app = QuickAPI()
    response = app.handle("GET", "/quick/jobs/missing")

    assert response.status == 404
    app.lifecycle.shutdown()
