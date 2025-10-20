import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

def add_common_middleware(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_timing_header(request: Request, call_next):
        start = time.time()
        try:
            response = await call_next(request)
        except Exception as e:
            return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})
        finally:
            duration = int((time.time() - start) * 1000)
            request.state.processing_ms = duration
        response.headers["X-Processing-Time-ms"] = str(int((time.time() - start) * 1000))
        return response
