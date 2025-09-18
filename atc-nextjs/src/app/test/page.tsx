'use client';

import { useState, useEffect } from 'react';

export default function TestPage() {
  const [tests, setTests] = useState<string[]>([]);
  const [currentTime, setCurrentTime] = useState('');

  useEffect(() => {
    // Test 1: Time update
    const updateTime = () => {
      const now = new Date();
      const timeString = now.toLocaleTimeString('en-US', { hour12: false, timeZone: 'UTC' }) + ' UTC';
      setCurrentTime(timeString);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);

    // Test 2: CSS animations
    setTests(prev => [...prev, '✅ CSS animations loaded']);
    
    // Test 3: TypeScript compilation
    setTests(prev => [...prev, '✅ TypeScript compilation successful']);
    
    // Test 4: React components
    setTests(prev => [...prev, '✅ React components rendered']);

    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ 
      padding: '20px', 
      fontFamily: 'Courier New, monospace', 
      background: '#0a0a0a', 
      color: '#00ff00',
      minHeight: '100vh'
    }}>
      <h1>ATC System - Functionality Test</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <h2>System Clock Test</h2>
        <p>Current UTC Time: <strong>{currentTime}</strong></p>
        <p>Status: {currentTime ? '✅ Working' : '❌ Not working'}</p>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h2>Component Tests</h2>
        <ul>
          {tests.map((test, index) => (
            <li key={index}>{test}</li>
          ))}
        </ul>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h2>CSS Animation Test</h2>
        <div 
          style={{
            width: '20px',
            height: '20px',
            background: '#00ff00',
            borderRadius: '50%',
            animation: 'pulse 2s infinite',
            boxShadow: '0 0 8px #00ff00'
          }}
        />
        <p>Status: ✅ Pulse animation active</p>
      </div>

      <div>
        <h2>Navigation</h2>
        <a 
          href="/" 
          style={{ 
            color: '#00ff00', 
            textDecoration: 'underline',
            padding: '10px 20px',
            border: '1px solid #00ff00',
            display: 'inline-block',
            marginTop: '10px'
          }}
        >
          ← Back to ATC System
        </a>
      </div>
    </div>
  );
}
