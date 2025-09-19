export const metadata = { title: 'Ground Ops — YYZ' };

export default function GroundLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0 }}>{children}</body>
    </html>
  );
}