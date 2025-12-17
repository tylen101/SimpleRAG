'use client';

import { ColumnDef, Table } from '@/components/Table/Table';
import React, { useEffect, useState } from 'react';

import styles from './DocumentsTable.module.css';

type DocRow = {
  doc_id: number;
  title: string;
  filename: string;
  status: string;
  created_at: string;
};

type DocumentsTableProps = {
  selected: number[];
  handleSelect: (row_id: number) => React.ReactNode;
};

function DocumentsTable({ selected = [], handleSelect }: DocumentsTableProps) {
  // load all documents user has access to
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  const [expand, setExpand] = useState(true);

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
    {
      title: 'Select',
      key: 'select',
      // sortable: true,
      logic: (row: DocRow) => {
        return (
          <input
            type="checkbox"
            onChange={(e) => handleSelect(row.doc_id)}
            checked={selected.includes(row.doc_id)}
          />
        );
      },
    },
    { title: 'Title', key: 'title', sortable: true },
    {
      title: 'Created',
      key: 'created_at',
      sortable: true,
      logic: (row: DocRow) => new Date(row.created_at).toLocaleString(),
    },
    { title: 'ID', key: 'doc_id', sortable: true },
    { title: 'File', key: 'filename', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {/* search bar */}
      {/* search all values in data, filter results */}
      <div style={{ display: 'flex' }}>
        <button
          style={{
            background: 'none',
            border: 'none',
            // width: '100%',
            // display: 'flex',
            // justifyContent: 'center',
          }}
          onClick={() => setExpand(!expand)}
        >
          {!selected.length ? '🔸' : '🔹'}
        </button>
        <div className={styles.label}>
          {selected.length} Document{selected.length !== 1 ? 's' : ''} selected{' '}
          {!expand && 'click to expand'}
        </div>
      </div>

      {/* {expand ? ( */}
      <Table
        className={styles.table + ' ' + (expand ? styles.expanded : '')}
        data={documents}
        columns={columns}
        loading={loading}
        rowKey="doc_id"
      />
      {/* ) : (
        ''
      )} */}
    </div>
  );
}

export default DocumentsTable;
