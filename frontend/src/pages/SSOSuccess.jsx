import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

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
    <div className="min-h-screen flex items-center justify-center p-4 relative z-10">
      <div className="bg-bg-card backdrop-blur-2xl border border-white/10 rounded-3xl w-full max-w-[420px] shadow-2xl p-8 relative overflow-hidden before:absolute before:-top-40 before:-right-40 before:w-80 before:h-80 before:bg-accent-primary/20 before:rounded-full before:blur-3xl before:-z-10">
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-white/10 rounded-2xl mx-auto mb-4 flex items-center justify-center text-accent-primary shadow-[inset_0_0_20px_rgba(99,102,241,0.2)]">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
              <line x1="6" y1="6" x2="6.01" y2="6" />
              <line x1="6" y1="18" x2="6.01" y2="18" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-white to-text-secondary bg-clip-text text-transparent mb-2">IPAM</h1>
          <p className="text-text-secondary text-sm">Single Sign-On</p>
        </div>

        <div className="flex flex-col gap-5">
          {error ? (
            <div className="bg-danger-bg text-danger border border-danger/20 rounded-xl p-4 flex items-center gap-3 text-sm font-medium" role="alert">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              {error}
            </div>
          ) : (
            <div className="text-center py-6">
              <span className="loader inline-block w-7 h-7 !border-3" />
              <p className="text-text-muted mt-4 text-sm">
                Completing sign-in…
              </p>
            </div>
          )}
        </div>

        <div className="mt-8 text-center text-xs text-text-muted">
          <p>Internal Network Tool · Authorized Access Only</p>
        </div>
      </div>
    </div>
  );
}

export default SSOSuccess;
