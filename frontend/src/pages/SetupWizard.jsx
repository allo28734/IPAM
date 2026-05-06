import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/axios';
import './Login.css';

export default function SetupWizard() {
  const [formData, setFormData] = useState({ username: '', email: '', password: '', role: 'admin', base_domain: window.location.origin, enable_network_discovery: true });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Register
      const registerData = {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        role: formData.role
      };
      await api.post('/auth/register', registerData);

      // Auto login
      const formDataUrlEncoded = new URLSearchParams();
      formDataUrlEncoded.append('username', formData.username);
      formDataUrlEncoded.append('password', formData.password);

      const loginRes = await api.post('/auth/token', formDataUrlEncoded, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      const token = loginRes.data.access_token;
      localStorage.setItem('access_token', token);

      // Save System Settings (Application Domain & Features)
      await api.put('/system/settings', {
        base_domain: formData.base_domain,
        enable_network_discovery: formData.enable_network_discovery
      }, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Setup failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card" style={{ maxWidth: '500px' }}>
        <div className="login-header">
          <h2 className="login-title">Welcome to IPAM</h2>
          <p className="login-subtitle">Complete the Zero-Touch Setup</p>
        </div>
        
        <form className="login-body" onSubmit={handleSubmit}>
          {error && (
            <div className="login-error" role="alert">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              {error}
            </div>
          )}

          <div className="form-group">
            <label className="form-label" htmlFor="username">Admin Username</label>
            <div className="login-input-wrapper">
              <input
                id="username"
                name="username"
                type="text"
                required
                className="form-input"
                placeholder="Admin username"
                value={formData.username}
                onChange={handleChange}
              />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="email">Admin Email</label>
            <div className="login-input-wrapper">
              <input
                id="email"
                name="email"
                type="email"
                required
                className="form-input"
                placeholder="admin@example.com"
                value={formData.email}
                onChange={handleChange}
              />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="password">Admin Password</label>
            <div className="login-input-wrapper">
              <input
                id="password"
                name="password"
                type="password"
                required
                className="form-input"
                placeholder="Secure password"
                value={formData.password}
                onChange={handleChange}
              />
            </div>
          </div>
          
          <div className="login-divider">
            <span>System Settings</span>
          </div>
          
          <div className="form-group">
            <label className="form-label" htmlFor="base_domain">Application Domain</label>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px' }}>Used for SSO redirects (e.g. https://ipam.local)</p>
            <div className="login-input-wrapper">
              <input
                id="base_domain"
                name="base_domain"
                type="url"
                required
                className="form-input"
                placeholder="https://ipam.local"
                value={formData.base_domain}
                onChange={handleChange}
              />
            </div>
          </div>
          
          <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              id="enable_network_discovery"
              name="enable_network_discovery"
              type="checkbox"
              checked={formData.enable_network_discovery}
              onChange={(e) => setFormData({ ...formData, enable_network_discovery: e.target.checked })}
            />
            <label htmlFor="enable_network_discovery" style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Enable Background Network Scanning
            </label>
          </div>

          <button
            type="submit"
            className="btn btn-primary login-submit"
            disabled={loading}
            style={{ marginTop: '24px' }}
          >
            {loading ? (
              <>
                <span className="loader" style={{ width: 18, height: 18, borderWidth: 2 }} />
                Setting up…
              </>
            ) : (
              'Complete Setup'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
