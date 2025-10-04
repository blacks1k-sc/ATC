import dynamic from 'next/dynamic';

// Tell Next.js: "Don't try to render this on the server, only in the browser!"
const GroundMapYYZ = dynamic(() => import('@/components/GroundMapYYZ'), {
  ssr: false, // This is the magic line that fixes it!
  loading: () => (
    <div style={{ 
      width: '100vw', 
      height: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      background: '#1a1a2e',
      color: '#00ff00',
      fontFamily: 'monospace'
    }}>
      Loading Ground Operations Map...
    </div>
  )
});

export default function GroundPage() {
  return <GroundMapYYZ airport="CYYZ" />;
}
