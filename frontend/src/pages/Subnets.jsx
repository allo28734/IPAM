import React, { useState, useEffect } from 'react';
import { Plus, Search, Download, Upload, ChevronRight, ChevronDown, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../lib/axios';

const buildSubnetTree = (subnets) => {
  const map = {};
  const roots = [];
  subnets.forEach(s => {
    map[s.id] = { ...s, children: [] };
  });
  subnets.forEach(s => {
    if (s.parent_id && map[s.parent_id]) {
      map[s.parent_id].children.push(map[s.id]);
    } else {
      roots.push(map[s.id]);
    }
  });
  return roots;
};

const Subnets = () => {
  const [subnets, setSubnets] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({ name: '', cidr: '', gateway: '', vlan_id: '', description: '', parent_id: '', discovery_profile_id: '', tags: {} });
  const [error, setError] = useState(null);
  
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);

  const [expandedIds, setExpandedIds] = useState(new Set());
  const [tagKey, setTagKey] = useState('');
  const [tagValue, setTagValue] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [subnetsRes, profilesRes] = await Promise.all([
        api.get('/subnets', { params: { search } }),
        api.get('/discovery-profiles').catch(() => ({ data: [] }))
      ]);
      setSubnets(subnetsRes.data.items || subnetsRes.data);
      setProfiles(profilesRes.data || []);
    } catch (err) {
      console.error('Failed to fetch data:', err);
      setError('Failed to load subnets.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchData();
    }, 300);
    return () => clearTimeout(delayDebounceFn);
  }, [search]);

  const toggleExpand = (id) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const payload = { ...formData };
      if (!payload.gateway) delete payload.gateway;
      if (!payload.vlan_id) delete payload.vlan_id;
      else payload.vlan_id = parseInt(payload.vlan_id, 10);
      if (!payload.description) delete payload.description;
      if (!payload.parent_id) delete payload.parent_id;
      else payload.parent_id = parseInt(payload.parent_id, 10);
      
      if (!payload.discovery_profile_id) delete payload.discovery_profile_id;
      else payload.discovery_profile_id = parseInt(payload.discovery_profile_id, 10);

      await api.post('/subnets', payload);
      setIsModalOpen(false);
      setFormData({ name: '', cidr: '', gateway: '', vlan_id: '', description: '', parent_id: '', discovery_profile_id: '', tags: {} });
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create subnet. Check CIDR overlaps or format.');
    }
  };

  const addTag = () => {
    if (tagKey.trim() && tagValue.trim()) {
      setFormData(prev => ({
        ...prev,
        tags: { ...prev.tags, [tagKey.trim()]: tagValue.trim() }
      }));
      setTagKey('');
      setTagValue('');
    }
  };

  const removeTag = (k) => {
    const newTags = { ...formData.tags };
    delete newTags[k];
    setFormData(prev => ({ ...prev, tags: newTags }));
  };

  const handleExport = async () => {
    try {
      const response = await api.get('/subnets/export', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'subnets.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to export subnets');
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
      const response = await api.post('/subnets/import', formData, {
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

  const renderSubnetRow = (subnet, depth = 0) => {
    const hasChildren = subnet.children && subnet.children.length > 0;
    const isExpanded = expandedIds.has(subnet.id);
    
    return (
      <React.Fragment key={subnet.id}>
        <tr>
          <td style={{ paddingLeft: `${16 + depth * 24}px`, fontWeight: 500 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {hasChildren ? (
                <button 
                  onClick={() => toggleExpand(subnet.id)}
                  style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                >
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </button>
              ) : <span style={{ width: 16 }}></span>}
              {subnet.name}
            </div>
          </td>
          <td>
            <span className="badge badge-info" style={{ marginRight: '8px' }}>IPv{subnet.ip_version}</span>
            <span className="badge badge-info">{subnet.cidr}</span>
          </td>
          <td>{subnet.gateway || '-'}</td>
          <td>{subnet.vlan_id || '-'}</td>
          <td>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              {subnet.tags && Object.entries(subnet.tags).map(([k, v]) => (
                <span key={k} className="tag-chip">
                  <span className="tag-key">{k}:</span> {v}
                </span>
              ))}
            </div>
          </td>
          <td>
            <Link to={`/subnets/${subnet.id}`} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
              Manage
            </Link>
          </td>
        </tr>
        {isExpanded && hasChildren && subnet.children.map(child => renderSubnetRow(child, depth + 1))}
      </React.Fragment>
    );
  };

  const tree = buildSubnetTree(subnets);

  return (
    <div className="content-area">
      <header className="header" style={{ margin: '-32px -32px 32px -32px' }}>
        <h1 className="page-title">Manage Subnets</h1>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={handleExport}>
            <Download size={16} /> Export CSV
          </button>
          <button className="btn btn-secondary" onClick={() => { setIsImportModalOpen(true); setImportResult(null); }}>
            <Upload size={16} /> Import CSV
          </button>
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
                <th>Tags</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tree.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    No subnets found.
                  </td>
                </tr>
              ) : (
                tree.map(node => renderSubnetRow(node, 0))
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
              <button className="modal-close" onClick={() => setIsModalOpen(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="modal-body">
                {error && (
                  <div className="badge badge-danger" style={{ display: 'block', marginBottom: '16px', padding: '8px' }}>
                    {error}
                  </div>
                )}
                
                <div className="form-group">
                  <label className="form-label">Parent Subnet (Optional)</label>
                  <select 
                    className="form-input"
                    value={formData.parent_id}
                    onChange={(e) => setFormData({ ...formData, parent_id: e.target.value })}
                  >
                    <option value="">-- None (Root Subnet) --</option>
                    {subnets.map(s => (
                      <option key={s.id} value={s.id}>{s.name} ({s.cidr})</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Discovery Profile (Optional)</label>
                  <select 
                    className="form-input"
                    value={formData.discovery_profile_id}
                    onChange={(e) => setFormData({ ...formData, discovery_profile_id: e.target.value })}
                  >
                    <option value="">-- None --</option>
                    {profiles.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>

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
                <div style={{ display: 'flex', gap: '16px' }}>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label className="form-label">Gateway IP (Optional)</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.gateway}
                      onChange={(e) => setFormData({ ...formData, gateway: e.target.value })}
                      placeholder="e.g. 10.0.1.1"
                    />
                  </div>
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

                <div className="form-group">
                  <label className="form-label">Custom Tags</label>
                  <div className="tag-builder-inputs">
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Key (e.g. env)"
                      value={tagKey}
                      onChange={(e) => setTagKey(e.target.value)}
                    />
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Value (e.g. prod)"
                      value={tagValue}
                      onChange={(e) => setTagValue(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                    />
                    <button type="button" className="btn btn-secondary" onClick={addTag}>Add</button>
                  </div>
                  
                  {Object.keys(formData.tags).length > 0 && (
                    <div className="tag-list">
                      {Object.entries(formData.tags).map(([k, v]) => (
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

      {isImportModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">Bulk Import Subnets</h2>
              <button className="modal-close" onClick={() => setIsImportModalOpen(false)}><X size={20} /></button>
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
                    <p>Successfully imported: {importResult.imported} subnets</p>
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
                    CSV must include 'name' and 'cidr' columns. Optional: 'gateway', 'vlan_id', 'description', 'parent_id', 'tags' (as JSON).
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

export default Subnets;
