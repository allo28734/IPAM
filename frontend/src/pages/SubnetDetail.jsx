import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Settings, Trash2, Download, Upload, X, Activity } from 'lucide-react';
import api from '../lib/axios';

const SubnetDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [subnet, setSubnet] = useState(null);
  const [ips, setIps] = useState([]);
  const [utilization, setUtilization] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sweeping, setSweeping] = useState(false);
  const [sweepTaskId, setSweepTaskId] = useState(null);
  const [sweepStatus, setSweepStatus] = useState(null);
  const [error, setError] = useState(null);
  
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [assignForm, setAssignForm] = useState({ address: '', hostname: '', status: 'assigned', tags: {} });
  const [tagKey, setTagKey] = useState('');
  const [tagValue, setTagValue] = useState('');
  const [confirmRelease, setConfirmRelease] = useState(null);
  
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);

  const formatLargeNumber = (num) => {
    if (num === null || num === undefined) return '';
    if (num > 1e15) return num.toExponential(2);
    return num.toLocaleString();
  };
  
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

  useEffect(() => {
    let intervalId;
    
    const checkStatus = async () => {
      if (!sweepTaskId) return;
      try {
        const res = await api.get(`/subnets/sweep/status/${sweepTaskId}`);
        setSweepStatus(res.data.status);
        
        if (res.data.status === 'SUCCESS') {
          setSweeping(false);
          setSweepTaskId(null);
          clearInterval(intervalId);
          const result = res.data.result;
          if (result && !result.error) {
             alert(`Sweep completed! ${result.updated_count} IPs updated, ${result.conflict_count} new conflicts found.`);
          } else {
             alert(`Sweep completed with error: ${result?.error || 'Unknown error'}`);
          }
          fetchData();
        } else if (res.data.status === 'FAILURE') {
          setSweeping(false);
          setSweepTaskId(null);
          clearInterval(intervalId);
          alert('Sweep task failed.');
        }
      } catch (err) {
        console.error("Failed to fetch sweep status", err);
      }
    };

    if (sweeping && sweepTaskId) {
      intervalId = setInterval(checkStatus, 2000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [sweeping, sweepTaskId]);

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
      setAssignForm({ address: '', hostname: '', status: 'assigned', tags: {} });
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to assign IP.');
    }
  };

  const addTag = () => {
    if (tagKey.trim() && tagValue.trim()) {
      setAssignForm(prev => ({
        ...prev,
        tags: { ...prev.tags, [tagKey.trim()]: tagValue.trim() }
      }));
      setTagKey('');
      setTagValue('');
    }
  };

  const removeTag = (k) => {
    const newTags = { ...assignForm.tags };
    delete newTags[k];
    setAssignForm(prev => ({ ...prev, tags: newTags }));
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

  const handleExport = async () => {
    try {
      const response = await api.get(`/subnets/${id}/ips/export`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `subnet_${id}_ips.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to export IPs');
    }
  };

  const handleImport = async (e) => {
    e.preventDefault();
    if (!importFile) return;
    setImporting(true);
    setImportResult(null);
    const formData = new FormData();
    formData.append('file', importFile);
    try {
      const response = await api.post(`/subnets/${id}/ips/import`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setImportResult(response.data);
      fetchData();
    } catch (err) {
      setImportResult({ error: err.response?.data?.detail || 'Import failed' });
    } finally {
      setImporting(false);
      setImportFile(null);
    }
  };

  const handleSweep = async () => {
    try {
      setSweeping(true);
      setSweepStatus('PENDING');
      const response = await api.post(`/subnets/${id}/sweep`);
      setSweepTaskId(response.data.task_id);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to initiate sweep.');
      setSweeping(false);
      setSweepStatus(null);
      setSweepTaskId(null);
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
          <span className="badge badge-info" style={{ marginRight: '8px' }}>IPv{subnet.ip_version}</span>
          <span className="badge badge-info">{subnet.cidr}</span>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={handleExport}>
            <Download size={16} /> Export CSV
          </button>
          <button className="btn btn-secondary" onClick={() => { setIsImportModalOpen(true); setImportResult(null); }}>
            <Upload size={16} /> Import CSV
          </button>
          <button className="btn btn-secondary" onClick={handleSweep} disabled={sweeping}>
            <Activity size={16} className={sweeping ? 'animate-pulse' : ''} /> {sweeping ? `Sweeping... (${sweepStatus || 'Starting'})` : 'Sweep Subnet'}
          </button>
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
          <div className="stat-value">{formatLargeNumber(utilization?.total_capacity)}</div>
          <span className="stat-desc">Total usable IPs</span>
        </div>
        <div className="glass-card stat-card">
          <span className="stat-title">Available</span>
          <div className="stat-value" style={{ color: 'var(--success)' }}>{formatLargeNumber(utilization?.available_count)}</div>
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
                <th>Tags</th>
                <th>Assigned At</th>
                <th>Last Seen</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {ips.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    No IPs allocated in this subnet.
                  </td>
                </tr>
              ) : (
                ips.map(ip => (
                  <tr key={ip.id}>
                    <td style={{ fontWeight: 600 }}>{ip.address}</td>
                    <td>
                      <span className={`badge badge-${ip.status === 'assigned' ? 'success' : ip.status === 'conflict' ? 'danger' : ip.status === 'reserved' ? 'warning' : 'info'}`}>
                        {ip.status}
                      </span>
                    </td>
                    <td>{ip.hostname || '-'}</td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {ip.tags && Object.entries(ip.tags).map(([k, v]) => (
                          <span key={k} className="tag-chip">
                            <span className="tag-key">{k}:</span> {v}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>{new Date(ip.created_at).toLocaleString()}</td>
                    <td>
                      {ip.last_seen ? (
                        <span style={{ color: 'var(--success)' }}>
                          {new Date(ip.last_seen).toLocaleString()}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>Never</span>
                      )}
                    </td>
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
                
                <div className="form-group">
                  <label className="form-label">Custom Tags</label>
                  <div className="tag-builder-inputs">
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Key (e.g. server-type)"
                      value={tagKey}
                      onChange={(e) => setTagKey(e.target.value)}
                    />
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Value (e.g. database)"
                      value={tagValue}
                      onChange={(e) => setTagValue(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                    />
                    <button type="button" className="btn btn-secondary" onClick={addTag}>Add</button>
                  </div>
                  
                  {Object.keys(assignForm.tags).length > 0 && (
                    <div className="tag-list">
                      {Object.entries(assignForm.tags).map(([k, v]) => (
                        <span key={k} className="tag-chip">
                          <span className="tag-key">{k}:</span> {v}
                          <button type="button" className="tag-remove" onClick={() => removeTag(k)}>
                            <X size={12} />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
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

      {isImportModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">Bulk Import IPs</h2>
              <button className="modal-close" onClick={() => setIsImportModalOpen(false)}>×</button>
            </div>
            <form onSubmit={handleImport}>
              <div className="modal-body">
                {importResult?.error && (
                  <div className="badge badge-danger" style={{ display: 'block', marginBottom: '16px', padding: '8px' }}>
                    {importResult.error}
                  </div>
                )}
                {importResult && !importResult.error && (
                  <div className="glass-card" style={{ marginBottom: '16px', padding: '16px', backgroundColor: 'var(--bg-glass-card)' }}>
                    <h3 style={{ color: 'var(--success)', marginBottom: '8px' }}>Import Complete</h3>
                    <p>Successfully imported: {importResult.imported} IPs</p>
                    {importResult.errors?.length > 0 && (
                      <div style={{ marginTop: '12px' }}>
                        <p style={{ color: 'var(--danger)', fontWeight: 600 }}>Errors ({importResult.errors.length}):</p>
                        <ul style={{ marginTop: '4px', paddingLeft: '20px', fontSize: '0.9rem', color: 'var(--text-muted)', maxHeight: '150px', overflowY: 'auto' }}>
                          {importResult.errors.map((err, i) => <li key={i}>{err}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
                <div className="form-group">
                  <label className="form-label">CSV File</label>
                  <input
                    type="file"
                    accept=".csv"
                    className="form-input"
                    style={{ padding: '8px' }}
                    onChange={(e) => setImportFile(e.target.files[0])}
                    required
                  />
                  <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: '8px' }}>
                    CSV must include an 'address' column. Optional: 'status', 'hostname', 'description', 'tags' (as JSON).
                  </small>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsImportModalOpen(false)}>
                  Close
                </button>
                <button type="submit" className="btn btn-primary" disabled={importing || !importFile}>
                  {importing ? 'Importing...' : 'Upload & Import'}
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
