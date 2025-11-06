#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

const API_KEY = process.env.SUPERMEMORY_API_KEY;
const API_BASE_URL = 'https://api.supermemory.ai/v3';
const PROJECT_NAME = process.env.PROJECT_NAME || 'ATC-1';

if (!API_KEY || API_KEY === 'your_api_key_here') {
  console.error('Error: SUPERMEMORY_API_KEY not set in .env file');
  process.exit(1);
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json',
  },
});

// Create MCP server
const server = new Server(
  {
    name: 'atc-codebase-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Define available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'search_codebase',
        description: 'Search the ATC-1 codebase semantically. Use natural language queries to find relevant code, documentation, or recent changes.',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'Natural language search query (e.g., "How does the physics engine work?")',
            },
            limit: {
              type: 'number',
              description: 'Maximum number of results to return (default: 5)',
              default: 5,
            },
          },
          required: ['query'],
        },
      },
      {
        name: 'get_recent_changes',
        description: 'Get recent commits and changes to the codebase. Search for recent development activity, bug fixes, or feature additions.',
        inputSchema: {
          type: 'object',
          properties: {
            limit: {
              type: 'number',
              description: 'Number of recent commits to retrieve (default: 10)',
              default: 10,
            },
          },
        },
      },
      {
        name: 'get_file_context',
        description: 'Get context about a specific file or component. Searches for all mentions and usage of a file.',
        inputSchema: {
          type: 'object',
          properties: {
            file_path: {
              type: 'string',
              description: 'Relative path to the file (e.g., "atc-nextjs/src/components/RadarDisplay.tsx")',
            },
          },
          required: ['file_path'],
        },
      },
      {
        name: 'search_by_language',
        description: 'Search code by programming language. Find all Python, TypeScript, or other language-specific code.',
        inputSchema: {
          type: 'object',
          properties: {
            language: {
              type: 'string',
              description: 'Programming language (e.g., "python", "typescript", "javascript")',
            },
            query: {
              type: 'string',
              description: 'Optional search query within that language',
            },
            limit: {
              type: 'number',
              description: 'Maximum results (default: 10)',
              default: 10,
            },
          },
          required: ['language'],
        },
      },
    ],
  };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'search_codebase': {
        const { query, limit = 5 } = args;
        
        const response = await apiClient.post('/search', {
          q: query,
          limit,
        });

        const results = response.data.results || [];

        if (!results || results.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: `No results found for query: "${query}"`,
              },
            ],
          };
        }

        const formattedResults = results.map((result, index) => {
          let metadata = {};
          try {
            metadata = JSON.parse(result.metadata || '{}');
          } catch (e) {
            // Ignore parse errors
          }

          const filePath = metadata.file_path || 'Unknown';
          const language = metadata.language || 'Unknown';
          const type = metadata.type || 'Unknown';
          const score = result.score?.toFixed(2) || 'N/A';

          return `
${index + 1}. ${filePath} (${language})
   Type: ${type}
   Relevance: ${score}
   
${result.content.substring(0, 500)}
${result.content.length > 500 ? '...\n[Content truncated]' : ''}
${'─'.repeat(80)}`;
        }).join('\n\n');

        return {
          content: [
            {
              type: 'text',
              text: `Found ${results.length} results for "${query}":\n\n${formattedResults}`,
            },
          ],
        };
      }

      case 'get_recent_changes': {
        const { limit = 10 } = args;
        
        const response = await apiClient.post('/search', {
          q: 'type:git_commit recent commits changes',
          limit,
        });

        const results = response.data.results || [];

        if (!results || results.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: 'No recent commits found. Make sure git hooks are installed and commits have been tracked.',
              },
            ],
          };
        }

        const commits = results.map((result, index) => {
          let metadata = {};
          try {
            metadata = JSON.parse(result.metadata || '{}');
          } catch (e) {
            // Ignore parse errors
          }

          return `
${index + 1}. Commit ${metadata.commit_hash?.substring(0, 7) || 'Unknown'}
   Author: ${metadata.author || 'Unknown'}
   Date: ${metadata.date ? new Date(metadata.date).toLocaleString() : 'Unknown'}
   Files: ${metadata.files_changed || 0} (+${metadata.insertions || 0}/-${metadata.deletions || 0})

${result.content.substring(0, 400)}
${result.content.length > 400 ? '...\n[Content truncated]' : ''}
${'─'.repeat(80)}`;
        }).join('\n\n');

        return {
          content: [
            {
              type: 'text',
              text: `Recent commits:\n\n${commits}`,
            },
          ],
        };
      }

      case 'get_file_context': {
        const { file_path } = args;
        
        const response = await apiClient.post('/search', {
          q: `file:${file_path} OR path:${file_path}`,
          limit: 3,
        });

        const results = response.data.results || [];

        if (!results || results.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: `No information found for file: ${file_path}`,
              },
            ],
          };
        }

        const fileInfo = results.map((result, index) => {
          let metadata = {};
          try {
            metadata = JSON.parse(result.metadata || '{}');
          } catch (e) {
            // Ignore parse errors
          }

          return `
${index + 1}. ${metadata.file_path || file_path}
   Language: ${metadata.language || 'Unknown'}
   Last Modified: ${metadata.last_modified ? new Date(metadata.last_modified).toLocaleString() : 'Unknown'}
   Lines: ${metadata.lines || 'N/A'}

${result.content}
${'─'.repeat(80)}`;
        }).join('\n\n');

        return {
          content: [
            {
              type: 'text',
              text: `Context for ${file_path}:\n\n${fileInfo}`,
            },
          ],
        };
      }

      case 'search_by_language': {
        const { language, query, limit = 10 } = args;
        
        const searchQuery = query 
          ? `language:${language} ${query}`
          : `language:${language}`;
        
        const response = await apiClient.post('/search', {
          q: searchQuery,
          limit,
        });

        const results = response.data.results || [];

        if (!results || results.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: `No ${language} files found.`,
              },
            ],
          };
        }

        const files = results.map((result, index) => {
          let metadata = {};
          try {
            metadata = JSON.parse(result.metadata || '{}');
          } catch (e) {
            // Ignore parse errors
          }

          return `
${index + 1}. ${metadata.file_path || 'Unknown'}
   
${result.content.substring(0, 400)}
${result.content.length > 400 ? '...\n[Content truncated]' : ''}
${'─'.repeat(80)}`;
        }).join('\n\n');

        return {
          content: [
            {
              type: 'text',
              text: `${language} files${query ? ` matching "${query}"` : ''}:\n\n${files}`,
            },
          ],
        };
      }

      default:
        return {
          content: [
            {
              type: 'text',
              text: `Unknown tool: ${name}`,
            },
          ],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error executing ${name}: ${error.response?.data?.message || error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('ATC Codebase MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
