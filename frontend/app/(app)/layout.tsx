'use client';
import styles from './AppLayout.module.css';
import { useRouter } from 'next/navigation';
import { useAuth } from '../context/AuthContext';

import VerticalNav from '@/components/Navbar/VerticalNav/VerticalNav';
import HorizontalNav from '@/components/Navbar/HorizontalNav/HorizontalNav';
import useWindowWidth from '@/hooks/useWindowWidth';
import MobileNav from '@/components/Navbar/MobileNav/MobileNav';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const width = useWindowWidth();

  if (loading) return null;

  if (!isAuthenticated) {
    router.replace('/login');
    return null;
  }

  return (
    <div className={styles.layout}>
      {width >= 600 && <VerticalNav />}

      <main className={styles.mainContent}>
        <HorizontalNav />
        {children}
        {width < 600 && <MobileNav />}
      </main>
    </div>
  );
}
