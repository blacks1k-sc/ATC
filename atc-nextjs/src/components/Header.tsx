'use client';

import { useState, useEffect } from 'react';
import { ControllerTab, SystemStatus } from '@/types/atc';

interface HeaderProps {
  systemStatus: SystemStatus;
  currentTime: string;
  onTabChange: (tabId: string) => void;
}

export default function Header({ systemStatus, currentTime, onTabChange }: HeaderProps) {
  const [tabs, setTabs] = useState<ControllerTab[]>([
    { id: 'tower', name: 'TOWER', active: true },
    { id: 'ground', name: 'GROUND', active: false },
    { id: 'approach', name: 'APPROACH', active: false },
    { id: 'center', name: 'CENTER', active: false },
    { id: 'coordinator', name: 'COORD', active: false },
  ]);

  const handleTabClick = (tabId: string) => {
    setTabs(tabs.map(tab => ({
      ...tab,
      active: tab.id === tabId
    })));
    onTabChange(tabId);
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'active': return 'active';
      case 'warning': return 'warning';
      case 'emergency': return 'emergency';
      default: return 'active';
    }
  };

  return (
    <div className="main-header">
      <div>
        <h1>AI ATC OPERATIONS CENTER - LAX</h1>
        <div className="controller-tabs">
          {tabs.map(tab => (
            <div
              key={tab.id}
              className={`tab ${tab.active ? 'active' : ''}`}
              onClick={() => handleTabClick(tab.id)}
            >
              {tab.name}
            </div>
          ))}
        </div>
      </div>
      <div className="system-status">
        <div className="status-indicator">
          <div className={`status-light ${getStatusClass(systemStatus.towerAI)}`}></div>
          <span>TOWER AI</span>
        </div>
        <div className="status-indicator">
          <div className={`status-light ${getStatusClass(systemStatus.groundAI)}`}></div>
          <span>GROUND AI</span>
        </div>
        <div className="status-indicator">
          <div className={`status-light ${getStatusClass(systemStatus.weather)}`}></div>
          <span>WEATHER</span>
        </div>
        <div className="status-indicator">
          <div className={`status-light ${getStatusClass(systemStatus.emergency)}`}></div>
          <span>EMERGENCY</span>
        </div>
        <span style={{ marginLeft: '20px' }}>{currentTime}</span>
      </div>
    </div>
  );
}
