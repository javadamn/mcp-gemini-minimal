# BioE234 MCP Starter (Gemini + FastMCP)

This repo is a minimal starter for building an MCP server and testing it with a Gemini-powered CLI client.

The default example module is `seq_basics`, which provides two simple sequence tools and a single example resource (a `pBR322.gb` GenBank file).

Important: tools never read files or MCP resources. The CLI client is responsible for reading a GenBank resource, extracting the DNA sequence, and then calling the sequence-level tools.

## Setup

1. Create a virtual environment
- macOS/Linux:
  python -m venv .venv
  source .venv/bin/activate
- Windows (PowerShell):
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1

2. Install deps
  pip install -r requirements.txt

3. Configure environment

Create a file named `.env` in the repo root and add your Gemini API key:

  GEMINI_API_KEY="YOUR_KEY_HERE"

## Run

Run the Gemini-driven client (this launches the MCP server as a subprocess):
(The client lists tools/resources, sends tool schemas and resource metadata to Gemini, and adapts GenBank resources into sequences when needed.)
  python client_gemini.py

## Example module: seq_basics

When you run the client, the server exposes the `seq_basics` module by default.

### Tools
- `dna_reverse_complement`: reverse-complement a DNA sequence string (A/C/G/T only)
- `dna_translate`: translate a DNA sequence string (frame 1, standard genetic code)

### Resource
- `resource://seq_basics/pbr322_genbank`: GenBank file for pBR322 (`modules/seq_basics/data/pBR322.gb`)
The client can resolve this resource (URI -> GenBank text -> extracted DNA sequence) before calling tools.

## Model choice

`client_gemini.py` uses a fast/cheap Gemini model by default (`gemini-2.5-flash-lite`). You can switch models by editing `client_gemini.py`.
## Client commands

The interactive client supports a few slash commands:

- `/tools`
- `/resources`, `/resource <uri>`
- `/prompts`, `/prompt <name> [json_args]`
- `/help`
