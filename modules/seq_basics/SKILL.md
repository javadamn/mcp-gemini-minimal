---
name: seq-basics
description: DNA sequence analysis tools for bioinformatics workflows
---

# Sequence Analysis Tools

## Overview

This module provides tools for basic DNA sequence manipulation: translation, reverse complement, and related operations. Tools operate on sequence resources (GenBank files, FASTA files) or raw sequence strings.

## Working with Resources

Use `resources/list` to see available sequence files. Each resource has a short name (e.g., "pBR322") that you pass directly to tools.

**Always prefer resource names over raw sequences.** Passing `seq="pBR322"` is better than pasting 4361 nucleotides into the call.

Resources available in this module:
- **pBR322**: Classic E. coli cloning vector, 4361bp circular plasmid, contains ampicillin and tetracycline resistance genes

## Tools

### dna_translate

Translates DNA to protein using the standard genetic code.

Parameters:
- `seq`: Resource name or DNA sequence
- `start`, `end`: Optional coordinates (0-indexed)
- `frame`: Reading frame 1, 2, or 3 (default: 1)

Notes:
- Frame 1 starts at position 0, frame 2 at position 1, frame 3 at position 2
- Stop codons appear as `*` in output
- When searching for ORFs, check all 3 frames on both strands

### dna_reverse_complement

Returns the reverse complement of a DNA sequence.

Parameters:
- `seq`: Resource name or DNA sequence

Use this to get the opposite strand before translating, or when designing primers.

## Common Workflows

### Find ORFs in a plasmid

1. Translate forward strand in frames 1, 2, 3
2. Get reverse complement
3. Translate reverse complement in frames 1, 2, 3
4. Look for sequences between start codons (M) and stop codons (*)

### Verify a gene annotation

1. Use the resource name with start/end coordinates from the annotation
2. Translate and confirm the expected protein sequence
3. Check that it starts with M and ends with *

### Quick sequence check

For short sequences (under 100bp), you can paste the sequence directly:
```
dna_translate(seq="ATGGCTAGCTAG")
```

For anything longer, use a resource name.

## Sequence Input Formats

Tools accept multiple input formats, automatically detected:
- Resource name: `"pBR322"`
- Raw sequence: `"ATGCGATCG"`
- Sequence with whitespace: `"ATG CGA TCG"` (whitespace stripped)
- FASTA format: `">name\nATGCGATCG"`
- GenBank format: Full GenBank file content

When in doubt, use the resource name.
