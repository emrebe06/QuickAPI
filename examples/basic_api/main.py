from quickapi import QuickAPI, q

app = QuickAPI("Basic API", docs=True)


@app.get("/ping")
def ping():
    return q.ok({"pong": True})


@app.post("/echo")
def echo(body):
    return q.ok(body)


if __name__ == "__main__":
    app.run()
