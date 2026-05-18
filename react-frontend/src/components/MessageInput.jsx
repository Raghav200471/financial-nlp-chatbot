import { useState, useRef, useEffect } from 'react';

export default function MessageInput({ onSend, loading }) {
  const [text, setText] = useState('');
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }, [text]);

  const send = () => {
    const msg = text.trim();
    if (!msg || loading) return;
    onSend(msg);
    setText('');
  };

  return (
    <div className="chat-input-wrap">
      <div className="chat-input-box">
        <textarea
          ref={ref}
          className="chat-textarea"
          placeholder="Ask me about stocks, loans, EMI, currency exchange..."
          value={text}
          rows={1}
          onChange={e => setText(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
          disabled={loading}
        />
        <button className="send-btn" onClick={send} disabled={!text.trim() || loading}>
          ↑
        </button>
      </div>
    </div>
  );
}
