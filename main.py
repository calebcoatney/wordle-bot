# main.py
"""
FastAPI application for Wordle Solver.

Run with: uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Tuple, Optional
from wordle_solver import WordleSolver
import uuid
import os

app = FastAPI(
    title="Wordle Solver API",
    description="An intelligent Wordle solver using entropy-based strategy",
    version="1.0.0"
)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active solver sessions
sessions = {}


# -----------------------------
# Request/Response Models
# -----------------------------

class InitRequest(BaseModel):
    n_top: int = Field(default=100000, description="Number of top words to consider")
    filter_past_answers: bool = Field(default=True, description="Filter out known past Wordle answers")
    alpha: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight for entropy vs frequency (0-1)")
    topk: int = Field(default=5, ge=1, description="Number of suggestions to return")
    restrict_guesses: bool = Field(default=True, description="Only suggest from remaining candidates")


class InitResponse(BaseModel):
    session_id: str
    suggestions: List[str]
    total_candidates: int


class GuessRequest(BaseModel):
    session_id: str
    word: str = Field(min_length=5, max_length=5, description="5-letter word that was guessed")
    pattern: Tuple[int, int, int, int, int] = Field(
        description="Feedback pattern: 0=gray, 1=yellow, 2=green"
    )
    alpha: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight for entropy vs frequency")
    topk: int = Field(default=5, ge=1, description="Number of suggestions to return")
    restrict_guesses: bool = Field(default=False, description="Only suggest from remaining candidates")


class GuessResponse(BaseModel):
    suggestions: List[str]
    candidates_remaining: int
    is_solved: bool
    message: Optional[str] = None


class ResetRequest(BaseModel):
    session_id: str


class SessionInfo(BaseModel):
    session_id: str
    candidates_remaining: int
    guesses_made: int


# -----------------------------
# API Endpoints
# -----------------------------

@app.get("/")
def root():
    """Serve the frontend HTML."""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {
        "name": "Wordle Solver API",
        "version": "1.0.0",
        "endpoints": {
            "POST /init": "Initialize a new solver session",
            "POST /guess": "Submit a guess and get next suggestions",
            "POST /reset": "Reset an existing session",
            "GET /session/{session_id}": "Get session information",
            "DELETE /session/{session_id}": "Delete a session"
        }
    }


@app.get("/api")
def api_info():
    """Root endpoint with API information."""
    return {
        "name": "Wordle Solver API",
        "version": "1.0.0",
        "endpoints": {
            "POST /init": "Initialize a new solver session",
            "POST /guess": "Submit a guess and get next suggestions",
            "POST /reset": "Reset an existing session",
            "GET /session/{session_id}": "Get session information",
            "DELETE /session/{session_id}": "Delete a session"
        }
    }


@app.post("/init", response_model=InitResponse)
def initialize_solver(request: InitRequest):
    """
    Initialize a new Wordle solver session.
    
    Returns a session_id and initial suggestions.
    """
    try:
        # Create new solver
        solver = WordleSolver(
            n_top=request.n_top,
            filter_past_answers=request.filter_past_answers
        )
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Get initial suggestions
        suggestions = solver.suggest_initial_guess(
            alpha=request.alpha,
            topk=request.topk,
            restrict_guesses=request.restrict_guesses
        )
        
        # Store session
        sessions[session_id] = solver
        
        return InitResponse(
            session_id=session_id,
            suggestions=suggestions,
            total_candidates=len(solver.candidates)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize solver: {str(e)}")


@app.post("/guess", response_model=GuessResponse)
def submit_guess(request: GuessRequest):
    """
    Submit a guess and receive next suggestions.
    
    Pattern format: tuple of 5 integers
    - 0 = gray (letter not in word)
    - 1 = yellow (letter in word, wrong position)
    - 2 = green (letter in correct position)
    
    Example: (0, 1, 2, 0, 1) means:
    - Position 0: gray
    - Position 1: yellow
    - Position 2: green
    - Position 3: gray
    - Position 4: yellow
    """
    # Validate session
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate word
    word = request.word.lower()
    if not word.isalpha() or len(word) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters")
    
    # Validate pattern
    if not all(p in [0, 1, 2] for p in request.pattern):
        raise HTTPException(status_code=400, detail="Pattern must contain only 0, 1, or 2")
    
    try:
        solver = sessions[request.session_id]
        
        # Process guess
        suggestions = solver.guess(
            word=word,
            pattern=request.pattern,
            alpha=request.alpha,
            topk=request.topk,
            restrict_guesses=request.restrict_guesses
        )
        
        # Check if solved
        is_solved = len(solver.candidates) == 1
        message = None
        
        if len(solver.candidates) == 0:
            message = "No candidates remain - check your pattern"
        elif is_solved:
            message = f"Solved! Answer is '{solver.candidates[0]}'"
        
        return GuessResponse(
            suggestions=suggestions,
            candidates_remaining=len(solver.candidates),
            is_solved=is_solved,
            message=message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process guess: {str(e)}")


@app.post("/reset")
def reset_session(request: ResetRequest):
    """Reset an existing solver session to initial state."""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        sessions[request.session_id].reset()
        return {"message": "Session reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset session: {str(e)}")


@app.get("/session/{session_id}", response_model=SessionInfo)
def get_session_info(session_id: str):
    """Get information about an existing session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    solver = sessions[session_id]
    return SessionInfo(
        session_id=session_id,
        candidates_remaining=len(solver.candidates),
        guesses_made=len(solver.history)
    )


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    """Delete a solver session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions[session_id]
    return {"message": "Session deleted successfully"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len(sessions)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="100.77.149.126", port=8000)
