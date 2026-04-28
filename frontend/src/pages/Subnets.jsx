import { useState, useEffect } from 'react';
import { Plus, Search, Network } from 'lucide-react';
import api from '../lib/axios';

const Subnets = () => {
  const [subnets, setSubnets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({ name: '', cidr: '', gateway: '', vlan_id: '', description: '' });
  const [error, setError] = useState(null);

  const fetchSubnets = async () => {
    setLoading(true);
    try {
      const response = await api.get('/subnets', { params: { search } });
      setSubnets(response.data.items);
    } catch (err) {
      console.error('Failed to fetch subnets:', err);
      setError('Failed to load subnets.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchSubnets();
    }, 300);
    return () => clearTimeout(delayDebounceFn);
  }, [search]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      // Clean up empty optional fields
      const payload = { ...formData };
      if (!payload.gateway) delete payload.gateway;
      if (!payload.vlan_id) delete payload.vlan_id;
      else payload.vlan_id = parseInt(payload.vlan_id, 10);
      if (!payload.description) delete payload.description;

      await api.post('/subnets', payload);
      setIsModalOpen(false);
      setFormData({ name: '', cidr: '', gateway: '', vlan_id: '', description: '' });
      fetchSubnets();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create subnet. Check CIDR overlaps or format.');
    }
  };

  return (
    <div className="content-area">
      <header className="header" style={{ margin: '-32px -32px 32px -32px' }}>
        <h1 className="page-title">Manage Subnets</h1>
        <div className="header-actions">
          <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
            <Plus size={16} /> New Subnet
          </button>
        </div>
      </header>

      {error && !isModalOpen && (
        <div className="glass-card badge-danger" style={{ marginBottom: '24px', padding: '16px' }}>
          {error}
        </div>
      )}

      <div className="glass-card" style={{ marginBottom: '24px', padding: '16px 24px' }}>
        <div style={{ position: 'relative', width: '300px' }}>
          <Search size={18} style={{ position: 'absolute', left: '12px', top: '14px', color: 'var(--text-muted)' }} />
          <input
            type="text"
            className="form-input"
            placeholder="Search subnets..."
            style={{ paddingLeft: '40px' }}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="table-container">
        {loading ? (
          <div style={{ padding: '32px', textAlign: 'center' }}>
            <div className="loader" style={{ margin: '0 auto' }}></div>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Network (CIDR)</th>
                <th>Gateway</th>
                <th>VLAN</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {subnets.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    No subnets found.
                  </td>
                </tr>
              ) : (
                subnets.map((subnet) => (
                  <tr key={subnet.id}>
                    <td style={{ fontWeight: 500 }}>{subnet.name}</td>
                    <td>
                      <span className="badge badge-info">{subnet.cidr}</span>
                    </td>
                    <td>{subnet.gateway || '-'}</td>
                    <td>{subnet.vlan_id || '-'}</td>
                    <td>
                      <a href={`/subnets/${subnet.id}`} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                        Manage IPs
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">Create Subnet</h2>
              <button className="modal-close" onClick={() => setIsModalOpen(false)}>×</button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="modal-body">
                {error && (
                  <div className="badge badge-danger" style={{ display: 'block', marginBottom: '16px', padding: '8px' }}>
                    {error}
                  </div>
                )}
                <div className="form-group">
                  <label className="form-label">Name *</label>
                  <input
                    required
                    type="text"
                    className="form-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Office LAN"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Network CIDR *</label>
                  <input
                    required
                    type="text"
                    className="form-input"
                    value={formData.cidr}
                    onChange={(e) => setFormData({ ...formData, cidr: e.target.value })}
                    placeholder="e.g. 10.0.1.0/24"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Gateway IP (Optional)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.gateway}
                    onChange={(e) => setFormData({ ...formData, gateway: e.target.value })}
                    placeholder="e.g. 10.0.1.1"
                  />
                </div>
                <div style={{ display: 'flex', gap: '16px' }}>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label className="form-label">VLAN ID (Optional)</label>
                    <input
                      type="number"
                      className="form-input"
                      value={formData.vlan_id}
                      onChange={(e) => setFormData({ ...formData, vlan_id: e.target.value })}
                      placeholder="1-4095"
                    />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create Subnet
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Subnets;
