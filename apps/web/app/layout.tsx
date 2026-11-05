import type { Metadata } from 'next';
import './style.css';
export const metadata: Metadata = {title:'Commonplace | Conversations',description:'A local messaging workspace'};
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html>; }
