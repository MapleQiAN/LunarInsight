"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import upload, ingest, graph, settings
from infra.neo4j_client import neo4j_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: Initialize Neo4j connection
    try:
        neo4j_client.initialize()
        print("✅ Neo4j client initialized successfully")
    except Exception as e:
        print(f"⚠️  Warning: Failed to initialize Neo4j client: {e}")
        print("   The API will start but database operations will fail.")
    
    yield
    
    # Shutdown: Close connections
    if neo4j_client.driver:
        neo4j_client.close()
        print("✅ Neo4j client closed")


app = FastAPI(
    title="LunarInsight API",
    description="Personal Knowledge Graph System",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)
app.include_router(ingest.router)
app.include_router(graph.router)
app.include_router(settings.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "LunarInsight API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

