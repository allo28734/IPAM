import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';

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
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-10 rounded-xl shadow-lg border border-gray-100">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Welcome to IPAM
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Complete the Zero-Touch Setup
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 text-red-500 p-3 rounded text-sm text-center">
              {error}
            </div>
          )}
          <div className="rounded-md shadow-sm space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700" htmlFor="username">Admin Username</label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className="appearance-none rounded relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm mt-1"
                placeholder="Admin username"
                value={formData.username}
                onChange={handleChange}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700" htmlFor="email">Admin Email</label>
              <input
                id="email"
                name="email"
                type="email"
                required
                className="appearance-none rounded relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm mt-1"
                placeholder="admin@example.com"
                value={formData.email}
                onChange={handleChange}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700" htmlFor="password">Admin Password</label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="appearance-none rounded relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm mt-1"
                placeholder="Secure password"
                value={formData.password}
                onChange={handleChange}
              />
            </div>
            <hr className="my-4" />
            <div>
              <label className="block text-sm font-medium text-gray-700" htmlFor="base_domain">Application Domain</label>
              <p className="text-xs text-gray-500 mb-1">Used for SSO redirects (e.g. https://ipam.local)</p>
              <input
                id="base_domain"
                name="base_domain"
                type="url"
                required
                className="appearance-none rounded relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="https://ipam.local"
                value={formData.base_domain}
                onChange={handleChange}
              />
            </div>
            <div className="flex items-center">
              <input
                id="enable_network_discovery"
                name="enable_network_discovery"
                type="checkbox"
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                checked={formData.enable_network_discovery}
                onChange={(e) => setFormData({ ...formData, enable_network_discovery: e.target.checked })}
              />
              <label htmlFor="enable_network_discovery" className="ml-2 block text-sm text-gray-900">
                Enable Background Network Scanning (Requires 'discovery' Docker profile)
              </label>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-blue-400"
            >
              {loading ? 'Setting up...' : 'Complete Setup'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
