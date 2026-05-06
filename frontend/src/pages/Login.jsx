import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/axios';

function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [ssoEnabled, setSsoEnabled] = useState(false);

  // Check if SSO is configured on mount
  useEffect(() => {
    api.get('/auth/sso/enabled')
      .then((res) => setSsoEnabled(res.data.sso_enabled))
      .catch(() => setSsoEnabled(false));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // OAuth2 token endpoint expects form-encoded data
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);

      const response = await api.post('/auth/token', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      localStorage.setItem('access_token', response.data.access_token);
      navigate('/', { replace: true });
    } catch (err) {
      if (err.response && err.response.status === 401) {
        setError('Invalid username or password.');
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSSOLogin = () => {
    // Redirect the entire browser to the backend SSO login endpoint
    window.location.href = `${api.defaults.baseURL}/auth/sso/login`;
  };

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
          <p className="text-text-secondary text-sm">IP Address Management</p>
        </div>

        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-danger-bg text-danger border border-danger/20 rounded-xl p-4 flex items-center gap-3 text-sm font-medium" role="alert">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              {error}
            </div>
          )}

          <div>
            <label className="block mb-2 text-sm font-medium text-text-secondary" htmlFor="login-username">Username</label>
            <div className="relative mt-2">
              <input
                id="login-username"
                className="peer w-full px-4 py-3 pl-11 bg-black/20 border border-white/10 rounded-xl text-text-primary text-sm transition-all focus:outline-none focus:border-accent-primary focus:ring-3 focus:ring-indigo-500/20"
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
                autoFocus
              />
              <svg className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted transition-colors peer-focus:text-accent-primary" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
          </div>

          <div>
            <label className="block mb-2 text-sm font-medium text-text-secondary" htmlFor="login-password">Password</label>
            <div className="relative mt-2">
              <input
                id="login-password"
                className="peer w-full px-4 py-3 pl-11 bg-black/20 border border-white/10 rounded-xl text-text-primary text-sm transition-all focus:outline-none focus:border-accent-primary focus:ring-3 focus:ring-indigo-500/20"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
              <svg className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted transition-colors peer-focus:text-accent-primary" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
          </div>

          <button
            type="submit"
            className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-medium text-sm cursor-pointer transition-all border-none outline-none bg-accent-primary text-white shadow-[0_4px_12px_var(--color-accent-glow)] hover:bg-accent-hover hover:-translate-y-0.5 hover:shadow-[0_6px_16px_var(--color-accent-glow)] disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-[0_4px_12px_var(--color-accent-glow)]"
            disabled={loading || !username || !password}
          >
            {loading ? (
              <>
                <span className="loader w-5 h-5 !border-2"></span>
                Signing in…
              </>
            ) : (
              'Sign In'
            )}
          </button>

          {ssoEnabled && (
            <>
              <div className="flex items-center my-2">
                <div className="flex-1 h-px bg-white/10"></div>
                <span className="px-4 text-sm font-medium text-text-muted uppercase tracking-wider">OR</span>
                <div className="flex-1 h-px bg-white/10"></div>
              </div>

              <button
                type="button"
                id="sso-login-btn"
                className="w-full inline-flex items-center justify-center gap-3 px-5 py-3 rounded-xl font-medium text-sm cursor-pointer transition-all border border-white/10 outline-none bg-white/5 text-text-primary hover:bg-white/10 hover:border-white/20"
                onClick={handleSSOLogin}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                  <polyline points="10 17 15 12 10 7" />
                  <line x1="15" y1="12" x2="3" y2="12" />
                </svg>
                Sign in with Corporate SSO
              </button>
            </>
          )}
        </form>

        <div className="mt-8 text-center text-xs text-text-muted">
          <p>Internal Network Tool · Authorized Access Only</p>
        </div>
      </div>
    </div>
  );
}

export default Login;

