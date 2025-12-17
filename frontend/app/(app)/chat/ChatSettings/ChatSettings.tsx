'use client';

import React from 'react';
import styles from './ChatSettings.module.css';
import DocumentsTable from '../DocumentsTable/DocumentsTable';
import { ScopeMode, Settings } from '../page';

interface ChatSettingsProps {
  setSettings: (settings: Settings) => void;
  settings: Settings;
}

function ChatSettings({ setSettings, settings }: ChatSettingsProps) {
  const toggleElement = (arr: number[], val: number) => {
    if (arr.includes(val)) {
      return arr.filter((el) => el !== val);
    } else {
      return [...arr, val];
    }
  };

  return (
    <section className={styles.card}>
      <div className={styles.grid2}>
        <div className={styles.formRow}>
          <label className={styles.label} htmlFor="scopeMode">
            Scope (what documents to search from)
          </label>
          <select
            id="scopeMode"
            className={styles.select}
            value={settings.scopeMode}
            onChange={(e) =>
              setSettings({
                ...settings,
                scopeMode: e.target.value as ScopeMode,
              })
            }
          >
            <option value="all">All</option>
            <option value="selected">Specific</option>
          </select>
          <div className={styles.helpText}>
            To choose what documents to search select Specific.
          </div>
        </div>
        <div className={styles.formRow}>
          <label className={styles.label} htmlFor="kVec">
            Source Limit ({settings.k_vec})
          </label>
          <input
            type="range"
            max={10}
            min={1}
            onChange={(e) =>
              setSettings({ ...settings, k_vec: Number(e.target.value) })
            }
          />
          <div className={styles.helpText}>
            Number of sources within searched documents. Higher source limits
            may lead to instability.
          </div>
        </div>
      </div>
      {settings.scopeMode === 'selected' && (
        <div>
          {/* load documents and allow user to select */}
          <DocumentsTable
            selected={settings.doc_ids}
            handleSelect={(doc_id: number) => {
              setSettings({
                ...settings,
                doc_ids: toggleElement(settings.doc_ids, doc_id),
              });
            }}
          />
        </div>
      )}
    </section>
  );
}

export default ChatSettings;
