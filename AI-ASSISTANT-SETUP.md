# AI Assistant Integration for ATC-1

Complete guide to keeping ChatGPT Plus and Claude Desktop updated with your ATC codebase using Supermemory.

## 🎯 Overview

This integration allows ChatGPT and Claude to:
- ✅ Search your entire ATC codebase semantically
- ✅ Understand recent changes and commits
- ✅ Reference actual code when helping you
- ✅ Debug issues with full project context
- ✅ Plan features based on existing architecture
- ✅ Stay automatically updated via git hooks

**Cost:** Free (uses Supermemory free tier: 1M tokens, 10K searches/month)

## 📁 Directory Structure

```
/ATC-1/
├── supermemory-integration/   # Core sync scripts
│   ├── sync-codebase.js       # Initial full sync
│   ├── track-changes.js       # Git commit tracker
│   ├── query-codebase.js      # Test queries
│   ├── install-hooks.js       # Git hook installer
│   └── README.md              # Detailed instructions
│
├── custom-gpt/                # ChatGPT Plus integration
│   ├── openapi-spec.yaml      # Supermemory API spec
│   ├── instructions.md        # Custom GPT instructions
│   └── README.md              # Setup guide
│
├── mcp-server/                # Claude Desktop integration
│   ├── server.js              # MCP server
│   └── README.md              # Setup guide
│
└── AI-ASSISTANT-SETUP.md      # This file
```

## 🚀 Quick Start (15 minutes)

### Step 1: Set Up Supermemory Integration (5 min)

```bash
# Navigate to integration directory
cd supermemory-integration

# Install dependencies
npm install

# Configure API key
cp .env.example .env
# Edit .env and add your Supermemory API key from https://supermemory.ai/dashboard
```

### Step 2: Initial Codebase Sync (5 min)

```bash
# Upload entire codebase to Supermemory
npm run sync
```

Expected output:
```
📈 Sync Complete!
✅ Files processed: 189
📝 Memories created: 234
💾 Data processed: 1847KB
```

### Step 3: Install Git Hooks (1 min)

```bash
# Enable automatic commit tracking
npm run install-hooks
```

### Step 4: Test the Integration (2 min)

```bash
# Run test queries
npm run query
```

You should see search results from your actual codebase.

### Step 5: Set Up AI Assistants (2-10 min)

Choose one or both:

**For ChatGPT Plus:**
- See `/custom-gpt/README.md`
- Create Custom GPT with Supermemory Actions
- Takes ~5 minutes

**For Claude Desktop:**
- See `/mcp-server/README.md`
- Configure MCP server
- Takes ~10 minutes

## 💡 How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your ATC Codebase                     │
│           (Next.js + Python + TypeScript)                │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ git commit
                     ↓
        ┌────────────────────────┐
        │   Git Post-Commit Hook  │
        │   (track-changes.js)    │
        └────────────┬───────────┘
                     │
                     │ uploads changes
                     ↓
        ┌────────────────────────┐
        │      Supermemory API    │
        │   (1M tokens free tier) │
        └────────────┬───────────┘
                     │
         ┌───────────┴──────────┐
         │                      │
         ↓                      ↓
┌─────────────────┐  ┌──────────────────┐
│  ChatGPT Plus   │  │ Claude Desktop   │
│  (Custom GPT)   │  │  (MCP Server)    │
│  Actions API    │  │  Local tools     │
└─────────────────┘  └──────────────────┘
```

### What Gets Synced

**Source Files:**
- TypeScript/JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`)
- Python (`.py`)
- Configuration (`.json`, `.yaml`, `.yml`)
- Documentation (`.md`)
- SQL, Shell scripts, CSS

**Metadata for each file:**
- File path
- Programming language
- Last modified date
- Line numbers (for chunks)
- Project name

**Commit Information:**
- Commit hash and message
- Author and date
- Files changed
- Additions/deletions
- Semantic summary

### What's Excluded

- `node_modules/`
- Virtual environments (`venv/`)
- Build artifacts
- Logs and cache
- `.git/` directory
- Everything in `.gitignore`

## 🎮 Daily Usage

### 1. Normal Development Workflow

Just commit as usual:

```bash
git add .
git commit -m "Fixed distance calculation bug in geo_utils.py"
git push
```

The git hook automatically:
1. Captures commit details
2. Extracts changes
3. Creates semantic summary
4. Uploads to Supermemory

**You don't need to do anything else!**

### 2. Using ChatGPT Plus

Open your Custom GPT and ask naturally:

```
How does the physics engine calculate aircraft position?
```

ChatGPT will:
1. Search your Supermemory codebase
2. Find relevant files (e.g., `kinematics.py`, `geo_utils.py`)
3. Show actual code snippets
4. Explain based on your implementation

More examples:
```
What were the recent changes to the radar display?
Show me how aircraft spawning works
I'm getting an error in distance calculation, can you help?
How should I add a new aircraft property?
```

### 3. Using Claude Desktop

Just chat naturally with Claude:

```
Search my codebase for the radar display implementation
```

Claude will:
1. Automatically invoke the `search_codebase` tool
2. Query Supermemory
3. Show results and explain

The 🔌 icon shows available tools.

### 4. Debugging with Context

**Scenario:** You get an error

**Before (without integration):**
```
You: I'm getting a TypeError in the radar component
ChatGPT: Can you share the code?
You: [Pastes code]
ChatGPT: [Generic suggestions]
```

**After (with integration):**
```
You: I'm getting a TypeError in the radar component
ChatGPT: [Searches codebase for RadarDisplay.tsx]
        I found the radar component. Looking at the actual code,
        the error is likely on line 147 where...
        [Shows actual code and specific fix]
```

### 5. Planning New Features

```
You: I want to add weather integration to the ATC system

ChatGPT: [Searches for existing architecture]
         Based on your current system:
         
         1. Your physics engine is in atc-brain-python/engine/
         2. Event system uses Redis pub/sub
         3. Frontend components in atc-nextjs/src/components/
         
         Here's how to integrate weather:
         [Specific recommendations based on actual code]
```

## 🔄 Keeping Everything Updated

### Automatic Updates (Recommended)

Once git hooks are installed, updates happen automatically:

```bash
git commit -m "Added new feature"
# ✅ Automatically tracked in Supermemory
```

ChatGPT and Claude immediately know about the change.

### Manual Updates

If you want to force-sync everything:

```bash
cd supermemory-integration
npm run sync
```

Use this if:
- You made changes outside git
- You want to re-upload everything
- Initial sync was interrupted

### Verifying Sync Status

Check what's in Supermemory:

```bash
cd supermemory-integration
npm run query

# Or search for something specific:
node query-codebase.js "recent commits"
```

## 📊 Usage Limits (Free Tier)

Supermemory free tier includes:

| Resource | Limit | Typical Usage |
|----------|-------|---------------|
| Tokens | 1M/month | ~750 average files |
| Searches | 10K/month | ~300 searches/day |
| Storage | Unlimited | All your code |

**For this ATC project:**
- Initial sync: ~234 memories, ~300K tokens
- Per commit: ~1 memory, ~2K tokens
- Per search: Counts as 1 search

You're well within limits for daily development.

## 🛠️ Advanced Configuration

### Customize What Gets Synced

Edit `supermemory-integration/sync-codebase.js`:

```javascript
// Add more file extensions
const INCLUDE_PATTERNS = [
  '**/*.js',
  '**/*.py',
  '**/*.go',  // Add Go files
  '**/*.rb',  // Add Ruby files
];

// Exclude specific directories
const ADDITIONAL_IGNORE = [
  'node_modules/**',
  'my-custom-folder/**',  // Add your exclusions
];

// Change file size limit
const MAX_FILE_SIZE_KB = 1000;  // Default: 500KB
```

### Adjust Chunking

For very large files:

```javascript
// In sync-codebase.js
const CHUNK_SIZE_LINES = 300;  // Default: 200
```

### Multiple Projects

You can use the same Supermemory account for multiple projects:

```bash
# Project 1
cd project1/supermemory-integration
# Edit .env: PROJECT_NAME=Project1
npm run sync

# Project 2
cd project2/supermemory-integration
# Edit .env: PROJECT_NAME=Project2
npm run sync
```

When searching, results will include project name in metadata.

## 🐛 Troubleshooting

### Supermemory Integration Issues

**Problem:** "API Key not set"

**Fix:**
```bash
cd supermemory-integration
cat .env  # Check API key exists
# If not, copy from .env.example and add your key
```

**Problem:** Initial sync finds no files

**Fix:**
```bash
# Check you're in the right directory
pwd  # Should be ATC-1/supermemory-integration

# Check parent directory
ls ..  # Should show atc-nextjs, atc-brain-python, etc.
```

**Problem:** Git hook not running

**Fix:**
```bash
# Check if hook exists
ls -la ../.git/hooks/post-commit

# If not, reinstall
cd supermemory-integration
npm run install-hooks

# Make a test commit
git commit --allow-empty -m "Test commit"
```

### ChatGPT Issues

**Problem:** Custom GPT not using search

**Fix:**
1. Check Actions are configured
2. Verify API key in Actions settings
3. Make sure instructions mention using searchCodebase
4. Try asking explicitly: "Search the codebase for X"

**Problem:** Search returns no results

**Fix:**
1. Test Supermemory directly: `cd supermemory-integration && npm run query`
2. If that works, issue is with Custom GPT Actions
3. Re-import OpenAPI spec
4. Check API key is correct

### Claude Desktop Issues

**Problem:** Tools not showing

**Fix:**
1. Check config file syntax (must be valid JSON)
2. Verify absolute paths are correct
3. Restart Claude Desktop completely
4. Check logs:
   ```bash
   # macOS
   tail -f ~/Library/Logs/Claude/mcp*.log
   ```

**Problem:** MCP server crashes

**Fix:**
```bash
# Check Node version
node --version  # Must be 18+

# Reinstall dependencies
cd mcp-server
rm -rf node_modules
npm install

# Test server
npm start
```

## 📚 Detailed Documentation

Each component has its own detailed README:

| Component | Location | What It Covers |
|-----------|----------|----------------|
| **Supermemory Integration** | `/supermemory-integration/README.md` | Sync scripts, git hooks, configuration |
| **Custom GPT** | `/custom-gpt/README.md` | ChatGPT Plus setup, Actions configuration |
| **MCP Server** | `/mcp-server/README.md` | Claude Desktop integration, tools |

## 💡 Tips & Best Practices

### 1. Write Good Commit Messages

Since commits are tracked, write descriptive messages:

```bash
# ❌ Bad
git commit -m "fix"

# ✅ Good
git commit -m "Fixed distance calculation bug in geo_utils.py by correcting haversine formula"
```

AI assistants use commit messages for context.

### 2. Ask Specific Questions

```bash
# ❌ Vague
"How does the system work?"

# ✅ Specific
"How does the radar display component render aircraft positions?"
```

### 3. Reference Recent Work

```bash
"We just added airspace sectors. How do they integrate with the existing controller logic?"
```

AI can search for recent commits and relevant code.

### 4. Use for Onboarding

Share your Custom GPT link with team members:
```
"Ask the ATC Codebase Assistant anything about the project!"
```

### 5. Regular Syncs

Run a full sync weekly or after major changes:

```bash
cd supermemory-integration
npm run sync
```

## ✅ Complete Setup Checklist

- [ ] Supermemory account created
- [ ] API key obtained
- [ ] Dependencies installed (`npm install`)
- [ ] `.env` configured
- [ ] Initial sync completed (`npm run sync`)
- [ ] Git hooks installed (`npm run install-hooks`)
- [ ] Test queries successful (`npm run query`)
- [ ] ChatGPT Custom GPT created (if using)
- [ ] Claude MCP server configured (if using)
- [ ] Test commit tracked
- [ ] AI assistant search working

## 🎉 You're All Set!

Your AI assistants now have full access to your ATC codebase and will stay automatically updated.

**Next Steps:**
1. Make a commit and verify it's tracked
2. Ask ChatGPT or Claude about your codebase
3. Use AI assistants for debugging and planning
4. Share with team members

---

**Questions or Issues?**
- Check component-specific READMEs in each directory
- Test Supermemory directly: `npm run query`
- Verify git hooks are running: Check logs after commit
- Review [Supermemory Docs](https://docs.supermemory.ai)

**Happy Coding! 🚀**

