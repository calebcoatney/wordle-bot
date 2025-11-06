# Wordle Solver API

A FastAPI-based REST API for an intelligent Wordle solver using entropy-based strategy.

## Installation

```bash
pip install -r requirements.txt
```

## Running the API

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### `POST /init`
Initialize a new solver session.

**Request Body:**
```json
{
  "n_top": 100000,
  "filter_past_answers": true,
  "alpha": 0.7,
  "topk": 5,
  "restrict_guesses": true
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "suggestions": ["soare", "roate", "raise", "arise", "irate"],
  "total_candidates": 5234
}
```

### `POST /guess`
Submit a guess and get next suggestions.

**Request Body:**
```json
{
  "session_id": "uuid-string",
  "word": "soare",
  "pattern": [0, 1, 2, 0, 1],
  "alpha": 0.7,
  "topk": 5,
  "restrict_guesses": false
}
```

**Pattern Values:**
- `0` = Gray (letter not in word)
- `1` = Yellow (letter in word, wrong position)
- `2` = Green (letter in correct position)

**Response:**
```json
{
  "suggestions": ["plunk", "trunk", "drunk"],
  "candidates_remaining": 12,
  "is_solved": false,
  "message": null
}
```

### `GET /session/{session_id}`
Get information about an existing session.

**Response:**
```json
{
  "session_id": "uuid-string",
  "candidates_remaining": 42,
  "guesses_made": 2
}
```

### `POST /reset`
Reset a session to initial state.

**Request Body:**
```json
{
  "session_id": "uuid-string"
}
```

**Response:**
```json
{
  "message": "Session reset successfully"
}
```

### `DELETE /session/{session_id}`
Delete a session.

**Response:**
```json
{
  "message": "Session deleted successfully"
}
```

### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "active_sessions": 3
}
```

## Usage Example with cURL

### 1. Initialize a session
```bash
curl -X POST "http://localhost:8000/init" \
  -H "Content-Type: application/json" \
  -d '{
    "alpha": 0.7,
    "topk": 5,
    "restrict_guesses": true
  }'
```

### 2. Submit a guess
```bash
curl -X POST "http://localhost:8000/guess" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id-here",
    "word": "soare",
    "pattern": [0, 1, 2, 0, 1]
  }'
```

## Usage Example with Python

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000"

# Initialize session
response = requests.post(f"{BASE_URL}/init", json={
    "alpha": 0.7,
    "topk": 5,
    "restrict_guesses": True
})
data = response.json()
session_id = data["session_id"]
print(f"Initial suggestions: {data['suggestions']}")

# Submit first guess
# Pattern example: [0,1,2,0,1] means gray, yellow, green, gray, yellow
response = requests.post(f"{BASE_URL}/guess", json={
    "session_id": session_id,
    "word": "soare",
    "pattern": [0, 1, 2, 0, 1],
    "alpha": 0.7,
    "topk": 5
})
data = response.json()
print(f"Next suggestions: {data['suggestions']}")
print(f"Candidates remaining: {data['candidates_remaining']}")

# Continue guessing until solved
while not data["is_solved"]:
    next_word = data["suggestions"][0]  # Use first suggestion
    # Get pattern from actual Wordle game
    pattern = [0, 1, 2, 0, 1]  # Replace with actual pattern
    
    response = requests.post(f"{BASE_URL}/guess", json={
        "session_id": session_id,
        "word": next_word,
        "pattern": pattern
    })
    data = response.json()
    print(f"Suggestions: {data['suggestions']}")
    
    if data["is_solved"]:
        print(f"Solved: {data['message']}")
        break
```

## Parameters Explained

### `alpha` (0.0 - 1.0)
Weight for entropy vs word frequency:
- Higher values (e.g., 0.9): Prioritize information gain (better for hard mode)
- Lower values (e.g., 0.3): Prioritize common words (more human-like)
- Default: 0.7 (balanced)

### `restrict_guesses`
- `true`: Only suggest from remaining possible answers
- `false`: Can suggest any word for maximum information gain

### `filter_past_answers`
- `true`: Removes known past Wordle answers from candidates
- `false`: Includes all words

## CORS

CORS is enabled for all origins. In production, configure this appropriately in `main.py`.

## License

MIT
