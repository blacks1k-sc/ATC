import dynamic from 'next/dynamic';

// Dynamically import the map component to avoid SSR issues
const GroundMapYYZ = dynamic(() => import('@/components/GroundMapYYZ'), {
  ssr: false,
  loading: () => <div style={{ 
    width: '100vw', 
    height: '100vh', 
    display: 'flex', 
    alignItems: 'center', 
    justifyContent: 'center',
    background: '#1a1a2e',
    color: '#00ff00',
    fontFamily: 'monospace'
  }}>Loading Ground Operations Map...</div>
});

export const metadata = { title: 'Ground Ops — YYZ' };

export default function GroundPage() {
  return <GroundMapYYZ airport="CYYZ" />;
}
