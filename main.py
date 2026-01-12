from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from routers import admin, student
from database import connect_db
import uvicorn

app = FastAPI()

app.mount("/static", StaticFiles(directory="templates"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(student.router, prefix="/student", tags=["student"])

# Connect to DB
connect_db()

# Custom error handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("error.html", {"request": request, "detail": exc.detail}, status_code=exc.status_code)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "landing.html",
        {"request": request}
    )

@app.get("/get-started", response_class=HTMLResponse)
async def get_started(request: Request):
    return templates.TemplateResponse(
        "get_started.html",
        {"request": request}
    )

@app.get("/api/status")
async def api_status():
    return {"status": "online", "app": "QuizMaster", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)