from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import models
from database import engine
from routes import router

# Load environment variables from .env file
load_dotenv()

# Create DB tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Perplexity Trading System")

# Include API Router
app.include_router(router, prefix="/api")

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")
