import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Settings, Trash2 } from 'lucide-react';
import api from '../lib/axios';

const SubnetDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [subnet, setSubnet] = useState(null);
  const [ips, setIps] = useState([]);
  const [utilization, setUtilization] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [assignForm, setAssignForm] = useState({ address: '', hostname: '', status: 'assigned' });
  const [confirmRelease, setConfirmRelease] = useState(null);
  
  const fetchData = async () => {
    try {
      setLoading(true);
      const [subnetRes, ipsRes, utilRes] = await Promise.all([
        api.get(`/subnets/${id}`),
        api.get(`/subnets/${id}/ips`),
        api.get(`/subnets/${id}/utilization`)
      ]);
      setSubnet(subnetRes.data);
      setIps(ipsRes.data.items);
      setUtilization(utilRes.data);
    } catch (err) {
      console.error('Failed to load subnet details:', err);
      setError('Failed to load subnet details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  const handleAutoAllocate = async () => {
    try {
      await api.post(`/subnets/${id}/ips/next-available`, { hostname: 'Auto-Allocated' });
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to auto-allocate IP.');
    }
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...assignForm };
      if (!payload.hostname) delete payload.hostname;
      await api.post(`/subnets/${id}/ips`, payload);
      setIsAssignModalOpen(false);
      setAssignForm({ address: '', hostname: '', status: 'assigned' });
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to assign IP.');
    }
  };

  const handleRelease = async (ipId) => {
    try {
      await api.post(`/ips/${ipId}/release`);
      setConfirmRelease(null);
      fetchData();
    } catch (err) {
      alert('Failed to release IP');
    }
  };

  if (loading) return <div className="loader" style={{ margin: '100px auto' }}></div>;
  if (error) return <div className="content-area"><div className="glass-card badge-danger">{error}</div></div>;
  if (!subnet) return null;

  return (
    <div className="content-area">
      <header className="header" style={{ margin: '-32px -32px 32px -32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/subnets')} style={{ padding: '8px' }}>
            <ArrowLeft size={16} />
          </button>
          <h1 className="page-title">{subnet.name}</h1>
          <span className="badge badge-info">{subnet.cidr}</span>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={handleAutoAllocate}>
            <Settings size={16} /> Auto-Allocate Next IP
          </button>
          <button className="btn btn-primary" onClick={() => setIsAssignModalOpen(true)}>
            <Plus size={16} /> Assign IP
          </button>
        </div>
      </header>

      <div className="stats-grid" style={{ marginBottom: '24px' }}>
        <div className="glass-card stat-card">
          <span className="stat-title">Capacity</span>
          <div className="stat-value">{utilization?.total_capacity}</div>
          <span className="stat-desc">Total usable IPs</span>
        </div>
        <div className="glass-card stat-card">
          <span className="stat-title">Available</span>
          <div className="stat-value" style={{ color: 'var(--success)' }}>{utilization?.available_count}</div>
          <span className="stat-desc">Free to allocate</span>
        </div>
        <div className="glass-card stat-card">
          <span className="stat-title">Utilization</span>
          <div className="stat-value">{utilization?.utilization_percent.toFixed(1)}%</div>
          <div className="progress-bg">
            <div 
              className="progress-bar" 
              style={{ width: `${utilization?.utilization_percent}%` }}
            ></div>
          </div>
        </div>
      </div>

      <div className="glass-card">
        <h2 style={{ marginBottom: '16px', fontSize: '1.1rem' }}>Allocated IP Addresses</h2>
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Address</th>
                <th>Status</th>
                <th>Hostname</th>
                <th>Assigned At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {ips.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    No IPs allocated in this subnet.
                  </td>
                </tr>
              ) : (
                ips.map(ip => (
                  <tr key={ip.id}>
                    <td style={{ fontWeight: 600 }}>{ip.address}</td>
                    <td>
                      <span className={`badge badge-${ip.status === 'assigned' ? 'success' : ip.status === 'reserved' ? 'warning' : 'info'}`}>
                        {ip.status}
                      </span>
                    </td>
                    <td>{ip.hostname || '-'}</td>
                    <td>{new Date(ip.created_at).toLocaleString()}</td>
                    <td>
                      {confirmRelease === ip.id ? (
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button className="btn btn-danger" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => handleRelease(ip.id)}>
                            Confirm
                          </button>
                          <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => setConfirmRelease(null)}>
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => setConfirmRelease(ip.id)}>
                          Release
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isAssignModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">Assign IP Address</h2>
              <button className="modal-close" onClick={() => setIsAssignModalOpen(false)}>×</button>
            </div>
            <form onSubmit={handleAssign}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">IP Address *</label>
                  <input
                    required
                    type="text"
                    className="form-input"
                    value={assignForm.address}
                    onChange={(e) => setAssignForm({ ...assignForm, address: e.target.value })}
                    placeholder={`e.g. ${utilization?.first_usable_ip}`}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Hostname (Optional)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={assignForm.hostname}
                    onChange={(e) => setAssignForm({ ...assignForm, hostname: e.target.value })}
                    placeholder="e.g. server-01"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Status</label>
                  <select 
                    className="form-input" 
                    value={assignForm.status}
                    onChange={(e) => setAssignForm({ ...assignForm, status: e.target.value })}
                  >
                    <option value="assigned">Assigned</option>
                    <option value="reserved">Reserved</option>
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsAssignModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Assign IP
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SubnetDetail;
