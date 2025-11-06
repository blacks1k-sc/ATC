# Quick Start: AI Assistant Integration

Get ChatGPT Plus and Claude Desktop connected to your ATC codebase in 15 minutes.

## 🎯 What You'll Get

- ChatGPT and Claude can search your entire codebase
- AI knows about recent commits and changes
- Automatic updates via git hooks
- 100% free using Supermemory (1M tokens/month)

## 🚀 5-Step Setup

### Step 1: Install Supermemory Integration (2 min)

```bash
cd supermemory-integration
npm install
cp .env.example .env
```

Edit `.env` and add your Supermemory API key from https://supermemory.ai/dashboard

### Step 2: Sync Your Codebase (5 min)

```bash
npm run sync
```

This uploads all your source code to Supermemory. Wait for it to complete.

### Step 3: Enable Auto-Tracking (30 seconds)

```bash
npm run install-hooks
```

Now every git commit will automatically sync to Supermemory.

### Step 4: Test It (1 min)

```bash
npm run query
```

You should see search results from your actual codebase.

### Step 5: Connect Your AI Assistant (5-10 min)

Choose one or both:

**For ChatGPT Plus:**
1. Go to ChatGPT → Explore GPTs → Create
2. Follow instructions in `/custom-gpt/README.md`
3. Takes ~5 minutes

**For Claude Desktop:**
1. Install dependencies: `cd ../mcp-server && npm install`
2. Follow instructions in `/mcp-server/README.md`
3. Takes ~10 minutes

## ✅ You're Done!

Now just ask your AI assistant:

```
Search my codebase for the physics engine implementation
```

or

```
What were the recent changes to the radar display?
```

## 📚 Full Documentation

- **Complete Guide**: [AI-ASSISTANT-SETUP.md](AI-ASSISTANT-SETUP.md)
- **Supermemory Integration**: [supermemory-integration/README.md](supermemory-integration/README.md)
- **ChatGPT Setup**: [custom-gpt/README.md](custom-gpt/README.md)
- **Claude Setup**: [mcp-server/README.md](mcp-server/README.md)

## 🐛 Troubleshooting

**"API Key not set" error:**
```bash
cd supermemory-integration
cat .env  # Make sure API key is there
```

**No search results:**
```bash
npm run sync  # Re-run sync
npm run query # Test again
```

**Git hook not working:**
```bash
npm run install-hooks  # Reinstall
git commit --allow-empty -m "Test"  # Test it
```

## 💡 Daily Usage

Just commit normally:
```bash
git commit -m "Fixed bug in radar display"
```

The git hook automatically syncs the change. Then ask ChatGPT or Claude about it!

---

**Need help?** See the full documentation in [AI-ASSISTANT-SETUP.md](AI-ASSISTANT-SETUP.md)

