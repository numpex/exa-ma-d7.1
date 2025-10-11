# AGENTS.md - LaTeX Compilation Guide for ExaMA D7.1

This document explains how to compile the ExaMA D7.1 deliverable LaTeX document using modern CI/CD with `article-cli` and `uv`.

## Overview

This project uses LaTeX with the `minted` package for syntax highlighting, which requires `--shell-escape` during compilation. The document is automatically compiled using GitHub Actions on push/tag events and can be compiled locally using various methods.

**Recent Updates**: The project has been modernized to use the `article-cli` PyPI package for centralized tool management, while maintaining backward compatibility with the existing `a.cli` script.

## Compilation Methods

### 1. Using article-cli (Modern Approach - Recommended)

The modern way uses the `article-cli` PyPI package for centralized tool management:

```bash
# Install article-cli
pip install article-cli>=1.0.3

# Setup hooks and configuration
article-cli setup

# Update bibliography from Zotero
article-cli update-bibtex

# Clean build artifacts
article-cli clean

# Compile LaTeX
latexmk --shell-escape -pdf -interaction=nonstopmode -synctex=1 exa-ma-d7.1.tex
```

**Benefits of article-cli:**
- Centralized tool management across multiple repositories
- Integrated Zotero bibliography management
- Consistent configuration via `pyproject.toml`
- Better CI/CD integration

### 2. Using Legacy a.cli Script (Still Supported)

The existing custom script provides additional development features:

```bash
# Setup hooks
./a.cli setup

# Fast compilation options
./a.cli compile wp           # Only Work Packages (WP1-WP6)
./a.cli compile methodology  # Only methodology chapter
./a.cli compile applications # Only applications chapter
./a.cli compile software     # Only software chapter
./a.cli compile draft        # Ultra-fast draft mode
./a.cli compile all          # Full compilation

# Update bibliography and clean
./a.cli update-bibtex
./a.cli clean
```

### 3. Using latexmk Directly

For direct compilation:

```bash
latexmk --shell-escape -pdf -interaction=nonstopmode -synctex=1 exa-ma-d7.1.tex
```

**Key flags:**
- `--shell-escape`: Required for the `minted` package to execute external programs for syntax highlighting
- `-pdf`: Generate PDF output
- `-interaction=nonstopmode`: Continue compilation even if there are non-critical errors
- `-synctex=1`: Enable SyncTeX for editor integration (forward/backward search)

### 4. Using VS Code LaTeX Workshop

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

### 5. Using GitHub Actions (CI/CD)

The project automatically compiles on GitHub Actions when:
- Pushing to main branch
- Creating pull requests to main
- Creating tags (for releases)

**Workflow details** (`.github/workflows/latex.yml`):
- Uses either `ubuntu-latest` with `xu-cheng/latex-action@v3` or self-hosted TeXLive runner
- **Modern features**: UV package manager, isolated virtual environments, comprehensive summaries
- **article-cli integration**: Centralized tool management with `article-cli>=1.0.3`
- **Pull request support**: Special naming (`exa-ma-d7.1-pr-N.pdf`) and git handling
- Automatically updates bibliography from Zotero using article-cli
- Creates releases with PDF artifacts for tagged versions

## Configuration

### Zotero Integration

The project is configured to use:
- **Zotero Group ID**: 5562142 (Exa-MA)
- **Output File**: references.bib
- **API Key**: Set via `ZOTERO_API_KEY` environment variable

Configuration is managed in `pyproject.toml`:
```toml
[tool.article-cli]
zotero_group_id = 5562142
zotero_group_name = "Exa-MA"
output_file = "references.bib"
git_branch = "main"
```

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
- **article-cli** package (for modern workflow)
- **shell-escape** capability enabled

### Installing Python and Pygments
```bash
# On Ubuntu/Debian
sudo apt-get install python3-pygments

# On macOS with Homebrew
brew install pygments

# Using pip
pip install pygments

# For modern workflow
pip install article-cli>=1.0.3
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
# Using article-cli (modern)
article-cli clean

# Using legacy script
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

### Modern Workflow (Recommended)
1. **Setup**: `pip install article-cli && article-cli setup`
2. **Edit**: Modify `.tex` files as needed
3. **Update bibliography**: `article-cli update-bibtex`
4. **Compile**: `latexmk --shell-escape -pdf exa-ma-d7.1.tex`
5. **Clean**: `article-cli clean`

### Legacy Workflow (Still supported)
1. **Setup**: `./a.cli setup`
2. **Fast compile**: `./a.cli compile wp` (for quick iteration)
3. **Full compile**: `./a.cli compile all`
4. **Clean**: `./a.cli clean`

## Release Process

Creating a release for the ExaMA D7.1 document involves two main steps: creating an annotated git tag and then creating a GitHub release. The GitHub Actions workflow will automatically compile the LaTeX document and attach the PDF to the release.

### Quick Release Guide

#### 1. Create an Annotated Git Tag

Annotated tags are required for releases. They include metadata like tagger name, email, date, and a message.

```bash
# For a stable release
git tag -a v1.0.0 -m "Release v1.0.0 - Description of changes"

# For a release candidate
git tag -a v1.0.0-rc.1 -m "Release candidate 1 for v1.0.0"

# For a preview/pre-release
git tag -a v1.0.0-preview.1 -m "Preview release for v1.0.0"
```

**Version Naming Convention:**
- **Stable releases**: `vX.Y.Z` (e.g., `v1.0.0`, `v2.1.3`)
- **Release candidates**: `vX.Y.Z-rc.N` (e.g., `v1.0.0-rc.1`, `v1.0.0-rc.2`)
- **Preview releases**: `vX.Y.Z-preview.N` (e.g., `v1.90.0-preview.1`)
- **Alpha releases**: `vX.Y.Z-alpha.N` (e.g., `v2.0.0-alpha.1`)
- **Beta releases**: `vX.Y.Z-beta.N` (e.g., `v2.0.0-beta.1`)

#### 2. Push the Tag

```bash
# Push the tag to GitHub
git push origin v1.0.0

# Or push all tags at once
git push origin --tags
```

#### 3. Create GitHub Release

Use the GitHub CLI (`gh`) to create the release from the tag:

```bash
# For a stable release
gh release create v1.0.0 \
  --title "Release v1.0.0" \
  --notes "Description of changes in this release"

# For a pre-release (rc, preview, alpha, beta)
gh release create v1.0.0-rc.1 \
  --title "Release Candidate v1.0.0-rc.1" \
  --notes "First release candidate for v1.0.0" \
  --prerelease
```

The `--prerelease` flag marks the release as a pre-release, which is automatically applied for tags containing `rc`, `alpha`, `beta`, or `preview` by the GitHub Actions workflow.

### Complete Release Example

Here's a complete example of creating and releasing version 1.90.0:

```bash
# Step 1: Ensure you're on the main branch and up to date
git checkout main
git pull

# Step 2: Create an annotated tag
git tag -a v1.90.0 -m "Release v1.90.0 - ExaMA D7.1 Benchmarking Report"

# Step 3: Push the tag to GitHub
git push origin v1.90.0

# Step 4: Create the GitHub release
gh release create v1.90.0 \
  --title "Release v1.90.0" \
  --notes "ExaMA D7.1 Benchmarking Analysis Report v1.90.0

## Highlights
- Updated repository structure and documentation
- Enhanced LaTeX compilation workflow with article-cli
- Bibliography updates from Zotero
- Improved CI/CD pipeline with UV and isolated environments

## Compilation
The PDF has been automatically compiled and attached by the CI/CD workflow.

## Changes
See the full changelog below for detailed changes."
```

### Release Candidates Example

For creating release candidates (useful for testing before final release):

```bash
# First release candidate
git tag -a v2.0.0-rc.1 -m "Release candidate 1 for v2.0.0"
git push origin v2.0.0-rc.1
gh release create v2.0.0-rc.1 \
  --title "Release Candidate v2.0.0-rc.1" \
  --notes "First release candidate for v2.0.0 - Please test!" \
  --prerelease

# Second release candidate (after fixes)
git tag -a v2.0.0-rc.2 -m "Release candidate 2 for v2.0.0"
git push origin v2.0.0-rc.2
gh release create v2.0.0-rc.2 \
  --title "Release Candidate v2.0.0-rc.2" \
  --notes "Second release candidate with bug fixes" \
  --prerelease

# Final stable release
git tag -a v2.0.0 -m "Release v2.0.0"
git push origin v2.0.0
gh release create v2.0.0 \
  --title "Release v2.0.0" \
  --notes "Stable release v2.0.0"
```

### What Happens Automatically

Once you create the GitHub release, the CI/CD workflow (`.github/workflows/latex.yml`) automatically:

1. **Detects the tag**: Triggered by the `v*` tag pattern
2. **Sets up the environment**: Installs Python, UV, and article-cli
3. **Updates bibliography**: Fetches latest references from Zotero
4. **Compiles LaTeX**: Generates the PDF with latexmk and shell-escape
5. **Creates artifacts**: 
   - Compiled PDF: `exa-ma-d7.1-vX.Y.Z.pdf`
   - Source archive: `exa-ma-d7.1-vX.Y.Z.tar.gz`
6. **Attaches to release**: Uploads both files to the GitHub release
7. **Marks as pre-release**: Automatically detects `rc`, `alpha`, `beta`, `preview` in tag name

### Viewing Releases

You can view all releases at:
```
https://github.com/numpex/exa-ma-d7.1/releases
```

Or using the GitHub CLI:
```bash
# List all releases
gh release list

# View a specific release
gh release view v1.90.0

# Download release assets
gh release download v1.90.0
```

### Using article-cli for Releases (Alternative Method)

You can also use `article-cli` to create releases, which combines tag creation and git operations:

```bash
# Using article-cli to create a release tag
article-cli create v1.0.0

# Then create the GitHub release
gh release create v1.0.0 \
  --title "Release v1.0.0" \
  --notes "Description of changes"
```

Note: `article-cli create` will:
- Create an annotated tag
- Update `gitHeadLocal.gin` with release information
- Commit the change
- You still need to use `gh release create` to publish on GitHub

### Semantic Versioning Guidelines

Follow semantic versioning for releases:

- **MAJOR version (X.0.0)**: Incompatible changes, major restructuring
- **MINOR version (X.Y.0)**: New features, significant updates (backwards compatible)
- **PATCH version (X.Y.Z)**: Bug fixes, minor updates (backwards compatible)

Examples:
- `v1.0.0` → `v1.0.1`: Bug fixes in existing content
- `v1.0.0` → `v1.1.0`: New chapter or significant content addition
- `v1.0.0` → `v2.0.0`: Major restructuring or complete rewrite

### Troubleshooting Releases

**Issue**: Tag already exists
```bash
# Delete local tag
git tag -d v1.0.0

# Delete remote tag
git push origin --delete v1.0.0

# Recreate the tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

**Issue**: Release creation failed in CI/CD
- Check the Actions tab: https://github.com/numpex/exa-ma-d7.1/actions
- Verify the Zotero API key is set correctly in repository secrets
- Ensure the tag follows the `v*` pattern

**Issue**: PDF not attached to release
- Wait for the workflow to complete (check Actions tab)
- The workflow may take several minutes to compile the LaTeX document
- Check workflow logs for compilation errors

---

## Migration Notes

This repository has been updated to use the modern `article-cli` approach while maintaining backward compatibility with the existing `a.cli` script. The GitHub Actions workflow now uses:

- **UV** instead of pip for faster Python setup
- **article-cli** for centralized tool management
- **Comprehensive summaries** for better CI/CD visibility
- **Pull request support** with proper PDF naming

Both approaches work, but `article-cli` provides better integration with the PyPI ecosystem and standardized tool management across multiple repositories.

---

**Remember**: Always test locally before releasing, and ensure the Zotero API key is properly configured for bibliography updates!