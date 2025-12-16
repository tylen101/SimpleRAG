'use client';

import { ColumnDef, Table } from '@/components/Table/Table';
import React, { useEffect, useState } from 'react';

type DocRow = {
  doc_id: number;
  title: string;
  filename: string;
  status: string;
  created_at: string;
};

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

  const columns: ColumnDef<DocRow>[] = [
    { title: 'ID', key: 'doc_id', sortable: true },
    { title: 'Title', key: 'title', sortable: true },
    { title: 'File', key: 'filename', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
    {
      title: 'Created',
      key: 'created_at',
      sortable: true,
      logic: (row: any) => new Date(row.created_at).toLocaleString(),
    },
  ];

  return (
    <div style={{ padding: 16, background: 'var(--background-primary)' }}>
      {/* search bar */}
      {/* search all values in data, filter results */}
      <input type="text" placeholder="Search..." />
      <Table
        data={documents}
        columns={columns}
        loading={loading}
        rowKey="doc_id"
      />
    </div>
  );
}

export default Documents;
