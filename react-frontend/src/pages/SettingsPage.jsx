import { useState, useEffect } from 'react';
import { api } from '../api/client';

export default function SettingsPage({ useGemini, setUseGemini, userProfile, setUserProfile, usePersonal, useBert }) {
  const [health, setHealth] = useState(null);
  const [healthErr, setHealthErr] = useState(false);
  const [form, setForm] = useState({ ...userProfile });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch('http://localhost:8000/api/health')
      .then(r => r.json())
      .then(d => setHealth(d))
      .catch(() => setHealthErr(true));
  }, []);

  const handleSave = async () => {
    // Save to local state
    setUserProfile(form);
    // Also persist to MongoDB
    try {
      await api.saveProfile({
        monthly_income: form.monthly_income ? Number(form.monthly_income) : null,
        existing_emis: form.existing_emis ? Number(form.existing_emis) : null,
        savings: form.savings ? Number(form.savings) : null,
        goals: form.financial_goals || '',
        risk_tolerance: (form.risk_tolerance || 'Moderate').toLowerCase(),
      });
    } catch (e) { console.error(e); }
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const field = (key) => ({
    value: form[key] || '',
    onChange: e => setForm(f => ({ ...f, [key]: e.target.value })),
  });

  return (
    <div className="settings-page">
      <div className="settings-inner">
        <h2>Settings</h2>
        <hr className="settings-divider" />

        {/* API Status */}
        <h3>API Status</h3>
        {healthErr ? (
          <div className="status-err">
            Backend not reachable. Start with:<br />
            <code>`uvicorn api.main:app --reload --port 8000`</code>
          </div>
        ) : health ? (
          <>
            <div className="status-ok">Connected — {health.mode || 'unknown'} mode</div>
            <div className={health.gemini_enabled ? 'status-ok' : 'status-warn'}>
              Gemini fallback: {health.gemini_enabled ? 'Enabled' : 'Disabled'}
            </div>
          </>
        ) : (
          <p>Checking connection…</p>
        )}

        <hr className="settings-divider" />

        {/* AI Model Engine — Streamlit line 502-504 */}
        <h3>AI Model Engine</h3>
        <p><strong>Currently selected:</strong> <code>{useBert === undefined ? 'BERT (Advanced)' : useBert ? 'BERT (Advanced)' : 'Baseline (Fast)'}</code></p>
        <p className="caption">Change this from the sidebar radio buttons.</p>

        <hr className="settings-divider" />

        {/* Gemini toggle */}
        <h3>Gemini AI Fallback</h3>
        <label className="personal-toggle" style={{ marginBottom: 8 }}>
          <span className="toggle-switch">
            <input type="checkbox" checked={useGemini} onChange={e => setUseGemini(e.target.checked)} />
            <span className="toggle-slider" />
          </span>
          Enable Gemini AI Fallback
        </label>
        {!useGemini
          ? <div className="status-info">Strictly using local rules & knowledge base.</div>
          : <p className="caption">When enabled, complex queries that can't be answered locally will be forwarded to Gemini.</p>
        }

        <hr className="settings-divider" />

        {/* Personal Finance Profile */}
        <h3>Personal Finance Profile</h3>
        {!usePersonal ? (
          <div className="status-warn">
            Personal Info is turned off. Enable it from the sidebar toggle to fill your profile.
          </div>
        ) : (
          <>
            <p className="caption">Used for personalised advice. Saved to your account.</p>
            <div className="settings-row">
              <label className="settings-label">Monthly Income (₹)</label>
              <input type="number" placeholder="e.g. 75000" {...field('monthly_income')} />
            </div>
            <div className="settings-row">
              <label className="settings-label">Existing Monthly EMIs (₹)</label>
              <input type="number" placeholder="e.g. 12000" {...field('existing_emis')} />
            </div>
            <div className="settings-row">
              <label className="settings-label">Total Savings / Investments (₹)</label>
              <input type="number" placeholder="e.g. 300000" {...field('savings')} />
            </div>
            <div className="settings-row">
              <label className="settings-label">Financial Goals</label>
              <textarea
                rows={3}
                placeholder="e.g. Buy a house in 5 years, retire early..."
                {...field('financial_goals')}
                style={{ borderRadius: 14 }}
              />
            </div>
            <div className="settings-row">
              <label className="settings-label">Risk Tolerance</label>
              <select value={form.risk_tolerance || 'Moderate'} onChange={e => setForm(f => ({ ...f, risk_tolerance: e.target.value }))}>
                <option>Low</option>
                <option>Moderate</option>
                <option>High</option>
              </select>
            </div>
          </>
        )}

        <hr className="settings-divider" />

        <button className="save-settings-btn" onClick={handleSave}>
          {saved ? 'Settings Saved!' : 'Save Settings'}
        </button>

        <hr className="settings-divider" />
        <p className="caption">Built with FastAPI + React + SpaCy + HuggingFace · Deterministic-First Architecture</p>
      </div>
    </div>
  );
}
