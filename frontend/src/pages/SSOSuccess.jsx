import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './Login.css';

/**
 * SSOSuccess — handles the OAuth2/OIDC callback redirect.
 *
 * The backend SSO callback redirects here with:
 *   /sso-success#token=<JWT>
 *
 * This component extracts the token, stores it in localStorage
 * (identical to local login), and navigates to the Dashboard.
 */
function SSOSuccess() {
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState('');

  useEffect(() => {
    const hash = location.hash.replace(/^#/, '');
    const params = new URLSearchParams(hash);
    const token = params.get('token');

    if (token) {
      localStorage.setItem('access_token', token);
      navigate('/', { replace: true });
    } else {
      setError('SSO authentication failed — no token received.');
    }
  }, [location, navigate]);

  // Only shown briefly on error; the happy path redirects instantly
  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
              <line x1="6" y1="6" x2="6.01" y2="6" />
              <line x1="6" y1="18" x2="6.01" y2="18" />
            </svg>
          </div>
          <h1 className="login-title">IPAM</h1>
          <p className="login-subtitle">Single Sign-On</p>
        </div>

        <div className="login-body">
          {error ? (
            <div className="login-error" role="alert">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              {error}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <span className="loader" style={{ width: 28, height: 28, borderWidth: 3, display: 'inline-block' }} />
              <p style={{ color: 'var(--text-muted)', marginTop: 16, fontSize: '0.9rem' }}>
                Completing sign-in…
              </p>
            </div>
          )}
        </div>

        <div className="login-footer">
          <p>Internal Network Tool · Authorized Access Only</p>
        </div>
      </div>
    </div>
  );
}

export default SSOSuccess;
