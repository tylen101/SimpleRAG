'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import styles from './DashboardPage.module.css';
import { useAuth } from '@/app/context/AuthContext';

export default function DashboardPage() {
  const { user, logout, isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [loading, isAuthenticated, router]);

  if (loading) return <p className={styles.loading}>Loading...</p>;
  if (!isAuthenticated) return null;


  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>
          Welcome, {user?.display_name || 'User'}!
        </h1>
        <button className={styles.logout} onClick={logout}>
          Logout
        </button>
      </header>
    </main>
  );
}
