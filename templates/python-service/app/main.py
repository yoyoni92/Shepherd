from fastapi import FastAPI

app = FastAPI(title="__NAME__")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "__NAME__"}
