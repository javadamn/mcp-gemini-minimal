# BioE234 MCP Starter — Student Guide

Welcome! This document explains how the BioE234 MCP Starter works and how you can extend it for your final project.

This guide assumes some students may be new to computer science. Everything is explained step-by-step.

---

# 1. What is this starter?

This repository is a framework for building **bioengineering automation tools** that can be used by an AI assistant via **MCP (Model Context Protocol)**.

You write **normal Python functions** that perform biology-related computations.

The framework handles:
- Connecting your tools to an AI model
- Auto-discovering tools
- Loading sequence files
- Accepting both resource names and raw sequences
- Handling input validation

> You write the biology logic.  
> The framework connects it to the AI.

---

# 2. Core concepts

## Tools
A **tool** is a Python function that performs a computation.

Examples:
- Translate DNA → protein
- Reverse complement
- Compute GC content
- Scan for PAM sites
- Design primers
- Analyze mutations

Tools live in:
> modules/seq_basics/tools/

---

## Resources
A **resource** is a file that tools can use.

> Examples:
> - GenBank files (.gb)
> - FASTA files (.fasta)

Resources live in:
> modules/seq_basics/data/

Each file automatically becomes available as a named resource.

> Example:
pBR322.gb → resource name: "pBR322"

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

# 5. Quick start

## Step 1  — Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


## Step 2 — Add your Gemini API key

Create a file named .env in the project root:
```bash
GEMINI_API_KEY="your_key_here"
```
## Step 3 — Run the Client
```bash
python client_gemini.py
```

Try:
```bash
Translate the first 60bp of pBR322 in frame 1
```
---
# 6. Adding a new tool 

Create a new file inside:
```bash
modules/seq_basics/tools/
```

Example:
```bash
"""Compute GC content of a DNA sequence."""

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

Important Rules:

- File name must match function name.
- Include TOOL_META.
- Use type hints.
- Return JSON-serializable values (str, int, float, list, dict).

Restart the server and your tool will appear automatically.
---

# 7. Adding new sequence files

Add files into:
```bash
modules/seq_basics/data/
```

Restart the server. The file becomes a resource.

---

# 8. Tools with multiple sequences

Example:
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

Both parameters can be:
- resource names
- raw sequences
---
# 9. Non-sequence inputs

Tools can take other types:
```bash
def find_pam_sites(seq: str, pam: str = "NGG", max_mismatch: int = 2) -> list[dict]:
    ...
```

Guidelines:

- Always validate inputs.
- Raise ValueError with clear messages.
- Return JSON-friendly data.
---

# 10. Creating a new module

If your project grows large, you may create:
```bash
modules/crispr/
modules/cloning/
modules/pathways/
```

Each module should contain:
- tools/
- resources/
- data/
- SKILL.md

You may need to update "modules/__init__.py" to register new modules.
---
# 13. pytest suite

Run:
```bash
pytest -vv -l
```
---
# 14. Troubleshooting
- API Key Missing

Create .env with:
```bash
GEMINI_API_KEY="..."
```
- Gemini 503 Error

This means high demand. Retry later.
---
## Any issues ?
Send an email to: 
> javadamn@berkeley.edu

