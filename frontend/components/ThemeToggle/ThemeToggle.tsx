'use client';
import styles from './ThemeToggle.module.css';
import Image from 'next/image';
import dark from '../../public/darkMode.svg';
import light from '../../public/lightMode.svg';
import { useTheme } from '@/hooks/useTheme';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  if (!theme) return null;

  return (
    <button
      className={styles.container}
      onClick={toggleTheme}
      aria-label="Toggle theme"
    >
      <Image
        src={theme === 'light' ? light : dark}
        alt="theme toggle"
        height={24}
        width={24}
        className={styles.toggleButton}
      />
    </button>
  );
}
