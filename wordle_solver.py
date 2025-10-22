# wordle_solver.py
"""
Optimized Wordle solver with entropy-based strategy and parallel processing.

Dependencies:
    - wordfreq: pip install wordfreq
    - requests: pip install requests
    - beautifulsoup4: pip install beautifulsoup4
"""

import math
from collections import defaultdict
from wordfreq import zipf_frequency, top_n_list
from concurrent.futures import ProcessPoolExecutor
import os


# -----------------------------
# Dictionary and Pattern Functions
# -----------------------------

def build_dictionary(n_top=100000, filter_past_answers=True):
    """
    Build dictionary of 5-letter words from most common English words.
    
    Args:
        n_top: Number of top words to consider
        filter_past_answers: If True, automatically filters out known past Wordle answers
    """
    words = [w.lower() for w in top_n_list("en", n_top) if len(w) == 5 and w.isalpha()]
    word_set = sorted(set(words))
    
    if filter_past_answers:
        try:
            import requests
            from bs4 import BeautifulSoup
            import warnings
            
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")
            
            url = "https://www.rockpapershotgun.com/wordle-past-answers"
            response = requests.get(url, verify=False, timeout=5)
            soup = BeautifulSoup(response.text, "html.parser")
            
            selector = "ul.inline li"
            past_answers = [li.get_text(strip=True).lower() for li in soup.select(selector)]
            word_set = [w for w in word_set if w not in past_answers]
        except Exception as e:
            # If scraping fails, just return the full dictionary
            print(f"Warning: Could not filter past answers ({e}). Using full dictionary.")
    
    return word_set


def feedback_pattern(guess, target):
    """
    Generate Wordle feedback pattern.
    0 = gray (absent), 1 = yellow (wrong pos), 2 = green (correct pos)
    """
    pattern = [0] * 5
    target_chars = list(target)
    
    # Greens first
    for i, ch in enumerate(guess):
        if target[i] == ch:
            pattern[i] = 2
            target_chars[i] = None
    
    # Yellows
    for i, ch in enumerate(guess):
        if pattern[i] == 0 and ch in target_chars:
            pattern[i] = 1
            target_chars[target_chars.index(ch)] = None
    
    return tuple(pattern)


def filter_candidates(candidates, guess, pattern):
    """Filter candidates based on feedback pattern."""
    return [w for w in candidates if feedback_pattern(guess, w) == pattern]


def is_consistent(word, history):
    """Check if word is consistent with entire guess history."""
    for guess, pattern in history:
        if feedback_pattern(guess, word) != pattern:
            return False
    return True


# -----------------------------
# Entropy and Scoring
# -----------------------------

def expected_entropy(guess, candidates):
    """Calculate expected information gain (entropy) for a guess."""
    partitions = defaultdict(int)
    for target in candidates:
        p = feedback_pattern(guess, target)
        partitions[p] += 1
    
    total = len(candidates)
    entropy = 0.0
    for count in partitions.values():
        prob = count / total
        entropy -= prob * math.log2(prob)
    
    return entropy


def hybrid_score(guess, candidates, alpha=0.7):
    """
    Hybrid scoring: alpha * entropy + (1-alpha) * frequency.
    
    Args:
        guess: Word to score
        candidates: Current possible answers
        alpha: Weight for entropy vs frequency (0-1, higher = more entropy)
    """
    ent = expected_entropy(guess, candidates)
    freq = zipf_frequency(guess, "en")
    freq_clamped = max(min(freq, 7.0), 1.0)
    freq_norm = (freq_clamped - 1.0) / 6.0
    return alpha * ent + (1.0 - alpha) * freq_norm


# -----------------------------
# Parallel Processing Helper (must be module-level for pickling)
# -----------------------------

def _score_word_worker(args):
    """Worker function for parallel scoring (must be top-level for multiprocessing)."""
    word, candidates, alpha = args
    score = hybrid_score(word, candidates, alpha)
    return (score, word)


# -----------------------------
# Stateful Solver Class
# -----------------------------

class WordleSolver:
    """Stateful Wordle solver with clean API."""
    
    def __init__(self, n_top=100000, filter_past_answers=True):
        """Initialize solver with dictionary."""
        # Always keep full dictionary for unrestricted guessing
        self.all_words = build_dictionary(n_top, filter_past_answers=False)
        
        # Filter candidates if requested
        if filter_past_answers:
            self.candidates = build_dictionary(n_top, filter_past_answers=True)
        else:
            self.candidates = self.all_words[:]
        
        self.history = []

    def suggest_initial_guess(self, alpha=0.7, topk=5, restrict_guesses=True):
        """
        Suggest initial guess based on entropy and frequency.
        
        Args:
            alpha: Weight for entropy vs frequency (0-1)
            topk: Number of suggestions to return
            restrict_guesses: If True, only suggest from candidates; if False, use full dictionary
        """
        # Get initial suggestions
        suggestions = suggest_guesses(self.candidates, self.all_words, 
                                       alpha=alpha, topk=topk, restrict_guesses=restrict_guesses)
        print(f"Initial suggestions: {suggestions}")
        return suggestions

    def guess(self, word, pattern, alpha=0.7, topk=5, restrict_guesses=False):
        """
        Process a guess and get next suggestions.
        
        Args:
            word: The word that was guessed
            pattern: Feedback pattern tuple, e.g., (0,1,2,0,1)
            alpha: Weight for entropy vs frequency (0-1)
            topk: Number of suggestions to show
            restrict_guesses: If True, only suggest from candidates; if False, use full dictionary
        
        Returns:
            List of suggested next guesses
        """
        # Update history
        self.history.append((word, pattern))
        
        # Filter candidates
        self.candidates = filter_candidates(self.candidates, word, pattern)
        
        # Print status
        print(f"\nGuess: '{word}' → Pattern: {pattern}")
        print(f"Candidates remaining: {len(self.candidates)}")
        
        # Get suggestions
        if len(self.candidates) == 0:
            print("❌ No candidates remain! Check your pattern.")
            return []
        elif len(self.candidates) == 1:
            print(f"✅ Answer found: '{self.candidates[0]}'")
            return self.candidates
        else:
            suggestions = suggest_guesses(self.candidates, self.all_words, 
                                         alpha, topk, restrict_guesses)
            print(f"Next suggestions: {suggestions}")
            return suggestions
    
    def reset(self):
        """Reset solver to initial state."""
        self.candidates = self.all_words[:]
        self.history = []
        print("Solver reset!")


# -----------------------------
# Main Suggestion Function
# -----------------------------

def suggest_guesses(candidates, all_words, alpha=0.7, topk=5, restrict_guesses=True, max_workers=None):
    """
    Suggest best guesses using parallel processing for large guess pools.
    
    Args:
        candidates: Current possible answers
        all_words: Full dictionary for exploration
        alpha: Weight for entropy vs frequency (0-1, higher = more entropy weight)
        topk: Number of suggestions to return
        restrict_guesses: If True, only suggest from candidates; if False, use all_words
        max_workers: Number of parallel processes (None = CPU count)
    
    Note: Automatically uses parallel processing for large pools (>500 words).
          Falls back to serial for small pools to avoid process overhead.
    """
    if restrict_guesses:
        guess_pool = candidates
    else:
        guess_pool = all_words

    # For small pools, parallel overhead isn't worth it - use serial
    if len(guess_pool) < 500:
        scores = []
        for w in guess_pool:
            s = hybrid_score(w, candidates, alpha)
            scores.append((s, w))
        scores.sort(reverse=True)
        return [w for _, w in scores[:topk]]
    
    # For large pools, use parallel processing
    args = [(w, candidates, alpha) for w in guess_pool]
    
    if max_workers is None:
        max_workers = os.cpu_count()
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        scores = list(executor.map(_score_word_worker, args))
    
    scores.sort(reverse=True)
    return [w for _, w in scores[:topk]]
