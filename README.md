# Procedural Story Generation with Storylets and LLM Support

This repository contains the source code for a procedural storytelling system that combines a rule-based storylet architecture with adaptive narrative selection mechanisms and optional Large Language Model (LLM) support.

The main narrative structure and game state are controlled by deterministic rules, while the LLM is used primarily for narrative paraphrasing and, in limited cases, for validated AI-generated micro-choices.

## Project Structure

- `main_tk.py`  
  Main application and graphical user interface implemented with Tkinter.

- `game_logic.py`  
  Core narrative engine. Handles player state, requirements, effects, adaptive choice ordering, novelty, cooldowns, loop avoidance, arc nudging and transition reinforcement.

- `enhanced_passages.py`  
  Definition of the story world, storylets, narrative passages, choices, requirements and effects.

- `llm.py`  
  Optional LLM integration for narrative paraphrasing and controlled AI-generated micro-choices.

- `simulate.py`  
  Automated simulation using a top-2 choice strategy (500 runs).

- `sim2.py`  
  Comparison between a guided top-1 strategy and an exploratory top-3 strategy (5000 runs per strategy).

- `ablation.py`  
  Ablation study used to evaluate the contribution of individual narrative-selection mechanisms (5000 runs per variant by default).

- `requirements.txt`  
  Python dependency required for optional LLM functionality.

## Requirements

- Python 3
- Tkinter
- `openai` Python package for optional LLM functionality

Install the required Python package with:

```bash
pip install -r requirements.txt
```

Tkinter is normally included with standard Python installations on Windows.

## Running the Application

Run:

```bash
python main_tk.py
```

If `python` is not available as a command, try:

```bash
python3 main_tk.py
```

The application can run without an API key. In this case, the rule-based narrative engine remains functional and the original narrative text is used when LLM functionality is unavailable.

## Optional LLM Support

LLM functionality is optional.

The API key is **not stored in the source code**. It must be provided through an environment variable.

For OpenRouter:

```text
OPENROUTER_API_KEY
```

Alternatively:

```text
OPENAI_API_KEY
```

The default API endpoint configured in `llm.py` is compatible with OpenRouter.

When no valid API key is available, the application falls back to the original narrative text.

AI-generated micro-choices are constrained by predefined allowed destination states and validated effects before being accepted by the narrative engine.

## Narrative Selection Mechanisms

The narrative engine includes several mechanisms intended to balance progression, exploration and narrative variety:

- novelty-based scoring
- recent-state loop avoidance
- choice cooldowns
- state cooldowns
- cluster-switching bonus
- quest arc nudging
- soft transition reinforcement

These mechanisms modify the ranking or weighting of available choices while the underlying story world, requirements and effects remain explicitly defined by the rule-based system.

## Evaluation

Three evaluation scripts are included.

### Basic Simulation

```bash
python simulate.py
```

Runs 500 automated playthroughs using a top-2 strategy.

### Guided vs Exploratory Strategies

```bash
python sim2.py
```

Runs 5000 simulations for each of two strategies:

- Guided player: top-1 choice
- Exploratory player: random selection among the top-3 choices

### Ablation Study

```bash
python ablation.py
```

By default, the ablation study runs 5000 simulations for each variant.

Individual mechanisms are disabled one at a time to examine their effect on metrics including:

- quest completion rate
- average completion turn
- number of distinct narrative paths
- A-B-A ("ping-pong") loops
- average number of distinct states visited

A faster test can be executed with:

```bash
python ablation.py --runs 50
```

Other examples:

```bash
python ablation.py --runs 1000
python ablation.py --topk 1
python ablation.py --csv results.csv
```

The evaluation scripts disable LLM/API functionality in order to evaluate the underlying narrative-selection algorithm independently and improve reproducibility.

## Reproducibility

The simulation scripts use deterministic random seeds where applicable.

The evaluation therefore focuses on the rule-based narrative engine and its adaptive selection mechanisms rather than on stochastic variation introduced by external language models.

Generated JSON/CSV result files can be excluded from version control and reproduced by running the corresponding evaluation scripts.

## Security

No API keys or credentials are included in this repository.

API credentials should only be supplied locally through environment variables and should never be committed to the repository.
