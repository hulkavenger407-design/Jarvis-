from fastapi import FastAPI

app = FastAPI(title="Chhaya API", description="Chhaya Agent Factory API")

@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "Chhaya API is running"}
