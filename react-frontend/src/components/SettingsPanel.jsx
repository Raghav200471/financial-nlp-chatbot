import { useState, useEffect } from 'react';
import { api } from '../api/client';

export default function SettingsPanel({ onClose, onProfileSaved }) {
  const [profile, setProfile] = useState({
    monthly_income: '',
    existing_emis: '',
    savings: '',
    goals: '',
    risk_tolerance: 'moderate',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getProfile().then(p => {
      setProfile({
        monthly_income: p.monthly_income ?? '',
        existing_emis: p.existing_emis ?? '',
        savings: p.savings ?? '',
        goals: p.goals ?? '',
        risk_tolerance: p.risk_tolerance ?? 'moderate',
      });
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const payload = {
        monthly_income: profile.monthly_income ? Number(profile.monthly_income) : null,
        existing_emis: profile.existing_emis ? Number(profile.existing_emis) : null,
        savings: profile.savings ? Number(profile.savings) : null,
        goals: profile.goals,
        risk_tolerance: profile.risk_tolerance,
      };
      await api.saveProfile(payload);
      if (onProfileSaved) onProfileSaved(payload);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  };

  const field = (key) => ({
    value: profile[key],
    onChange: e => setProfile(p => ({ ...p, [key]: e.target.value })),
  });

  return (
    <div className="settings-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="settings-panel">
        <div className="settings-header">
          <h3>Financial Profile</h3>
          <button className="settings-close" onClick={onClose}>×</button>
        </div>

        <div className="settings-body">
          <div className="settings-section-title">Your Financial Context</div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
            This information is used to personalise loan eligibility checks, EMI calculations, and investment advice. Never stored externally — only in your account.
          </p>

          <div className="settings-row">
            <label>Monthly Income (₹)</label>
            <input type="number" placeholder="e.g. 75000" {...field('monthly_income')} />
          </div>

          <div className="settings-row">
            <label>Existing Monthly EMIs (₹)</label>
            <input type="number" placeholder="e.g. 12000" {...field('existing_emis')} />
          </div>

          <div className="settings-row">
            <label>Total Savings / Investments (₹)</label>
            <input type="number" placeholder="e.g. 300000" {...field('savings')} />
          </div>

          <div className="settings-row">
            <label>Financial Goals</label>
            <input type="text" placeholder="e.g. Buy a house in 5 years, retire at 50" {...field('goals')} />
          </div>

          <div className="settings-row">
            <label>Risk Tolerance</label>
            <select {...field('risk_tolerance')}>
              <option value="low">Low — prefer safe investments</option>
              <option value="moderate">Moderate — balanced approach</option>
              <option value="high">High — comfortable with volatility</option>
            </select>
          </div>

          {loading ? (
            <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>Loading profile…</p>
          ) : (
            <button className="settings-save-btn" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : '💾 Save Profile'}
            </button>
          )}

          {saved && <div className="settings-saved">Profile saved successfully!</div>}
        </div>
      </div>
    </div>
  );
}
