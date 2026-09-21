"""FastAPI composition root: middleware, lifecycle, and modular controllers."""
import hmac
import os
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .api import migration, review, target
from .api.common import APIError
from .agent import Agent
from .store import Store
from .config import DATA_PATH, frontend_origins

def create_app(db_path=None, port=None):
    token = secrets.token_hex(32)
    store = Store(db_path or DATA_PATH)
    agent = Agent(store, port or int(os.environ.get('PORT', 8000)), token)
    @asynccontextmanager
    async def lifespan(app):
        agent.recover()
        yield
        agent.executor.shutdown(wait=True)
    app = FastAPI(title='Relay Migration API', version='2.0.0', lifespan=lifespan)
    app.state.store, app.state.agent, app.state.token = store, agent, token
    origins = frontend_origins()
    @app.middleware('http')
    async def protect(request: Request, call_next):
        origin = request.headers.get('origin')
        if origin and origin.rstrip('/') != str(request.base_url).rstrip('/') and origin not in origins:
            return JSONResponse(dict(error='This frontend origin is not allowed'), status_code=403)
        if request.url.path.startswith('/mock/') and not hmac.compare_digest(request.headers.get('x-internal-token', ''), token):
            return JSONResponse(dict(error='Internal mock API only'), status_code=403)
        try:
            size = int(request.headers.get('content-length', '0'))
        except ValueError:
            return JSONResponse(dict(error='Invalid content length'), status_code=400)
        if size > 26 * 1024 * 1024:
            return JSONResponse(dict(error='Request too large'), status_code=413)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response
    app.add_middleware(CORSMiddleware, allow_origins=list(origins), allow_methods=['GET', 'POST', 'OPTIONS'],
                       allow_headers=['Content-Type'], expose_headers=['Content-Disposition'])
    @app.exception_handler(APIError)
    async def api_error(request, exc):
        return JSONResponse(dict(error=str(exc)), status_code=exc.status)
    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return JSONResponse(dict(error=str(exc)), status_code=400)
    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(dict(error='Invalid request: ' + '; '.join(e['msg'] for e in exc.errors())), status_code=400)
    app.include_router(migration.router)
    app.include_router(review.router)
    app.include_router(target.router)
    return app
