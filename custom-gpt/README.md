# Custom GPT Setup for ATC Codebase Assistant

Set up a Custom GPT in ChatGPT Plus that can search and understand your ATC codebase via Supermemory.

## 🎯 What You'll Get

A ChatGPT assistant that can:
- Search your entire ATC codebase semantically
- Understand recent changes and commits
- Reference actual code when helping you
- Debug issues with full project context
- Plan features based on existing architecture

## 📋 Prerequisites

- ChatGPT Plus subscription ($20/month)
- Supermemory integration set up (`/supermemory-integration/`)
- Initial codebase sync completed
- Supermemory API key

## 🚀 Setup Steps

### Step 1: Create the Custom GPT

1. Go to ChatGPT: https://chat.openai.com
2. Click **Explore GPTs** (left sidebar)
3. Click **Create** (top right)
4. Switch to **Configure** tab

### Step 2: Basic Configuration

**Name:**
```
ATC Codebase Assistant
```

**Description:**
```
Expert assistant for the ATC-1 simulation system with full codebase access via Supermemory. Search code, understand architecture, debug issues, and plan features.
```

**Instructions:**
Copy the entire content from `instructions.md` and paste it into the Instructions field.

### Step 3: Add Conversation Starters

Add these 4 conversation starters:

1. `What's the current architecture of the ATC system?`
2. `Show me how the physics engine works`
3. `What were the most recent changes to the codebase?`
4. `How does the radar display component work?`

### Step 4: Upload Knowledge Files (Optional)

Upload these key documentation files:

- Go back to `/Users/nrup/ATC-1/`
- Upload: `README.md`
- Upload: `atc-nextjs/README.md`
- Upload: `atc-brain-python/README.md`
- Upload: `claude-learn.md`

This gives the GPT additional context about your project.

### Step 5: Configure Actions

1. Scroll down to **Actions**
2. Click **Create new action**
3. Click **Import from URL** OR paste the schema

**Import from URL:**
If you host the `openapi-spec.yaml` file online, use that URL.

**Or paste directly:**
Copy the entire content of `openapi-spec.yaml` and paste it.

### Step 6: Add Authentication

After importing the schema:

1. Authentication type: **API Key**
2. Auth Type: **Bearer**
3. API Key: Get from https://supermemory.ai/dashboard
4. Paste your key (starts with `sm_`)

### Step 7: Set Capabilities

Enable these:
- ✅ Web Browsing: No (not needed)
- ✅ DALL·E Image Generation: No
- ✅ Code Interpreter: Yes (helpful for analysis)

### Step 8: Test the GPT

1. Click **Save** (top right)
2. Choose visibility (Only me / Anyone with link)
3. Click **Confirm**

**Test with:**
```
Search for the physics engine implementation
```

The GPT should use the `searchCodebase` action and return results from your actual codebase.

## 🧪 Testing Queries

Try these to verify it's working:

### Architecture Questions
```
What's the overall architecture of the ATC system?
```

### Code Search
```
Show me the aircraft kinematics calculations
```

### Recent Changes
```
What were the last commits about?
```

### Debugging Help
```
I'm getting an error in the radar display. Can you find the relevant code?
```

### Feature Planning
```
How should I add a new aircraft property to the system?
```

## 📊 Expected Behavior

**Good Response:**
```
I searched your codebase for "physics engine" and found:

1. core_engine.py - Main 1 Hz tick loop orchestrator
   Located at: atc-brain-python/engine/core_engine.py
   This handles...

2. kinematics.py - Physics formulas for aircraft motion
   Located at: atc-brain-python/engine/kinematics.py
   The formulas include...

[Actual code snippets from your files]
```

**Bad Response** (means it's not working):
```
Based on typical ATC systems... [generic answer]
```

If you get generic answers, the action isn't working. Check:
- API key is correct
- Supermemory sync completed
- Actions are properly configured

## 🎨 Customization

### Change Search Limits

In the OpenAPI spec, adjust:
```yaml
limit:
  type: integer
  default: 5  # Change this
  maximum: 20  # Or this
```

### Add More Actions

You can add more Supermemory endpoints:
- List recent memories
- Filter by file type
- Search within date ranges

### Adjust Instructions

Modify `instructions.md` to:
- Focus on specific areas (frontend vs backend)
- Add project-specific conventions
- Include team member names/roles

## 🔐 Privacy & Security

- Only you can access your Custom GPT (unless you share the link)
- API key is stored securely by OpenAI
- Conversations stay within ChatGPT
- Supermemory data is on their servers

## 💡 Usage Tips

1. **Be specific**: "Show me the radar display component" vs "how does display work"
2. **Reference files**: "Check RadarDisplay.tsx for the animation logic"
3. **Mention recent work**: "We just added airspace sectors, how do they work?"
4. **Ask for comparisons**: "Compare the Python engine to the TypeScript frontend"
5. **Debug with context**: "The distance calculation is wrong, find the geo_utils code"

## 🔄 Keeping It Updated

The GPT automatically stays updated because:
1. Git hooks sync every commit to Supermemory
2. Supermemory search returns latest data
3. No need to re-upload or reconfigure

Just keep committing and the GPT knows about changes!

## 🐛 Troubleshooting

### GPT Not Using the Action

**Problem:** GPT gives generic answers without searching

**Fix:**
1. Check Actions are enabled in GPT settings
2. Verify API key is correct
3. Test Supermemory directly: `cd ../supermemory-integration && npm run query`
4. Make sure instructions mention using searchCodebase

### Authentication Errors

**Problem:** "API authentication failed"

**Fix:**
1. Get new API key from Supermemory dashboard
2. Update in Custom GPT Actions settings
3. Make sure it's Bearer token format

### No Search Results

**Problem:** Action works but returns empty

**Fix:**
1. Run initial sync: `cd ../supermemory-integration && npm run sync`
2. Check Supermemory dashboard for uploaded memories
3. Try broader search terms

### Action Not Available

**Problem:** GPT says "I don't have access to that action"

**Fix:**
1. Re-import the OpenAPI spec
2. Save the GPT again
3. Test in a new conversation

## 📚 Learn More

- [OpenAI Custom GPTs Guide](https://help.openai.com/en/articles/8554397-creating-a-gpt)
- [Custom GPT Actions Documentation](https://platform.openai.com/docs/actions)
- [Supermemory API Docs](https://docs.supermemory.ai)

## ✅ Setup Checklist

- [ ] ChatGPT Plus subscription active
- [ ] Custom GPT created
- [ ] Instructions added
- [ ] OpenAPI spec imported
- [ ] API key configured
- [ ] Conversation starters added
- [ ] Knowledge files uploaded (optional)
- [ ] Tested with sample queries
- [ ] Getting actual codebase results

---

**Need Help?** Make sure your Supermemory integration is working first by running `npm run query` in the `supermemory-integration` directory.

