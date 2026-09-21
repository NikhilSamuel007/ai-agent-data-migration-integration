"""Run one FastAPI process. Agent jobs are supervised background workers."""
import os
import uvicorn
from relay.web import create_app

if __name__ == '__main__':
    uvicorn.run(create_app(), host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', 8000)))
