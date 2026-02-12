# BioE234 MCP Starter — Student Guide

Welcome! This document explains how the BioE234 MCP Starter works and how you can extend it for your final project.

This guide assumes some students may be new to computer science. Everything is explained step-by-step.

---

# 1. What Is This Starter?

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

# 2. Core Concepts

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

# 3. How the Pipeline Works

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

# 4. Project Structure Overview
    '''bash
server.py # Starts MCP server
client_gemini.py # Gemini-based CLI client
    '''

modules/
init.py

seq_basics/
SKILL.md
_utils.py
_plumbing/
resources/
data/
tools/

You mostly work inside:

modules/seq_basics/tools/
modules/seq_basics/data/

yaml
Copy code

---

# 5. Quick Start

## Step 1  — Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash'''


## Step 2 — Add Your Gemini API Key

Create a file named .env in the project root:

GEMINI_API_KEY="your_key_here"

Step 3 — Run the Client
python client_gemini.py


Try:

Translate the first 60bp of pBR322 in frame 1




