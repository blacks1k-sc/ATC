#!/usr/bin/env node

import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

const API_KEY = process.env.SUPERMEMORY_API_KEY;
const API_BASE_URL = 'https://api.supermemory.ai/v3';
const PROJECT_NAME = process.env.PROJECT_NAME || 'ATC-1';

class CodebaseQuery {
  constructor() {
    if (!API_KEY || API_KEY === 'your_api_key_here') {
      console.error('Error: SUPERMEMORY_API_KEY not set');
      process.exit(1);
    }

    this.apiClient = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
      },
    });
  }

  async testQuery(query) {
    console.log(`Searching: "${query}"\n`);

    try {
      const response = await this.apiClient.post('/search', {
        q: query,
        limit: 5,
      });

      const results = response.data.results || [];

      if (!results || results.length === 0) {
        console.log('No results found');
        return;
      }

      console.log(`Found ${results.length} results:\n`);
      
      results.forEach((result, index) => {
        console.log(`${index + 1}. ${result.title || 'Untitled'} (score: ${result.score?.toFixed(2) || 'N/A'})`);
        
        // Show first chunk content if available
        if (result.chunks && result.chunks.length > 0) {
          const firstChunk = result.chunks[0];
          const content = firstChunk.content || '';
          const preview = content.substring(0, 200).replace(/\n/g, ' ');
          console.log(`   Preview: ${preview}...`);
        }
        
        console.log(`   Type: ${result.type || 'N/A'}`);
        console.log('');
      });

    } catch (error) {
      console.error('Search error:', error.response?.data?.message || error.message);
      if (error.response?.status === 404) {
        console.error('\nTip: Make sure you have run the initial sync first:');
        console.error('   npm run sync\n');
      }
      process.exit(1);
    }
  }

  async runTests() {
    console.log('Testing Supermemory Integration\n');
    console.log('='.repeat(60) + '\n');

    const testQueries = [
      'aircraft physics kinematics engine',
      'Next.js frontend components',
      'recent commits and changes',
      'database schema and PostgreSQL',
      'Python Redis event publishing',
    ];

    for (const query of testQueries) {
      await this.testQuery(query);
      console.log('─'.repeat(60) + '\n');
    }

    console.log('Test queries complete!\n');
    console.log('Your AI assistants can now search your codebase using these queries.\n');
  }
}

// Run tests
const query = new CodebaseQuery();
const customQuery = process.argv[2];

if (customQuery) {
  query.testQuery(customQuery).catch(error => {
    console.error('Fatal error:', error.message);
    process.exit(1);
  });
} else {
  query.runTests().catch(error => {
    console.error('Fatal error:', error.message);
    process.exit(1);
  });
}
