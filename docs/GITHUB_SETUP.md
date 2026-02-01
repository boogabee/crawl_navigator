# GitHub Setup Guide

This document provides step-by-step instructions for setting up this repository on GitHub.

## Prerequisites

- GitHub account (free account is fine)
- Git installed locally
- Clone or access to this codebase

## Step-by-Step Setup

### 1. Create a GitHub Repository

1. Log in to [GitHub](https://github.com)
2. Click the **+** icon in the top right → **New repository**
3. Fill in the details:
   - **Repository name**: `crawl-navigator` (or `dcss-bot`, your choice)
   - **Description**: "An automated bot for Dungeon Crawl Stone Soup using Python"
   - **Visibility**: Public (to allow others to see and fork)
   - **Initialize repository**: Leave unchecked (we'll push existing code)

4. Click **Create repository**
5. You'll see instructions for pushing an existing repository

### 2. Initialize Local Git Repository

In the project directory:

```bash
# Initialize git
git init

# Add all files (excluding those in .gitignore)
git add .

# Verify what will be committed
git status

# Create initial commit
git commit -m "Initial commit: DCSS Bot fully functional with 71 passing tests"
```

### 3. Connect to GitHub

Replace `USERNAME` with your GitHub username and `REPONAME` with your repository name:

```bash
# Add remote origin (HTTPS method)
git remote add origin https://github.com/USERNAME/REPONAME.git

# Verify the remote is set
git remote -v
```

### 4. Push to GitHub

```bash
# Rename branch to main (GitHub standard)
git branch -M main

# Push to GitHub
git push -u origin main
```

## What Gets Uploaded

✅ **Source Code** (tracked):
- All `.py` files
- Documentation `.md` files
- Configuration files (requirements.txt, .gitignore, etc.)
- Tests in tests/ directory
- GitHub templates and workflows

❌ **Excluded from Git** (via .gitignore):
- `logs/` - Bot session logs (can be large)
- `venv/` - Virtual environment
- `__pycache__/` - Python cache
- `.pytest_cache/` - Test cache
- `crawl/` - Local DCSS installation (not needed for GitHub)
- IDE settings (`.vscode/`, `.idea/`)

## Repository Structure After Push

```
crawl-navigator/
├── README.md                      # Main documentation
├── LICENSE                        # MIT License
├── CHANGELOG.md                   # Version history
├── CONTRIBUTING.md                # Contribution guidelines
├── requirements.txt               # Python dependencies
├── .gitignore                     # Git exclusions
├── .github/
│   ├── copilot-instructions.md   # AI assistant instructions
│   ├── pull_request_template.md  # PR template for contributors
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md         # Bug report template
│       └── feature_request.md    # Feature request template
├── bot.py                         # Main bot logic
├── main.py                        # Entry point
├── local_client.py                # PTY handler
├── game_state.py                  # Game state parser
├── bot_unified_display.py         # Display engine
├── char_creation_state_machine.py # Menu automation
├── game_state_machine.py          # State tracking
├── credentials.py                 # Configuration
├── tests/                         # Test suite (71 tests)
└── [documentation files...]       # Architecture, guides, etc.
```

## Post-Upload: GitHub Features to Enable

### 1. Enable GitHub Pages (Optional)

If you want to host documentation:

1. Go to **Settings** → **Pages**
2. Select **Deploy from a branch**
3. Choose `main` branch and `/root` folder
4. Save

This will create a website from your README.

### 2. Setup GitHub Actions (Optional)

Create `.github/workflows/tests.yml` to run tests automatically:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: bash run_tests.sh
```

### 3. Enable Security Features

1. Go to **Settings** → **Security**
2. Enable:
   - Dependabot alerts
   - Dependabot security updates
   - Secret scanning

### 4. Add Topics (for discoverability)

1. Go to **Settings** → **General** (scroll down)
2. Add topics:
   - `dungeon-crawl`
   - `automation`
   - `python-bot`
   - `game-bot`
   - `dcss`

## Managing Your Repository

### Adding Collaborators

1. Go to **Settings** → **Collaborators**
2. Click **Add people**
3. Search for GitHub username and select appropriate access level

### Protecting Main Branch (Recommended)

1. Go to **Settings** → **Branches**
2. Click **Add rule**
3. For branch name pattern: `main`
4. Check:
   - Require a pull request before merging
   - Require status checks to pass (if using CI/CD)
   - Dismiss stale pull request approvals

### Regular Maintenance

- Review issues and PRs regularly
- Keep dependencies up to date (Dependabot helps)
- Update documentation as features change
- Maintain CHANGELOG.md with version updates

## Troubleshooting

### "fatal: remote origin already exists"

```bash
git remote remove origin
git remote add origin https://github.com/USERNAME/REPONAME.git
```

### "fatal: Not a git repository"

Make sure you're in the project directory:
```bash
cd /path/to/crawl-navigator
git status
```

### Cannot push after authentication

Use HTTPS with GitHub token or SSH with keys:
```bash
# HTTPS with token
git remote set-url origin https://[token]@github.com/USERNAME/REPONAME.git

# SSH (if keys configured)
git remote set-url origin git@github.com:USERNAME/REPONAME.git
```

## What's Included for Collaboration

The repository includes everything contributors need:

- **CONTRIBUTING.md** - Guides for submitting changes
- **Issue templates** - Standardized bug reports and feature requests
- **Pull request template** - Consistent PR format
- **Detailed documentation** - Architecture guides, developer guide, CHANGELOG
- **Full test suite** - 71 passing tests for validation

## Next Steps After Uploading

1. **Update the README** with the GitHub repository URL
2. **Add a Topics section** on the repository page (for discoverability)
3. **Enable GitHub Discussions** (if you want community discussions)
4. **Create initial Releases** (optional - for version tracking)
5. **Link from your website/portfolio** (if applicable)

## Resources

- [GitHub Quick Start](https://docs.github.com/en/get-started/quickstart)
- [About branches and merging](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Markdown formatting](https://guides.github.com/features/mastering-markdown/)

---

Your DCSS Bot is now ready for the world! 🚀
