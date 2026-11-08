---
name: web-design-guidelines
description: 'Use para "review my UI", "check accessibility" ou auditar UI contra as Web Interface Guidelines da Vercel, em file:line. Redesenhar é impeccable.'
metadata:
  author: vercel
  version: "1.0.0"
  argument-hint: <file-or-pattern>
---

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines.

## How It Works

1. Read the guidelines in [references/guidelines.md](references/guidelines.md)
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in the guidelines
4. Output findings in the terse `file:line` format

## Guidelines Source

The guidelines are pinned in `references/guidelines.md`, copied from `vercel-labs/web-interface-guidelines` at `434b7f9` (`command.md`). They contain all the rules and output format instructions. Do not fetch them from the web.

## Usage

When a user provides a file or pattern argument:
1. Read `references/guidelines.md`
2. Read the specified files
3. Apply all rules from the guidelines
4. Output findings using the format specified in the guidelines

If no files specified, ask the user which files to review.
