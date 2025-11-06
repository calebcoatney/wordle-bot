# Wordle Solver - Frontend Guide

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the server:**
   ```bash
   uvicorn main:app --reload
   ```

3. **Open your browser:**
   Navigate to `http://localhost:8000`

## Using the Web Interface

### Step 1: Initialize Solver
- **Dictionary Size**: Number of words to consider (default: 100,000)
- **Alpha**: Weight for entropy vs frequency (0-1)
  - Higher (0.9): Prioritize information gain
  - Lower (0.3): Prioritize common words
  - Default: 0.7 (balanced)
- **Number of Suggestions**: How many word suggestions to show
- **Filter Past Answers**: Remove known past Wordle answers
- **Restrict to Remaining Candidates**: Only suggest from possible answers

Click "Initialize Solver" to get your first suggestions.

### Step 2: Enter Guesses

For each guess:

1. **Enter the word** you guessed (5 letters)
2. **Select the feedback pattern** using the dropdowns:
   - ⬜ Gray (0): Letter not in word
   - 🟨 Yellow (1): Letter in word, wrong position
   - 🟩 Green (2): Letter in correct position
3. **Adjust parameters** (optional):
   - **Alpha**: Change strategy for next guess
   - **Top K**: Number of suggestions to show
   - **Restrict**: Only suggest from remaining candidates
4. Click "Submit Guess"

The app will show:
- Visual history of your guesses with colored tiles
- Number of remaining candidates
- Suggested next guesses
- Success message when solved

### Example Workflow

1. Initialize solver → Get suggestions: ["soare", "roate", "raise", "arise", "irate"]
2. Guess "soare" → Enter pattern [0, 1, 2, 0, 1]
3. Get new suggestions based on feedback
4. Repeat until solved!

## Tips

- Start with **alpha=0.7** for balanced approach
- Use **alpha=0.9-1.0** for maximum information gain
- Enable "Restrict" when only a few candidates remain
- The solver tracks your entire guess history
- Use "Reset Solver" to start a new game

## API Access

The API is also available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- API Info: `http://localhost:8000/api`

See `API_README.md` for detailed API documentation.
