import { useState, useEffect, useCallback, useRef } from 'react';
import { v4 as uuid } from 'uuid';
import Sidebar from '../components/Sidebar';
import ChatWindow from '../components/ChatWindow';
import MessageInput from '../components/MessageInput';
import TopBar from '../components/TopBar';
import SettingsPage from './SettingsPage';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

function makeChat() {
  return {
    id: uuid(),
    title: 'New Chat',
    pinned: false,
    messages: [],
    debugData: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

export default function ChatPage() {
  const { user } = useAuth();
  const [chats, setChats]           = useState([]);
  const [activeId, setActiveId]     = useState(null);
  const [loading, setLoading]       = useState(false);
  const [page, setPage]             = useState('chat'); // 'chat' | 'settings'
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [useBert, setUseBert]       = useState(true);
  const [useGemini, setUseGemini]   = useState(true);
  const [usePersonal, setUsePersonal] = useState(false);
  const [userProfile, setUserProfile] = useState({
    monthly_income: '', existing_emis: '', savings: '',
    financial_goals: '', risk_tolerance: 'Moderate',
  });
  const profileRef = useRef(userProfile);

  // Keep ref in sync
  useEffect(() => { profileRef.current = userProfile; }, [userProfile]);

  // ── Load chats + profile on mount ───────────────────────
  useEffect(() => {
    api.getChats().then(data => {
      if (data && data.length > 0) {
        const sorted = [...data]
          .map(c => ({ ...c, debugData: c.debugData || [] }))
          .sort((a, b) => {
            if (a.pinned !== b.pinned) return b.pinned - a.pinned;
            return new Date(b.updated_at || 0) - new Date(a.updated_at || 0);
          });
        setChats(sorted);
        setActiveId(sorted[0].id);
      } else {
        const first = makeChat();
        setChats([first]);
        setActiveId(first.id);
        api.saveChat(first).catch(console.error);
      }
    }).catch(() => {
      const first = makeChat();
      setChats([first]);
      setActiveId(first.id);
    });

    // Load RAG profile
    api.getProfile().then(p => {
      if (p) {
        const mapped = {
          monthly_income:  p.monthly_income  ? String(p.monthly_income)  : '',
          existing_emis:   p.existing_emis   ? String(p.existing_emis)   : '',
          savings:         p.savings         ? String(p.savings)         : '',
          financial_goals: p.goals           || '',
          risk_tolerance:  p.risk_tolerance
            ? p.risk_tolerance.charAt(0).toUpperCase() + p.risk_tolerance.slice(1)
            : 'Moderate',
        };
        setUserProfile(mapped);
        profileRef.current = mapped;
      }
    }).catch(() => {});
  }, []);

  const persist = useCallback(async (chat) => {
    try {
      // strip debugData before sending to API (not part of DB schema)
      const { debugData, ...toSave } = chat;
      await api.saveChat(toSave);
    } catch (e) { console.error(e); }
  }, []);

  const activeChat = chats.find(c => c.id === activeId);
  const messages   = activeChat?.messages  || [];
  const debugData  = activeChat?.debugData || [];

  // ── New Chat ─────────────────────────────────────────────
  const handleNew = useCallback(() => {
    const c = makeChat();
    setChats(prev => [c, ...prev]);
    setActiveId(c.id);
    setPage('chat');
    persist(c);
  }, [persist]);

  // ── Send ─────────────────────────────────────────────────
  const handleSend = useCallback(async (text) => {
    let cid = activeId;
    if (!cid) {
      const c = makeChat();
      setChats(prev => [c, ...prev]);
      setActiveId(c.id);
      cid = c.id;
    }
    setPage('chat');
    setLoading(true);

    const userMsg = { role: 'user', content: text };

    setChats(prev => prev.map(c => {
      if (c.id !== cid) return c;
      const msgs = [...c.messages, userMsg];
      return { ...c, messages: msgs, debugData: [...(c.debugData||[]), null] };
    }));

    try {
      const profile = profileRef.current;
      const hasProfile = usePersonal && (profile.monthly_income || profile.existing_emis || profile.savings || profile.financial_goals);
      const res = await api.sendMessage({
        message: text,
        sessionId: cid,
        useBert,
        useGemini,
        userContext: hasProfile ? profile : null,
      });

      const botMsg   = { role: 'assistant', content: res.response };
      const debugEntry = {
        intent:     res.intent,
        confidence: res.confidence,
        entities:   res.entities || [],
      };

      setChats(prev => prev.map(c => {
        if (c.id !== cid) return c;
        const msgs  = [...c.messages, botMsg];
        const dbg   = [...(c.debugData||[]), debugEntry];
        // Set title from intent on first message
        let title = c.title;
        if (c.messages.length === 0 && res.intent) {
          title = res.intent.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase());
        } else if (c.messages.length === 0) {
          title = text.slice(0, 40);
        }
        const updated = { ...c, messages: msgs, debugData: dbg, title, updated_at: new Date().toISOString() };
        persist(updated);
        return updated;
      }));
    } catch (err) {
      const errMsg = { role: 'assistant', content: `Error: ${err.message}` };
      setChats(prev => prev.map(c => {
        if (c.id !== cid) return c;
        return { ...c, messages: [...c.messages, errMsg], debugData: [...(c.debugData||[]), null] };
      }));
    } finally {
      setLoading(false);
    }
  }, [activeId, useBert, useGemini, usePersonal, persist]);

  // ── Chat actions ─────────────────────────────────────────
  const handleDelete = useCallback(async (chatId) => {
    try { await api.deleteChat(chatId); } catch {}
    setChats(prev => {
      const remaining = prev.filter(c => c.id !== chatId);
      if (activeId === chatId) setActiveId(remaining[0]?.id || null);
      return remaining;
    });
  }, [activeId]);

  const handleRename = useCallback((chatId, title) => {
    setChats(prev => prev.map(c => {
      if (c.id !== chatId) return c;
      const u = { ...c, title };
      persist(u);
      return u;
    }));
  }, [persist]);

  const handlePin = useCallback((chatId) => {
    setChats(prev => {
      const updated = prev.map(c => {
        if (c.id !== chatId) return c;
        const u = { ...c, pinned: !c.pinned };
        persist(u);
        return u;
      });
      return [...updated].sort((a, b) => {
        if (a.pinned !== b.pinned) return b.pinned - a.pinned;
        return new Date(b.updated_at||0) - new Date(a.updated_at||0);
      });
    });
  }, [persist]);

  return (
    <div className="app-layout">
      {sidebarCollapsed && (
        <button
          className="sidebar-expand-btn"
          onClick={() => setSidebarCollapsed(false)}
          title="Expand sidebar"
        >
          &#187;
        </button>
      )}
      <Sidebar
        chats={chats}
        activeId={activeId}
        onSelect={id => { setActiveId(id); setPage('chat'); }}
        onNew={handleNew}
        onDelete={handleDelete}
        onRename={handleRename}
        onPin={handlePin}
        onGoSettings={() => setPage('settings')}
        onGoChat={() => setPage('chat')}
        currentPage={page}
        useBert={useBert}
        setUseBert={setUseBert}
        usePersonal={usePersonal}
        setUsePersonal={setUsePersonal}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(c => !c)}
      />

      {page === 'settings' ? (
        <SettingsPage
          useGemini={useGemini}
          setUseGemini={setUseGemini}
          userProfile={userProfile}
          setUserProfile={p => { setUserProfile(p); profileRef.current = p; }}
          usePersonal={usePersonal}
          useBert={useBert}
        />
      ) : (
        <div className="chat-main">
          <TopBar />
          <div className="chat-inner">
            <ChatWindow
              messages={messages}
              debugData={debugData}
              loading={loading}
              onSend={handleSend}
            />
            <MessageInput onSend={handleSend} loading={loading} />
          </div>
        </div>
      )}
    </div>
  );
}
