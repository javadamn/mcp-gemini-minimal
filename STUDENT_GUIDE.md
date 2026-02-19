# BioE234 MCP Starter — Student Guide

Welcome! This document explains how the BioE234 MCP Starter works and how you can extend it for your final project.

This guide assumes some students may be new to coding and will walk you through everything step-by-step.

---

# 1. What is this starter?

This repository is a framework for building **bioengineering automation tools** that can be used by an AI assistant via **MCP (Model Context Protocol)**.

You write **normal Python functions** that perform biology-related computations. The framework handles:
- Connecting your tools to an AI model,
- Auto-discovering tools you write,
- Loading sequence files (like `.gb` or `.fasta`),
- Accepting both resource names and raw sequences,
- Handling input validation.

> **The golden rule:** You write the biology logic. The framework connects it to the AI. The AI does *not* perform the biological computation; your Python code does. The AI simply interprets your results.

---

# 2. Core concepts

## Tools
A **tool** is a Python function you write to perform a specific computation.
*Examples:* Translate DNA → protein, reverse complement, compute GC content, scan for PAM sites, or design primers.
*Location:* `modules/seq_basics/tools/`

## Resources
A **resource** is a data file that your tools can use.
*Examples:* GenBank files (`.gb`), FASTA files (`.fasta`).
*Location:* `modules/seq_basics/data/`

Each file you place here automatically becomes available as a named resource. For example, if you add `pBR322.gb`, the resource name the AI uses will be `"pBR322"`.

---

# 3. How the pipeline works

When you run the project:

1. The MCP server starts.
2. It scans your module folders.
3. It automatically registers:
   - Tools
   - Resources
4. The AI assistant can now call your tools.
5. Your Python function runs.
6. The AI explains the result.

Important:

The AI does NOT perform the biological computation.
Your Python code does.

---

# 4. Project structure overview

Here is a map of the files you just downloaded. You will spend almost all of your time in the `tools` and `data` folders.
```
.
├── server.py                 # MCP server entry point
├── client_gemini.py          # Gemini-powered CLI client
├── SPEC.md                   # Architecture specification
├── requirements.txt
├── tests/
│   └── confest.py          
│   ├── test_registration_smoke.py 
│   ├── test_resolve.py
│   ├── test_tools.py
├── modules/
│   └── seq_basics/           # Example module
│       ├── SKILL.md          # LLM guidance for this module
│       ├── _plumbing/        # Auto-registration (don't modify)
│       ├── _utils.py         # Shared constants (codon table, etc.)
│       ├── data/
│       │   └── pBR322.gb     # Sequence resources
│       └── tools/
│           ├── translate.py
│           └── reverse_complement.py
```
You mostly work inside:
```bash
modules/seq_basics/tools/
modules/seq_basics/data/
```


---

# 5. Step-by-step quick start

## Step 0: Prerequisites

Before you begin, ensure you have the following installed on your computer:

1. Python (3.10 or newer)
2. Visual Studio Code (VS Code): A free code editor. 
3. Open this project folder inside VS Code. Open a new terminal inside VS Code by clicking `Terminal -> New Terminal` at the top of your screen.


## Step 1  — Create a virtual environment and install dependencies

A virtual environment keeps this project's files isolated from the rest of your computer. Run these commands in your terminal:

```bash
python -m venv .venv
source .venv/bin/activate
```

*(You will know it worked if you see* `(.venv)` *appear at the start of your terminal line).*

Now, install the required software packages:

```bash
pip install -r requirements.txt
```


## Step 2 — Add your Gemini API Key

You need a key to let your code talk to the Gemini AI.

1. In the root folder of your project, create a new file and name it exactly .env (don't forget the dot!).
2. Open the file and add your key like this:

```bash
GEMINI_API_KEY="your_key_here"
```

> 🛑 SECURITY WARNING: NEVER upload your `.env` file to GitHub or share it with anyone. If you are using Git, ensure `.env` is listed inside your `.gitignore` file.

## Step 3 — Run the Client

You are ready to go! Start the program:

```bash
python client_gemini.py
```

Try typing a prompt like:
```bash
Translate the first 60bp of pBR322 in frame 1
```
---
# 6. Adding a new tool 

To add a new capability, create a new `.py` file inside `modules/seq_basics/tools/`.

***Example:*** Let's create `dna_gc_content.py`


```bash
"""Compute GC content of a DNA sequence."""

# This dictionary tells the AI how to use your tool
TOOL_META = {
    "name": "dna_gc_content",
    "description": "Compute GC content (fraction of G/C bases).",
    "seq_param": "seq",
}

def gc_content(seq: str) -> float:
    """Return GC fraction between 0 and 1."""
    seq = seq.upper()
    gc = sum(1 for b in seq if b in "GC")
    return gc / len(seq) if seq else 0.0
```

Important rules for tools:

- The Python file name must match the function name (e.g., `gc_content.py` for `def gc_content`).
- You must include the `TOOL_META` dictionary.
- Always use type hints (e.g., `seq: str`).
- Return JSON-serializable values (str, int, float, list, dict).

***Restart the server*** (stop the terminal and run python `client_gemini.py` again) for your new tool to appear.
---

# 7. Tools with multiple sequences

If your tool compares two things, for example, specify multiple parameters in `TOOL_META`.
```bash
TOOL_META = {
    "name": "dna_hamming_distance",
    "description": "Count mismatches between two sequences.",
    "seq_params": ["seq1", "seq2"],
}

def hamming_distance(seq1: str, seq2: str) -> int:
    if len(seq1) != len(seq2):
        raise ValueError("Sequences must have equal length")
    return sum(a != b for a, b in zip(seq1, seq2))
```

*Note: Both* `seq1` *and* `seq2` *can be resource names (like "pBR322") or raw pasted sequences.*
---
# 8. Non-sequence inputs

Your tools can accept numbers, text, and other variables.
```bash
def find_pam_sites(seq: str, pam: str = "NGG", max_mismatch: int = 2) -> list[dict]:
    ...
```

Guidelines:

- Always validate inputs.
- Raise a `ValueError` with clear messages if the AI or user provides bad data.
- Return JSON-friendly data.
---
#9. Adding new sequence files
Drop any `.gb` or `.fasta` files into `modules/seq_basics/data/`. Restart your terminal server, and the file instantly becomes a resource the AI can read.

---
# 10. Creating a new module

If your final project grows large, you can organize it by creating new module folders:

- `modules/crispr/`
- `modules/cloning/`
- `modules/pathways/`

Each new module should contain its own `tools/`, `data/`, and a `SKILL.md` file to guide the AI (*Note: You may need to update* `modules/__init__.py` *to register new module folders*).
---
# 11. Testing your code

We use `pytest` to make sure code works. Run this command in your terminal to run the automated test suite:
```bash
pytest -vv -l
```
---
# 12. Troubleshooting
- ***API Key Missing Error:*** Ensure you created the `.env` file correctly in the main folder and that it contains `GEMINI_API_KEY="..."`.

- ***Gemini 503 Error:*** This means the Google servers are experiencing high demand. Wait a few minutes and try again.

- ***Command Not Found (***`python`***):*** You may need to type `python3` instead of `python` on Mac/Linux.
---
## Still stuck?
Send an email to your TA at: 
> javadamn@berkeley.edu

