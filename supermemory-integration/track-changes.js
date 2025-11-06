#!/usr/bin/env node

import axios from 'axios';
import simpleGit from 'simple-git';
import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config();

const API_KEY = process.env.SUPERMEMORY_API_KEY;
const API_BASE_URL = 'https://api.supermemory.ai/v3';
const PROJECT_ROOT = path.resolve(__dirname, process.env.PROJECT_ROOT || '..');
const PROJECT_NAME = process.env.PROJECT_NAME || 'ATC-1';

class ChangeTracker {
  constructor() {
    if (!API_KEY || API_KEY === 'your_api_key_here') {
      console.error('❌ Error: SUPERMEMORY_API_KEY not set');
      process.exit(1);
    }

    this.apiClient = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
      },
    });

    this.git = simpleGit(PROJECT_ROOT);
  }

  async getLastCommit() {
    try {
      const log = await this.git.log({ maxCount: 1 });
      return log.latest;
    } catch (error) {
      console.error('❌ Error getting git log:', error.message);
      return null;
    }
  }

  async getCommitDiff() {
    try {
      // Get diff of last commit
      const diff = await this.git.diff(['HEAD~1', 'HEAD']);
      return diff;
    } catch (error) {
      console.error('❌ Error getting diff:', error.message);
      return '';
    }
  }

  async getChangedFiles() {
    try {
      const diff = await this.git.diffSummary(['HEAD~1', 'HEAD']);
      return diff.files.map(f => ({
        path: f.file,
        insertions: f.insertions,
        deletions: f.deletions,
        changes: f.changes,
      }));
    } catch (error) {
      console.error('❌ Error getting changed files:', error.message);
      return [];
    }
  }

  generateSemanticSummary(commit, changedFiles, diff) {
    // Create a semantic summary of what changed
    const fileList = changedFiles.map(f => {
      const change = f.insertions + f.deletions;
      return `  - ${f.path} (+${f.insertions}/-${f.deletions})`;
    }).join('\n');

    // Extract key changes from diff (simplified)
    const addedLines = diff.split('\n').filter(l => l.startsWith('+')).length;
    const deletedLines = diff.split('\n').filter(l => l.startsWith('-')).length;

    return `
Commit: ${commit.hash.substring(0, 7)}
Author: ${commit.author_name}
Date: ${commit.date}
Message: ${commit.message}

Files Changed (${changedFiles.length}):
${fileList}

Summary:
- ${addedLines} lines added
- ${deletedLines} lines removed
- ${changedFiles.length} files modified

Context:
This commit was made to the ${PROJECT_NAME} codebase. The changes include modifications to the following components:
${changedFiles.map(f => `- ${f.path}`).join('\n')}

Commit Message Context:
${commit.message}

This change can help understand:
- Recent bug fixes or features added
- Code modifications and their rationale
- Evolution of specific files or components
`.trim();
  }

  async trackLastCommit() {
    console.log('🔍 Tracking latest commit...\n');

    const commit = await this.getLastCommit();
    if (!commit) {
      console.log('⚠️  No commits found');
      return;
    }

    const changedFiles = await this.getChangedFiles();
    if (changedFiles.length === 0) {
      console.log('⚠️  No file changes detected');
      return;
    }

    const diff = await this.getCommitDiff();
    const summary = this.generateSemanticSummary(commit, changedFiles, diff);

    try {
      // Upload to Supermemory
      await this.apiClient.post('/memories', {
        content: summary,
        metadata: JSON.stringify({
          project: PROJECT_NAME,
          type: 'git_commit',
          commit_hash: commit.hash,
          author: commit.author_name,
          date: commit.date,
          files_changed: changedFiles.length,
          insertions: changedFiles.reduce((sum, f) => sum + f.insertions, 0),
          deletions: changedFiles.reduce((sum, f) => sum + f.deletions, 0),
        }),
      });

      console.log('✅ Commit tracked successfully!');
      console.log(`📝 Commit: ${commit.hash.substring(0, 7)} - ${commit.message}`);
      console.log(`📂 Files changed: ${changedFiles.length}`);
      console.log('\n💡 This change is now available for AI assistants to query.\n');

    } catch (error) {
      console.error('❌ Error uploading to Supermemory:', error.response?.data?.message || error.message);
      process.exit(1);
    }
  }
}

// Run tracker
const tracker = new ChangeTracker();
tracker.trackLastCommit().catch(error => {
  console.error('❌ Fatal error:', error.message);
  process.exit(1);
});
