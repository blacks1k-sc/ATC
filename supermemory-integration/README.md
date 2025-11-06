# Supermemory Integration for ATC-1

Automatically sync your ATC codebase to Supermemory and keep ChatGPT Plus and Claude Desktop updated with your project context and changes.

## 🎯 What This Does

- **Initial Sync**: Uploads your entire codebase to Supermemory (respects .gitignore)
- **Automatic Tracking**: Git hooks track every commit and update Supermemory
- **AI Integration**: ChatGPT and Claude can search your codebase semantically
- **Change Context**: AI assistants understand what changed and why
- **Free**: Uses Supermemory's free tier (1M tokens, 10K searches/month)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd supermemory-integration
npm install
```

### 2. Configure API Key

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Supermemory API key
# Get it from: https://supermemory.ai/dashboard
```

Your `.env` should look like:
```
SUPERMEMORY_API_KEY=sm_xxxxxxxxxxxxx
PROJECT_ROOT=..
PROJECT_NAME=ATC-1
```

### 3. Initial Sync

Upload your entire codebase to Supermemory (one-time):

```bash
npm run sync
```

This will:
- ✅ Scan all source files (JS, TS, Python, etc.)
- ✅ Skip build artifacts and dependencies
- ✅ Chunk large files appropriately
- ✅ Add metadata (file path, language, timestamps)
- ✅ Upload to Supermemory

Expected output:
```
🚀 Starting codebase sync to Supermemory...
📁 Project: ATC-1
📂 Root: /Users/nrup/ATC-1

📊 Found 247 files matching patterns
🔄 Processing 189 files...

✅ atc-nextjs/src/components/ATCSystem.tsx
✅ atc-brain-python/engine/core_engine.py
...

📈 Sync Complete!
✅ Files processed: 189
📝 Memories created: 234
💾 Data processed: 1847KB
```

### 4. Install Git Hooks

Enable automatic tracking of every commit:

```bash
npm run install-hooks
```

This creates a post-commit hook that automatically syncs changes to Supermemory after each commit.

### 5. Test the Integration

```bash
npm run query
```

Or search for something specific:
```bash
node query-codebase.js "physics engine kinematics"
```

## 📝 Usage

### Daily Workflow

Just commit as normal:

```bash
git add .
git commit -m "Fixed distance calculation bug in geo_utils.py"
```

The git hook automatically:
1. Captures commit details
2. Extracts file changes and diffs
3. Creates semantic summary
4. Uploads to Supermemory in the background

### Querying Your Codebase

**Test Queries:**
```bash
npm run query
```

**Custom Query:**
```bash
node query-codebase.js "How does the radar display work?"
```

### Manual Change Tracking

Track the last commit manually:
```bash
npm run track
```

## 🔧 Scripts

| Command | Description |
|---------|-------------|
| `npm run sync` | Initial full codebase sync |
| `npm run track` | Track last commit |
| `npm run query` | Test search queries |
| `npm run install-hooks` | Install git post-commit hook |

## 🎨 What Gets Synced

### Included Files
- JavaScript/TypeScript (`.js`, `.jsx`, `.ts`, `.tsx`)
- Python (`.py`)
- Configuration (`.json`, `.yaml`, `.yml`)
- Documentation (`.md`)
- SQL, Shell scripts, CSS

### Excluded Files
- `node_modules/`
- Virtual environments (`venv/`)
- Build artifacts (`dist/`, `build/`)
- Logs and cache
- `.git/` directory
- Files in `.gitignore`

### File Size Limits
- Max file size: 500KB (configurable in `.env`)
- Large files are automatically chunked
- Chunk size: 200 lines (configurable)

## 🤖 AI Assistant Integration

### ChatGPT Plus (Custom GPT)

See `/custom-gpt/` directory for setup instructions:
1. Create a new Custom GPT
2. Upload the OpenAPI spec
3. Add custom instructions
4. Use Actions to query Supermemory

### Claude Desktop (MCP Server)

See `/mcp-server/` directory for setup instructions:
1. Install and run the MCP server
2. Configure in Claude Desktop settings
3. Claude can now search your codebase

## 📊 Usage Limits (Free Tier)

Supermemory free tier includes:
- **1M tokens/month**: ~750 files of average size
- **10K searches/month**: More than enough for daily use
- Resets monthly

## 🔐 Security

- API key stored in `.env` (not committed)
- `.env` is in `.gitignore`
- Only source code uploaded (no secrets or credentials)
- Data stored on Supermemory servers

## 🐛 Troubleshooting

### "API Key not set" Error

```bash
# Make sure .env exists and contains your key
cat .env
# Should show: SUPERMEMORY_API_KEY=sm_xxxxx
```

### Git Hook Not Running

```bash
# Check if hook exists and is executable
ls -la ../.git/hooks/post-commit

# Reinstall if needed
npm run install-hooks
```

### No Search Results

- Make sure initial sync completed: `npm run sync`
- Check Supermemory dashboard for uploaded memories
- Try broader search terms

### Files Not Syncing

Check file patterns in `sync-codebase.js`:
- File may be in `.gitignore`
- File may exceed size limit (500KB default)
- File extension may not be in `INCLUDE_PATTERNS`

## 💡 Tips

1. **Initial Sync**: Run once when setting up
2. **Git Hooks**: Commit normally, changes auto-sync
3. **Search**: Use natural language queries
4. **Context**: Mention recent commits when asking AI for help
5. **Updates**: Re-run sync if you want to force update all files

## 📚 Example Queries for AI

Once integrated with ChatGPT/Claude:

- "What's the architecture of the physics engine?"
- "Show me how aircraft spawning works"
- "What was the last commit about?"
- "Where is the radar display component?"
- "How does the database integration work?"
- "What recent bugs were fixed?"

## 🔄 Updates

To update all files in Supermemory:
```bash
npm run sync
```

This will re-upload everything with latest changes.

## 📖 Learn More

- [Supermemory Docs](https://docs.supermemory.ai)
- [Custom GPT Setup](/custom-gpt/README.md)
- [MCP Server Setup](/mcp-server/README.md)

## ✅ Checklist

- [ ] Install dependencies (`npm install`)
- [ ] Configure API key in `.env`
- [ ] Run initial sync (`npm run sync`)
- [ ] Install git hooks (`npm run install-hooks`)
- [ ] Test queries (`npm run query`)
- [ ] Set up Custom GPT (optional)
- [ ] Set up MCP server for Claude (optional)

---

**Need Help?** Check the troubleshooting section or run `npm run query` to test the integration.

