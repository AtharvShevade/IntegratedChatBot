import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, query, voice

# Attach a handler directly so logs always appear in the uvicorn terminal
# regardless of whether uvicorn already configured the root logger.
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(levelname)s  [%(name)s]  %(message)s"))
for _name in ("query", "voice"):
    _lg = logging.getLogger(_name)
    _lg.setLevel(logging.INFO)
    if not _lg.handlers:
        _lg.addHandler(_handler)
    _lg.propagate = False


app = FastAPI(
    title="SQL Query Generator API",
    description="Natural language → SQL pipeline with Oracle DB execution",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(voice.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["api", "src"],   # only watch api/ and src/ — not test.py or output/
    )
