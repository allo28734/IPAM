import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/axios';

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

  const formInputClass = "w-full px-4 py-3 bg-black/20 border border-white/10 rounded-xl text-text-primary text-sm transition-all focus:outline-none focus:border-accent-primary focus:ring-3 focus:ring-indigo-500/20";
  const formLabelClass = "block mb-2 text-sm font-medium text-text-secondary";
  const btnPrimaryClass = "w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-medium text-sm cursor-pointer transition-all border-none outline-none bg-accent-primary text-white shadow-[0_4px_12px_var(--color-accent-glow)] hover:bg-accent-hover hover:-translate-y-0.5 hover:shadow-[0_6px_16px_var(--color-accent-glow)] disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-[0_4px_12px_var(--color-accent-glow)]";

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative z-10">
      <div className="bg-bg-card backdrop-blur-2xl border border-white/10 rounded-3xl w-full max-w-[500px] shadow-2xl p-8 relative overflow-hidden before:absolute before:-top-40 before:-right-40 before:w-80 before:h-80 before:bg-accent-primary/20 before:rounded-full before:blur-3xl before:-z-10">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold bg-gradient-to-r from-white to-text-secondary bg-clip-text text-transparent mb-2">Welcome to IPAM</h2>
          <p className="text-text-secondary text-sm">Complete the Zero-Touch Setup</p>
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
            <label className={formLabelClass} htmlFor="username">Admin Username</label>
            <div className="relative">
              <input
                id="username"
                name="username"
                type="text"
                required
                className={formInputClass}
                placeholder="Admin username"
                value={formData.username}
                onChange={handleChange}
              />
            </div>
          </div>
          <div>
            <label className={formLabelClass} htmlFor="email">Admin Email</label>
            <div className="relative">
              <input
                id="email"
                name="email"
                type="email"
                required
                className={formInputClass}
                placeholder="admin@example.com"
                value={formData.email}
                onChange={handleChange}
              />
            </div>
          </div>
          <div>
            <label className={formLabelClass} htmlFor="password">Admin Password</label>
            <div className="relative">
              <input
                id="password"
                name="password"
                type="password"
                required
                className={formInputClass}
                placeholder="Secure password"
                value={formData.password}
                onChange={handleChange}
              />
            </div>
          </div>
          
          <div className="flex items-center my-2">
            <div className="flex-1 h-px bg-white/10"></div>
            <span className="px-4 text-sm font-medium text-text-muted uppercase tracking-wider">System Settings</span>
            <div className="flex-1 h-px bg-white/10"></div>
          </div>
          
          <div>
            <label className={formLabelClass} htmlFor="base_domain">Application Domain</label>
            <p className="text-xs text-text-muted mb-2">Used for SSO redirects (e.g. https://ipam.local)</p>
            <div className="relative">
              <input
                id="base_domain"
                name="base_domain"
                type="url"
                required
                className={formInputClass}
                placeholder="https://ipam.local"
                value={formData.base_domain}
                onChange={handleChange}
              />
            </div>
          </div>
          
          <div className="flex items-center gap-3 p-4 bg-black/20 border border-white/5 rounded-xl transition-all hover:bg-black/30 cursor-pointer" onClick={() => setFormData({ ...formData, enable_network_discovery: !formData.enable_network_discovery })}>
            <div className="relative flex items-center">
              <input
                id="enable_network_discovery"
                name="enable_network_discovery"
                type="checkbox"
                className="w-5 h-5 rounded border-white/20 bg-black/50 text-accent-primary focus:ring-accent-primary focus:ring-offset-bg-card"
                checked={formData.enable_network_discovery}
                onChange={(e) => setFormData({ ...formData, enable_network_discovery: e.target.checked })}
                onClick={(e) => e.stopPropagation()}
              />
            </div>
            <label htmlFor="enable_network_discovery" className="text-sm font-medium text-text-secondary cursor-pointer flex-1" onClick={(e) => e.stopPropagation()}>
              Enable Background Network Scanning
            </label>
          </div>

          <button
            type="submit"
            className={`${btnPrimaryClass} mt-4`}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="loader w-5 h-5 !border-2"></span>
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
