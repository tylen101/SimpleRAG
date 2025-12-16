'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';
import { useAuth } from './context/AuthContext';

export default function Home() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [loading, isAuthenticated, router]);

  if (loading) {
    return <div className={styles.page}>Loading...</div>;
  }

  if (!loading && !isAuthenticated) {
    router.replace('/login');
    return (
      <div>
        <h1>Login Required</h1>
      </div>
    );
  }

  return (
    <main className={styles.page}>
      <h1>RAGsearch</h1>
    </main>
  );
}
