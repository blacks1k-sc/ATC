# MCP Server for Claude Desktop

Model Context Protocol (MCP) server that integrates your ATC codebase with Claude Desktop via Supermemory.

## 🎯 What This Does

Adds these tools to Claude Desktop:
- **search_codebase**: Search your ATC codebase semantically
- **get_recent_changes**: View recent commits and changes
- **get_file_context**: Get details about specific files
- **search_by_language**: Search code by programming language

Claude can automatically invoke these tools to understand your codebase and help with development.

## 📋 Prerequisites

- Claude Desktop app (free or Pro)
- Supermemory integration set up and synced
- Node.js 18+
- Supermemory API key

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
cd mcp-server
npm install
```

### Step 2: Configure Environment

```bash
# Copy from parent directory or create new
cp ../supermemory-integration/.env .env

# Or create manually:
echo "SUPERMEMORY_API_KEY=your_api_key_here" > .env
echo "PROJECT_NAME=ATC-1" >> .env
```

### Step 3: Test the Server

```bash
npm start
```

You should see:
```
ATC Codebase MCP Server running on stdio
```

Press Ctrl+C to stop.

### Step 4: Configure Claude Desktop

#### macOS

Edit Claude Desktop config:
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

#### Windows

```bash
notepad %APPDATA%\Claude\claude_desktop_config.json
```

#### Linux

```bash
code ~/.config/Claude/claude_desktop_config.json
```

### Step 5: Add MCP Server Configuration

Add this to the config file:

```json
{
  "mcpServers": {
    "atc-codebase": {
      "command": "node",
      "args": [
        "/Users/nrup/ATC-1/mcp-server/server.js"
      ],
      "env": {
        "SUPERMEMORY_API_KEY": "your_api_key_here",
        "PROJECT_NAME": "ATC-1"
      }
    }
  }
}
```

**Important:** 
- Replace `/Users/nrup/ATC-1/` with your actual project path
- Replace `your_api_key_here` with your actual Supermemory API key
- Use absolute paths, not relative paths

If you already have other MCP servers, add the `atc-codebase` entry to the existing `mcpServers` object.

### Step 6: Restart Claude Desktop

1. Quit Claude Desktop completely
2. Reopen Claude Desktop
3. Look for the 🔌 icon in the bottom right
4. Click it to see available tools

You should see:
- search_codebase
- get_recent_changes
- get_file_context
- search_by_language

## 🧪 Testing in Claude

Try these prompts:

### Basic Search
```
Search my codebase for the physics engine implementation
```

Claude will automatically invoke `search_codebase` and show results.

### Recent Changes
```
What are the recent changes to the codebase?
```

Claude will call `get_recent_changes` and summarize commits.

### File Context
```
Show me details about the RadarDisplay.tsx component
```

Claude will use `get_file_context` with the file path.

### Language-Specific Search
```
Show me all the Python code related to aircraft kinematics
```

Claude will use `search_by_language` with language="python".

## 🛠️ Available Tools

### 1. search_codebase

Search the entire codebase semantically.

**Parameters:**
- `query` (required): Natural language search query
- `limit` (optional): Max results (default: 5)

**Example:**
```
Search for "how aircraft spawning works"
```

### 2. get_recent_changes

Get recent commits and changes.

**Parameters:**
- `limit` (optional): Number of commits (default: 10)

**Example:**
```
Show me the last 5 commits
```

### 3. get_file_context

Get information about a specific file.

**Parameters:**
- `file_path` (required): Relative file path

**Example:**
```
Get context for atc-brain-python/engine/core_engine.py
```

### 4. search_by_language

Search code by programming language.

**Parameters:**
- `language` (required): Language name (python, typescript, javascript, etc.)
- `query` (optional): Additional search terms
- `limit` (optional): Max results (default: 10)

**Example:**
```
Show me Python code related to Redis
```

## 💡 Usage Tips

### Let Claude Use Tools Automatically

Instead of:
```
Use the search_codebase tool to find...
```

Just ask naturally:
```
How does the radar display animation work?
```

Claude will automatically choose and invoke the right tool.

### Combine with Other Questions

```
I'm getting an error in the physics engine. Can you search the code and help me debug it?
```

Claude will:
1. Search for physics engine code
2. Review the implementation
3. Help diagnose the issue

### Ask for Recent Context

```
What have we been working on recently? Show me the last few commits and then help me continue that work.
```

Claude will:
1. Get recent changes
2. Understand the context
3. Suggest next steps

## 🔧 Configuration Options

### Change Server Name

In `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "my-custom-name": {  // Change this
      ...
    }
  }
}
```

### Adjust Search Limits

In `server.js`, modify the default values:
```javascript
limit: {
  type: 'number',
  default: 5,  // Change this
}
```

### Add More Tools

You can extend `server.js` to add custom tools:
```javascript
{
  name: 'my_custom_tool',
  description: 'Does something specific',
  inputSchema: { ... },
}
```

## 🐛 Troubleshooting

### Tools Not Showing in Claude

**Problem:** No 🔌 icon or tools not listed

**Fix:**
1. Check config file syntax (valid JSON)
2. Verify absolute paths are correct
3. Restart Claude Desktop completely
4. Check Claude Desktop logs

**View logs (macOS):**
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

### "API Key not set" Error

**Problem:** Server fails to start

**Fix:**
1. Check `.env` file exists
2. Verify API key is correct
3. Or set in `claude_desktop_config.json` env section

### "Supermemory not found" Error

**Problem:** No search results

**Fix:**
1. Run initial sync: `cd ../supermemory-integration && npm run sync`
2. Wait for sync to complete
3. Test with: `npm run query`

### Server Crashes

**Problem:** Tools fail with error

**Fix:**
1. Check Node.js version: `node --version` (need 18+)
2. Reinstall dependencies: `npm install`
3. Check Claude Desktop logs for details

### Tools Work But Return Empty

**Problem:** Tools execute but find nothing

**Fix:**
1. Verify Supermemory has data: `cd ../supermemory-integration && npm run query`
2. Re-run initial sync if needed
3. Check API key has access to correct account

## 🔄 Keeping Updated

The MCP server automatically uses the latest data because:
1. Git hooks sync every commit to Supermemory
2. MCP server queries Supermemory in real-time
3. No need to restart or reconfigure

Just keep committing and Claude knows about changes!

## 📊 Performance

- **Startup**: ~1 second
- **Search**: ~500ms per query
- **Memory**: ~50MB RAM
- **Network**: Only when tools are invoked

The server runs on-demand when Claude needs it and stops when idle.

## 🔐 Security

- Server runs locally on your machine
- Communicates with Claude Desktop via stdio
- API key stored in config file
- No external network access except Supermemory API

## 🎨 Advanced Usage

### Multiple Projects

You can run multiple MCP servers for different projects:

```json
{
  "mcpServers": {
    "atc-codebase": { ... },
    "other-project": {
      "command": "node",
      "args": ["/path/to/other-project/mcp-server/server.js"],
      "env": { ... }
    }
  }
}
```

### Custom Search Queries

Create shortcuts for common searches:

```javascript
// In server.js, add a new tool
{
  name: 'search_python_engine',
  description: 'Search Python physics engine code',
  inputSchema: {
    type: 'object',
    properties: {
      query: { type: 'string' }
    }
  }
}
```

## 📚 Learn More

- [MCP Documentation](https://modelcontextprotocol.io)
- [Claude Desktop](https://claude.ai/download)
- [Supermemory API](https://docs.supermemory.ai)

## ✅ Setup Checklist

- [ ] Dependencies installed (`npm install`)
- [ ] `.env` file configured with API key
- [ ] Server tested (`npm start`)
- [ ] Claude Desktop config updated
- [ ] Absolute paths verified
- [ ] Claude Desktop restarted
- [ ] Tools visible in Claude (🔌 icon)
- [ ] Test search successful

---

**Need Help?** 
1. Check Claude Desktop logs
2. Test Supermemory directly: `cd ../supermemory-integration && npm run query`
3. Verify config file syntax at [JSONLint](https://jsonlint.com)

## 🎉 You're All Set!

Now Claude Desktop can search and understand your entire ATC codebase. Just chat naturally and Claude will use the tools automatically.

**Example conversation:**
```
You: How does aircraft spawning work in the ATC system?
Claude: [Searches codebase]
      I found the aircraft spawning implementation. It's handled in...
      [Shows actual code and explains]

You: Great! How has this changed recently?
Claude: [Gets recent changes]
      Looking at recent commits, there were two changes to spawning...
      [Explains recent modifications]
```

