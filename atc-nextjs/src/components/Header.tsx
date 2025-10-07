'use client';

import Link from 'next/link';
import { SystemStatus } from '@/types/atc';

interface HeaderProps {
  systemStatus: SystemStatus;
  currentTime: string;
  onTabChange: (tabId: string) => void;
}

export default function Header({ systemStatus, currentTime, onTabChange }: HeaderProps) {
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
          {/* Navigation moved to ControlButtons component */}
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
