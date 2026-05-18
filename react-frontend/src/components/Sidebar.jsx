import { useState, useEffect, useRef } from 'react';

/* ── Simple monochrome SVG icons (no colored emojis) ─── */
const IconPin = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/>
  </svg>
);
const IconRename = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/>
  </svg>
);
const IconDelete = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>
  </svg>
);

export default function Sidebar({
  chats, activeId, onSelect, onNew, onDelete, onRename, onPin,
  onGoSettings, onGoChat, currentPage,
  useBert, setUseBert, usePersonal, setUsePersonal,
  collapsed, onToggleCollapse,
}) {
  const [menuId, setMenuId] = useState(null);
  const [renamingId, setRenamingId] = useState(null);
  const [renameVal, setRenameVal] = useState('');
  const menuRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuId(null);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const pinned   = chats.filter(c =>  c.pinned);
  const unpinned = chats.filter(c => !c.pinned);

  const renderRow = (chat) => {
    const isActive = chat.id === activeId;

    if (renamingId === chat.id) {
      return (
        <div key={chat.id} style={{ padding: '2px 0' }}>
          <input
            className="rename-input"
            value={renameVal}
            autoFocus
            onChange={e => setRenameVal(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') { if (renameVal.trim()) onRename(chat.id, renameVal.trim()); setRenamingId(null); }
              if (e.key === 'Escape') setRenamingId(null);
            }}
          />
          <div className="rename-actions">
            <button onClick={() => { if (renameVal.trim()) onRename(chat.id, renameVal.trim()); setRenamingId(null); }}>Save</button>
            <button onClick={() => setRenamingId(null)}>Cancel</button>
          </div>
        </div>
      );
    }

    return (
      <div key={chat.id} className="chat-row-wrap" ref={menuId === chat.id ? menuRef : null}>
        <div className="chat-row">
          <button
            className={`chat-row-btn ${isActive ? 'active' : ''}`}
            onClick={() => { onSelect(chat.id); setMenuId(null); }}
            title={chat.title}
          >
            {(chat.title || 'New Chat').slice(0, 26)}
          </button>
          <button
            className="chat-dots-btn"
            onClick={e => { e.stopPropagation(); setMenuId(menuId === chat.id ? null : chat.id); }}
          >
            &#8942;
          </button>
        </div>
        {menuId === chat.id && (
          <div className="ctx-menu">
            <button className="ctx-menu-item" onClick={() => {
              setRenamingId(chat.id); setRenameVal(chat.title || ''); setMenuId(null);
            }}>
              <IconRename /> Rename
            </button>
            <button className="ctx-menu-item" onClick={() => { onPin(chat.id); setMenuId(null); }}>
              <IconPin /> {chat.pinned ? 'Unpin' : 'Pin'}
            </button>
            <button className="ctx-menu-item danger" onClick={() => { onDelete(chat.id); setMenuId(null); }}>
              <IconDelete /> Delete
            </button>
          </div>
        )}
      </div>
    );
  };

  if (collapsed) {
    return null;
  }

  return (
    <aside className="sidebar">
      {/* Collapse button — top right like Streamlit's << */}
      <button className="sidebar-collapse-btn" onClick={onToggleCollapse} title="Collapse sidebar">
        &#171;
      </button>

      {/* Brand */}
      <div className="brand-header">FinChat AI</div>

      {/* + New Chat — Streamlit: use_container_width=True, secondary */}
      <button className="new-chat-btn" onClick={onNew}>+ New Chat</button>

      {/* Model — radio buttons like Streamlit radio(horizontal=True) */}
      <div className="model-radio-group">
        <label className="model-radio-item">
          <input type="radio" name="model" checked={useBert} onChange={() => setUseBert(true)} />
          BERT (Advanced)
        </label>
        <label className="model-radio-item">
          <input type="radio" name="model" checked={!useBert} onChange={() => setUseBert(false)} />
          Baseline (Fast)
        </label>
      </div>

      {/* Personal Info toggle */}
      <label className="personal-toggle">
        <span className="toggle-switch">
          <input type="checkbox" checked={usePersonal} onChange={e => setUsePersonal(e.target.checked)} />
          <span className="toggle-slider" />
        </span>
        Personal Info
      </label>

      {/* Chat list — scrollable middle section */}
      <div className="sidebar-chats">
        {pinned.length > 0 && (
          <>
            <div className="sb-label">PINNED</div>
            {pinned.map(renderRow)}
          </>
        )}
        <div className="sb-label">CHATS</div>
        {unpinned.map(renderRow)}
      </div>

      {/* Footer — sticky bottom */}
      <div className="sidebar-footer">
        <button
          className="sidebar-footer-btn"
          onClick={currentPage === 'settings' ? onGoChat : onGoSettings}
        >
          {currentPage === 'settings' ? '\u2190 Back to Chat' : '\u2699  Settings & Help'}
        </button>
        <div className="sidebar-footer-note">
          FastAPI · SpaCy · HuggingFace<br />
          Deterministic-First Architecture
        </div>
      </div>
    </aside>
  );
}
