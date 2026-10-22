from fastapi import FastAPI

app = FastAPI(title="I-adore-pdf", docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
