from quickapi import QuickAPI

app = QuickAPI("Native API")

# Build the native example first, then point this at the generated library.
app.native_post("/run/analyze", library="./native_score.dll", symbol="analyze_run")


if __name__ == "__main__":
    app.run()
