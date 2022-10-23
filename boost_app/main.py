from fastapi import FastAPI

from boost_app.handlers import wallets

app = FastAPI()

app.include_router(wallets.router)


@app.get("/")
def get_root() -> dict:
    return {"message": "Welcome to Boost!"}
