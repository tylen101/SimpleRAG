'use client';

import React, { useEffect, useRef } from 'react';

interface MermaidProps {
  chart: string;
  theme?: 'default' | 'dark' | 'forest' | 'neutral';
}

export default function Mermaid({ chart, theme = 'dark' }: MermaidProps) {
  const ref = useRef<HTMLDivElement>(null);
  const idRef = useRef(`mermaid-${Math.random().toString(36).substr(2, 9)}`);

  useEffect(() => {
    let mounted = true;

    const loadMermaid = async () => {
      // Dynamically import mermaid to ensure client-only execution
      const mermaid = (await import('mermaid')).default;

      // Initialize once globally
      if (!(window as any).__mermaidInitialized) {
        mermaid.initialize({ startOnLoad: false, theme });
        (window as any).__mermaidInitialized = true;
      }

      // Render diagram
      try {
        if (mounted && ref.current && chart) {
          ref.current.innerHTML = '';
          const cleanChart = chart.replace(/\\n/g, '\n');
          const { svg, bindFunctions } = await mermaid.render(
            idRef.current,
            cleanChart
          );
          ref.current.innerHTML = svg;
          bindFunctions?.(ref.current);
        }
      } catch (err) {
        console.error('Mermaid render error:', err);
        if (ref.current) ref.current.innerHTML = `<pre>${chart}</pre>`;
      }
    };

    loadMermaid();

    return () => {
      mounted = false;
    };
  }, [chart, theme]);

  return <div ref={ref} className="mermaid-container" />;
}
