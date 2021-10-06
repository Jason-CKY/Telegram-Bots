from typing import Optional
import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {
        "Hello": "World"
        }

@app.get("/modbot")
def read_root():
    return {
        "Hello": "World",
        "Ngrok url": os.getenv('PUBLIC_URL')
        }
