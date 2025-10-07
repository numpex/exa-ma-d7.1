# AGENTS.md - LaTeX Compilation Guide

This document explains how to compile the ExaMA D7.1 deliverable LaTeX document using `latexmk`.

## Overview

This project uses LaTeX with the `minted` package for syntax highlighting, which requires `--shell-escape` during compilation. The document is automatically compiled using GitHub Actions on push/tag events and can be compiled locally using various methods.

## Compilation Methods

### 1. Using latexmk (Recommended)

The recommended way to compile the document is using `latexmk` with shell escape enabled:

```bash
latexmk --shell-escape -pdf -interaction=nonstopmode -synctex=1 exa-ma-d7.1.tex
```

**Key flags:**
- `--shell-escape`: Required for the `minted` package to execute external programs for syntax highlighting
- `-pdf`: Generate PDF output
- `-interaction=nonstopmode`: Continue compilation even if there are non-critical errors
- `-synctex=1`: Enable SyncTeX for editor integration (forward/backward search)

### 2. Using VS Code LaTeX Workshop

The project includes VS Code configuration in `.vscode/settings.json` that sets up:

- **Auto-build on save**: The document compiles automatically when you save any `.tex` file
- **Two compilation recipes**:
  1. `latexmk-pdf` (default): Uses `latexmk` with shell escape
  2. `pdflatex-shell-escape-recipe`: Direct `pdflatex` compilation

**VS Code settings highlights:**
```json
{
    "latex-workshop.latex.recipes": [
        {
            "name": "latexmk-pdf",
            "tools": ["latexmk-shell-escape"]
        }
    ],
    "latex-workshop.latex.tools": [
        {
            "name": "latexmk-shell-escape",
            "command": "latexmk",
            "args": [
                "--shell-escape",
                "-pdf",
                "-interaction=nonstopmode",
                "-synctex=1",
                "%DOC%"
            ]
        }
    ],
    "latex-workshop.latex.autoBuild.run": "onSave",
    "latex-workshop.latex.autoBuild.enabled": true
}
```

### 3. Using the CLI Helper Script

The project includes an `a.cli` script that provides various utilities:

```bash
# Clean build artifacts
./a.cli clean

# Setup git hooks
./a.cli setup

# Update bibliography from Zotero
./a.cli update-bibtex
```

### 4. Using GitHub Actions (CI/CD)

The project automatically compiles on GitHub Actions when:
- Pushing to any branch
- Creating tags (for releases)

**Workflow details** (`.github/workflows/latex.yml`):
- Uses either `ubuntu-latest` with `xu-cheng/latex-action@v3` or self-hosted TeXLive runner
- Compilation command: `latexmk -shell-escape -pdf -file-line-error -halt-on-error -interaction=nonstopmode exa-ma-d7.1.tex`
- Automatically updates bibliography from Zotero (on non-main branches)
- Creates releases with PDF artifacts for tagged versions

## Requirements

### LaTeX Packages
The document requires several LaTeX packages, including:
- `minted` (for code syntax highlighting - **requires Python and Pygments**)
- `pgfplots`, `tikz` (for graphics)
- `booktabs`, `tabularx`, `longtable` (for tables)
- `cleveref`, `acronym` (for references)
- Custom `numpex.sty` style file

### System Dependencies
- **LaTeX distribution** (TeX Live, MikTeX, etc.)
- **Python** with **Pygments** library (for `minted` package)
- **shell-escape** capability enabled

### Installing Python and Pygments
```bash
# On Ubuntu/Debian
sudo apt-get install python3-pygments

# On macOS with Homebrew
brew install pygments

# Using pip
pip install pygments
```

## Troubleshooting

### Common Issues

1. **Shell escape not enabled**
   ```
   Error: Package minted Error: You must invoke LaTeX with the -shell-escape flag.
   ```
   **Solution**: Always use `--shell-escape` flag with your LaTeX compilation command.

2. **Pygments not found**
   ```
   Error: Package minted Error: You must have 'pygmentize' installed.
   ```
   **Solution**: Install Python and Pygments as described above.

3. **Permission issues with shell escape**
   Some systems require explicit enabling of shell escape in TeXLive configuration.
   
4. **Missing fonts or style files**
   Ensure all custom `.sty` files are in the project directory or LaTeX path.

### Build Artifacts Cleanup

After compilation, you can clean up temporary files:
```bash
# Using the CLI script
./a.cli clean

# Manual cleanup
rm -f *.aux *.bbl *.blg *.log *.out *.pyg *.fls *.synctex* *.toc *.fdb_latexmk *.idx *.ilg *.ind *.chl *.lof *.lot

# Clean minted cache
rm -rf _minted-exa-ma-d7.1/
```

## File Structure

- **Main document**: `exa-ma-d7.1.tex`
- **Chapters**: `chapters/` directory
- **Sections**: `sections/` directory  
- **Graphics**: `graphics/` directory
- **Software info**: `software/` directory
- **Bibliography**: `references.bib`
- **Style files**: `numpex.sty`, `istcover.sty`, `istprog.sty`

## Development Workflow

1. **Setup**: Run `./a.cli setup` to install git hooks
2. **Edit**: Modify `.tex` files as needed
3. **Compile**: Use VS Code (auto-compile) or run `latexmk --shell-escape -pdf exa-ma-d7.1.tex`
4. **Clean**: Run `./a.cli clean` when needed
5. **Commit**: Git hooks will automatically update version info
6. **Release**: Tag with `vX.Y.Z` format to trigger automatic release build

## Release Process

To create a new release:
```bash
# Create and push a version tag
./a.cli create v1.0.0

# This will:
# 1. Tag the repository
# 2. Update version info
# 3. Trigger GitHub Actions
# 4. Create a release with PDF artifact
```

The GitHub Actions workflow will automatically:
- Compile the LaTeX document
- Create a release
- Upload the PDF and source archive as release assets