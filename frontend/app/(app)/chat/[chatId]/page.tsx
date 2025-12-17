'use client';
import { useAuth } from '@/app/context/AuthContext';
import { useParams, useRouter } from 'next/navigation';
import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import styles from './Chat.module.css';
import Mermaid from '@/components/Mermaid/Mermaid';
import Button from '@/components/Button/Button';

// interface MarkdownBlock {
//   id: number;
//   position: number;
//   type: 'markdown';
//   content: string;
// }

// interface DiagramBlock {
//   id: number;
//   position: number;
//   type: 'diagram';
//   content: string;
// }

// interface CodeBlock {
//   id: number;
//   position: number;
//   type: 'code';
//   lang: string;
//   caption?: string;
//   content: string;
// }

// interface QuizBlock {
//   id: number;
//   position: number;
//   type: 'quiz';
//   prompt: string;
//   choices?: string[];
//   answer?: number;
//   explain_on_fail?: string;
// }

// interface ChallengeBlock {
//   id: number;
//   position: number;
//   type: 'challenge';
//   instructions_md: string;
//   boilerplate: string;
//   tests?: string;
//   rubric?: object;
//   static_checks?: object;
// }

// type LessonBlock =
//   | MarkdownBlock
//   | DiagramBlock
//   | CodeBlock
//   | QuizBlock
//   | ChallengeBlock;

// interface LessonObj {
//   id: string;
//   title: string;
//   topic: string;
//   objectives: string[];
//   difficulty: string;
//   blocks: LessonBlock[];
//   current_block_index: number;
// }

type ChatHistory = {};

function LessonPage() {
  const params = useParams();
  const lessonId = params.lessonId;

  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [lesson, setLesson] = useState<ChatHistory | null>(null);

  const getLesson = async () => {
    try {
      const res = await fetch(
        `http://localhost:8000/conversations/conversations/${lessonId}`,
        {
          credentials: 'include',
        }
      );

      if (!res.ok) throw new Error('Unauthorized');

      const data = await res.json();
      console.log('Lesson data:', data);
      setLesson(data);
    } catch (error) {
      console.warn('Error fetching lesson', error);
    }
  };

  const progressLesson = async () => {
    try {
      const newLessonData = await fetch(
        `http://localhost:8000/lessons/${lessonId}/progress`,
        {
          method: 'POST',
          credentials: 'include',
        }
      );
      if (!newLessonData.ok) throw new Error('Unauthorized');

      const data = await newLessonData.json();
      console.log('Lesson data:', data);
      setLesson(data);
    } catch (error) {
      console.warn('Error fetching lesson', error);
    }
  };

  useEffect(() => {
    if (!lesson) getLesson();
  }, [loading]);

  const sanitize = (content: string) => content.replace(/\\n/g, '\n').trim();

  if (loading || !lesson) return <p>Loading...</p>;

  return (
    <div className={styles.lesson}>
      <header className={styles.header}>
        <h1>{lesson.title}</h1>
        <div className={styles.meta}>
          <span>{lesson.topic}</span>
          <span>{lesson.difficulty}</span>
        </div>
      </header>

      {/* Objectives */}
      <section className={styles.section}>
        <h2>Objectives</h2>
        <ul>
          {lesson.objectives.map((o, i) => (
            <li key={i}>{o}</li>
          ))}
        </ul>
      </section>

      {/* Lesson Blocks */}
      <section className={styles.section}>
        <h2>Lesson Content</h2>

        {lesson.blocks.map((block) => {
          switch (block.type) {
            case 'markdown':
              return (
                <div key={block.id} className={styles.markdown}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {sanitize(block.content)}
                  </ReactMarkdown>
                </div>
              );

            case 'diagram':
              return (
                <div key={block.id}>
                  <Mermaid chart={sanitize(block.content)} />
                </div>
              );

            case 'code':
              return (
                <div key={block.id} className={styles.codeBlock}>
                  {block.caption && <h4>{block.caption}</h4>}
                  <pre>
                    <code className={`language-${block.lang}`}>
                      {sanitize(block.content)}
                    </code>
                  </pre>
                </div>
              );

            case 'quiz':
              return (
                <div key={block.id} className={styles.quizBlock}>
                  <h4>{block.prompt}</h4>
                  <ul>
                    {block.choices?.map((choice, i) => (
                      <li key={i}>{choice}</li>
                    ))}
                  </ul>
                </div>
              );

            case 'challenge':
              return (
                <div key={block.id} className={styles.challenge}>
                  <ReactMarkdown>{block.instructions_md}</ReactMarkdown>

                  <pre>
                    <code>{block.boilerplate}</code>
                  </pre>
                </div>
              );

            default:
              return null;
          }
        })}
      </section>
      <Button text={'Continue'} onClick={progressLesson} />

      {/*  */}
    </div>
  );
}

export default LessonPage;
