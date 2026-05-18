import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const SUGGESTIONS = [
  'What is the price of Apple?',
  'Calculate EMI for 10 lakh at 8.5%',
  'USD to INR rate',
  'What is a savings account?',
  'Am I eligible for a home loan with a 50k monthly salary and existing EMI of 10k?',
  'Explain SIP vs lump sum',
];

function DebugPanel({ debug }) {
  const [open, setOpen] = useState(false);
  if (!debug) return null;
  return (
    <div>
      <button className="debug-toggle" onClick={() => setOpen(o => !o)}>
        {open ? '\u25BE' : '\u25B8'} View Intent &amp; Entities
      </button>
      {open && (
        <div className="debug-panel">
          <div>
            <span>Intent: </span>
            <code className="tag">{debug.intent || 'N/A'}</code>
          </div>
          <div>
            <span>Confidence: </span>
            <code className="tag">
              {debug.confidence != null ? debug.confidence.toFixed(4) : 'N/A'}
            </code>
          </div>
          <div>
            <span>Entities: </span>
            {debug.entities && debug.entities.length > 0
              ? debug.entities.map((e, i) => (
                  <code key={i} className="tag" style={{ marginRight: 4 }}>
                    {e.value} ({e.entity})
                  </code>
                ))
              : <code className="tag">None detected</code>
            }
          </div>
        </div>
      )}
    </div>
  );
}

export default function ChatWindow({ messages, debugData, loading, onSend }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Welcome screen — no messages yet
  if (messages.length === 0 && !loading) {
    return (
      <div className="chat-messages">
        <div className="welcome-container">
          <div className="welcome-greeting">Hi, I'm your Financial Assistant</div>
          <div className="welcome-tagline">What would you like to know?</div>
          <div className="suggestions-grid">
            {SUGGESTIONS.map(s => (
              <button
                key={s}
                className="suggestion-btn"
                onClick={() => onSend && onSend(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-messages">
      {messages.map((msg, i) => (
        <div key={i} className={`chat-msg ${msg.role}`}>
          <div className={`msg-avatar ${msg.role}`}>
            {msg.role === 'user' ? 'U' : 'AI'}
          </div>
          <div className="msg-body">
            <div className="msg-content">
              {msg.role === 'assistant'
                ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                : msg.content
              }
            </div>
            {msg.role === 'assistant' && debugData?.[i] && (
              <DebugPanel debug={debugData[i]} />
            )}
          </div>
        </div>
      ))}

      {loading && (
        <div className="chat-msg assistant">
          <div className="msg-avatar assistant">AI</div>
          <div className="msg-body">
            <div className="typing-dots">
              <span /><span /><span />
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
