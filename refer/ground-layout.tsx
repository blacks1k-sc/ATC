export const metadata = { title: 'Ground Ops — YYZ' };

export default function GroundLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ margin: 0 }}>
      {children}
    </div>
  );
}
