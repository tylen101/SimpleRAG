'use client';

import { FormEvent, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useRouter } from 'next/navigation';
import styles from './login.module.css';

export default function AuthPage() {
  const { login, register, error, isAuthenticated } = useAuth();
  const router = useRouter();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [isRegister, setIsRegister] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    try {
      if (isRegister) {
        await register(username, password);
      } else {
        await login(username, password);
      }

      // check if authentication succeeded
      if (isAuthenticated) {
        router.push('/dashboard');
      }
    } catch (error) {
      console.error('Auth failed:', error);
      if (typeof error === 'string') setErrorMessage(error);
      else if (error instanceof Error) setErrorMessage(error.message);
      else setErrorMessage('An unexpected error occurred');
    }
  };

  if (isAuthenticated) {
    router.push('/dashboard');
    return <div>Logging you in...</div>;
  }

  return (
    <main className={styles.main}>
      <div className={styles.sideBySide}>
        <div className={styles.welcomeInfo}>
          <h2>Welcome to the Enterprise Knowledge Search Platform</h2>

          <p>
            A secure, AI-powered retrieval system designed to help teams search,
            analyze, and interact with organizational documents using advanced
            semantic search and contextual reasoning.
          </p>

          <p>
            {isRegister ? (
              <>
                Get started by <strong>creating an account</strong> to securely
                access indexed documents, saved conversations, and
                organization-wide knowledge.
              </>
            ) : (
              <>
                Sign in to <strong>resume your workspace</strong> and continue
                exploring documents with context-aware AI assistance.
              </>
            )}
          </p>

          <ul className={styles.featuresList}>
            <li>Semantic and vector-based document search</li>
            <li>Context-aware AI responses grounded in your data</li>
            <li>Secure access with conversation and document history</li>
          </ul>
        </div>

        <div className={styles.card}>
          <h1 className={styles.title}>
            {isRegister ? 'Create Account' : 'Login'}
          </h1>
          <form onSubmit={handleSubmit}>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button type="submit">{isRegister ? 'Register' : 'Login'}</button>
          </form>
          <p className={styles.toggle}>
            {isRegister ? (
              <>
                Already have an account?{' '}
                <button type="button" onClick={() => setIsRegister(false)}>
                  Log in
                </button>
              </>
            ) : (
              <>
                Don’t have an account?{' '}
                <button type="button" onClick={() => setIsRegister(true)}>
                  Create one
                </button>
              </>
            )}
          </p>
          {(error || errorMessage) && (
            <p className={styles.error}>{error || errorMessage}</p>
          )}
        </div>
      </div>
    </main>
  );
}
