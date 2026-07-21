# Repository Guidelines

## Project Structure & Module Organization

This repository contains an academic capstone project rather than a software application. The main deliverable is the root-level Word manuscript, `TCC CONFIABILIDADE DE SISTEMAS RAG NO SUPORTE TÉCNICO_ UM MECANISMO CALIBRADO DE SUFICIÊNCIA DA EVIDÊNCIA COM RECUPERAÇÃO LEXICAL E SEMÂNTICA.docx`. Supporting research papers are stored as PDFs under `Referemcoas/`. Preserve that directory name in links and commands unless a coordinated rename is approved. Keep draft exports, notes, and temporary Word files out of the root; add only material needed to reproduce or review the final work.

## Document Workflow & Validation Commands

There is no build system or automated test suite. Edit the manuscript in a DOCX-compatible editor and use Word's tracked changes for substantive review. Useful PowerShell checks are:

```powershell
Get-ChildItem -Recurse -File
Get-ChildItem .\Referemcoas\*.pdf | Select-Object Name, Length
```

The first inventories repository contents; the second confirms the reference library. Before submitting, update the automatic table of contents, inspect page numbering and heading hierarchy, accept or resolve tracked changes, run spelling/grammar checks in Portuguese, and open the final DOCX on a second machine or viewer.

## Writing Style & Naming Conventions

Write in formal Brazilian Portuguese and maintain consistent terminology for RAG, recuperação lexical, recuperação semântica, calibração, and suficiência da evidência. Use Word styles (`Heading 1`, `Heading 2`, body text, captions) instead of manual formatting. Follow the institution's required citation standard consistently. Name new references descriptively, preferably `Author_Year_Short_Title.pdf`; avoid ambiguous names such as `paper-final.pdf`.

## Evidence & Citation Checks

Every factual or methodological claim should point to a source in the bibliography. Verify author names, publication year, title, DOI or URL, and access date where applicable. Confirm that every in-text citation has a bibliography entry and that every listed reference is cited. Do not alter or annotate source PDFs in place; create a clearly named notes file if annotations must be shared.

## Commit & Pull Request Guidelines

No Git history or established commit convention is currently available. Use short, imperative commits such as `Revise methodology section` or `Add calibration references`, grouping manuscript and reference changes logically. Pull requests should summarize affected sections, explain citation additions or removals, identify formatting changes, and include screenshots or an exported PDF when layout changed. Avoid committing Word lock files (`~$*.docx`) or unrelated temporary exports.
