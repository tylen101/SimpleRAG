'use client';

import React, { useEffect, useState } from 'react';

function Documents() {
  // load all documents user has access to
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadDocuments = async () => {
    try {
      const API_BASE =
        process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const res = await fetch(`${API_BASE}/documents`, {
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Unauthorized');
      const data = await res.json();
      setDocuments(data);
    } catch (err) {
      console.warn('No active session');
      setDocuments([]);
      // reroute to login
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  console.log(documents);

  return <div>Documents</div>;
}

export default Documents;
