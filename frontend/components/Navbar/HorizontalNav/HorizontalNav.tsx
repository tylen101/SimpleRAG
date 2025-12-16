import React from 'react';
import styles from './HorizontalNav.module.css';
import ThemeToggle from '@/components/ThemeToggle/ThemeToggle';

export default function HorizontalNav() {
  return (
    <nav className={styles.navbar}>
      <ThemeToggle />
    </nav>
  );
}
