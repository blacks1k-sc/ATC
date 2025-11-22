#!/usr/bin/env node

import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import ignore from 'ignore';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config();

// Configuration
const API_KEY = process.env.SUPERMEMORY_API_KEY;
const API_BASE_URL = 'https://api.supermemory.ai/v3';
const PROJECT_ROOT = path.resolve(__dirname, process.env.PROJECT_ROOT || '..');
const PROJECT_NAME = process.env.PROJECT_NAME || 'ATC-1';
const MAX_FILE_SIZE_KB = parseInt(process.env.MAX_FILE_SIZE_KB || '500');
const CHUNK_SIZE_LINES = parseInt(process.env.CHUNK_SIZE_LINES || '200');

// File patterns to include
const INCLUDE_PATTERNS = [
  '**/*.js',
  '**/*.ts',
  '**/*.tsx',
  '**/*.jsx',
  '**/*.py',
  '**/*.json',
  '**/*.md',
  '**/*.sql',
  '**/*.sh',
  '**/*.yaml',
  '**/*.yml',
  '**/*.css',
];

// Additional patterns to ignore beyond .gitignore
const ADDITIONAL_IGNORE = [
  'node_modules/**',
  '**/node_modules/**',
  'venv/**',
  '**/venv/**',
  '__pycache__/**',
  '**/__pycache__/**',
  '.git/**',
  '**/dist/**',
  '**/build/**',
  '**/*.log',
  '**/logs/**',
  '**/telemetry/**',
  '**/cache/**',
  '**/.next/**',
  '**/tsconfig.tsbuildinfo',
  '**/*.pyc',
  '.env',
  '.env.*',
];

class CodebaseSync {
  constructor() {
    if (!API_KEY || API_KEY === 'your_api_key_here') {
      console.error('Error: SUPERMEMORY_API_KEY not set in .env file');
      console.error('Please copy .env.example to .env and add your API key');
      process.exit(1);
    }

    this.apiClient = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
      },
    });

    this.ig = ignore();
    this.stats = {
      filesProcessed: 0,
      memoriesCreated: 0,
      bytesProcessed: 0,
      errors: 0,
    };
  }

  async initialize() {
    // Load .gitignore patterns
    const gitignorePath = path.join(PROJECT_ROOT, '.gitignore');
    if (fs.existsSync(gitignorePath)) {
      const gitignoreContent = fs.readFileSync(gitignorePath, 'utf8');
      this.ig.add(gitignoreContent);
    }

    // Add additional ignore patterns
    this.ig.add(ADDITIONAL_IGNORE);

    console.log('Starting codebase sync to Supermemory...');
    console.log(`Project: ${PROJECT_NAME}`);
    console.log(`Root: ${PROJECT_ROOT}`);
    console.log('');
  }

  shouldProcessFile(filePath) {
    const relativePath = path.relative(PROJECT_ROOT, filePath);
    
    // Check if ignored
    if (this.ig.ignores(relativePath)) {
      return false;
    }

    // Check file size
    const stats = fs.statSync(filePath);
    if (stats.size > MAX_FILE_SIZE_KB * 1024) {
      console.log(`Skipping large file: ${relativePath} (${Math.round(stats.size / 1024)}KB)`);
      return false;
    }

    return true;
  }

  detectLanguage(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const langMap = {
      '.js': 'javascript',
      '.jsx': 'javascript',
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.py': 'python',
      '.json': 'json',
      '.md': 'markdown',
      '.sql': 'sql',
      '.sh': 'bash',
      '.yaml': 'yaml',
      '.yml': 'yaml',
      '.css': 'css',
    };
    return langMap[ext] || 'plaintext';
  }

  chunkFile(content, filePath) {
    const lines = content.split('\n');
    const chunks = [];

    if (lines.length <= CHUNK_SIZE_LINES) {
      return [{ content, startLine: 1, endLine: lines.length }];
    }

    for (let i = 0; i < lines.length; i += CHUNK_SIZE_LINES) {
      const chunkLines = lines.slice(i, i + CHUNK_SIZE_LINES);
      chunks.push({
        content: chunkLines.join('\n'),
        startLine: i + 1,
        endLine: Math.min(i + CHUNK_SIZE_LINES, lines.length),
      });
    }

    return chunks;
  }

  async syncFile(filePath) {
    try {
      const relativePath = path.relative(PROJECT_ROOT, filePath);
      const content = fs.readFileSync(filePath, 'utf8');
      const language = this.detectLanguage(filePath);
      const stats = fs.statSync(filePath);
      const chunks = this.chunkFile(content, filePath);

      for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i];
        const isMultiChunk = chunks.length > 1;
        
        const memoryContent = isMultiChunk
          ? `File: ${relativePath} (Part ${i + 1}/${chunks.length}, Lines ${chunk.startLine}-${chunk.endLine})\n\n${chunk.content}`
          : `File: ${relativePath}\n\n${chunk.content}`;

        const metadata = {
          project: PROJECT_NAME,
          file_path: relativePath,
          language,
          type: 'source_code',
          last_modified: stats.mtime.toISOString(),
          chunk_index: isMultiChunk ? i + 1 : undefined,
          total_chunks: isMultiChunk ? chunks.length : undefined,
          lines: `${chunk.startLine}-${chunk.endLine}`,
        };

        const response = await this.apiClient.post('/memories', {
          content: memoryContent,
        });

        this.stats.memoriesCreated++;
      }

      this.stats.filesProcessed++;
      this.stats.bytesProcessed += stats.size;
      
      const chunkInfo = chunks.length > 1 ? ` (${chunks.length} chunks)` : '';
      console.log(`${relativePath}${chunkInfo}`);

    } catch (error) {
      this.stats.errors++;
      const errorMsg = error.response?.data?.error || error.response?.data?.message || error.message;
      const errorDetails = error.response?.data ? JSON.stringify(error.response.data) : '';
      console.error(`Error processing ${filePath}:`, errorMsg);
      if (errorDetails && this.stats.errors === 1) {
        console.error(`   Details: ${errorDetails}`);
      }
    }
  }

  async syncAll() {
    await this.initialize();

    // Find all matching files
    const files = await glob(INCLUDE_PATTERNS, {
      cwd: PROJECT_ROOT,
      absolute: true,
      nodir: true,
    });

    console.log(`Found ${files.length} files matching patterns\n`);

    // Filter and process files
    const filesToProcess = files.filter(f => this.shouldProcessFile(f));
    console.log(`Processing ${filesToProcess.length} files...\n`);

    for (const file of filesToProcess) {
      await this.syncFile(file);
    }

    // Print summary
    console.log('\n' + '='.repeat(60));
    console.log('Sync complete!');
    console.log('='.repeat(60));
    console.log(`Files processed: ${this.stats.filesProcessed}`);
    console.log(`Memories created: ${this.stats.memoriesCreated}`);
    console.log(`Data processed: ${Math.round(this.stats.bytesProcessed / 1024)}KB`);
    console.log(`Errors: ${this.stats.errors}`);
    console.log('='.repeat(60));
    console.log('\nYour codebase is now synced to Supermemory!');
    console.log('   You can now query it from ChatGPT or Claude.\n');
  }
}

// Run sync
const sync = new CodebaseSync();
sync.syncAll().catch(error => {
  console.error('Fatal error:', error.message);
  process.exit(1);
});
