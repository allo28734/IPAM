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

  // Shared classes
  const glassCardClass = "bg-bg-card backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-md transition-all hover:shadow-lg hover:border-white/20";
  const btnPrimaryClass = "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm cursor-pointer transition-all border-none outline-none bg-accent-primary text-white shadow-[0_4px_12px_var(--color-accent-glow)] hover:bg-accent-hover hover:-translate-y-0.5 hover:shadow-[0_6px_16px_var(--color-accent-glow)]";
  const btnSecondaryClass = "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm cursor-pointer transition-all border border-white/10 outline-none bg-bg-tertiary text-text-primary hover:bg-white/10 hover:border-white/20";
  const formInputClass = "w-full px-4 py-3 bg-black/20 border border-white/10 rounded-xl text-text-primary text-sm transition-all focus:outline-none focus:border-accent-primary focus:ring-3 focus:ring-indigo-500/20";
  const formLabelClass = "block mb-2 text-sm font-medium text-text-secondary";
  const formGroupClass = "mb-5";
  const modalOverlayClass = "fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100] animate-[fadeIn_0.2s_forwards]";
  const modalContentClass = "bg-bg-secondary border border-white/10 rounded-2xl w-full max-w-[500px] shadow-2xl transform scale-95 animate-[scaleIn_0.2s_0.05s_forwards]";
  const modalHeaderClass = "p-5 px-6 border-b border-white/10 flex justify-between items-center";
  const modalTitleClass = "text-lg font-semibold";
  const modalCloseClass = "bg-transparent border-none text-text-secondary cursor-pointer transition-all hover:text-text-primary flex items-center";
  const modalBodyClass = "p-6";
  const modalFooterClass = "px-6 py-4 border-t border-white/10 flex justify-end gap-3 bg-black/20 rounded-b-2xl";
  const tableContainerClass = "w-full overflow-x-auto rounded-xl border border-white/10 bg-bg-secondary";
  const tableClass = "w-full border-collapse text-left";
  const thClass = "p-4 text-xs font-semibold uppercase text-text-secondary border-b border-white/10 bg-black/20 tracking-wider";
  const tdClass = "p-4 text-sm border-b border-white/5 align-middle group-last:border-none";
  const trClass = "transition-all hover:bg-white/5 group";
  const badgeInfoClass = "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-info-bg text-info border border-info/20";
  const badgeDangerClass = "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-danger-bg text-danger border border-danger/20";
  const tagChipClass = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-500/15 text-text-primary border border-indigo-500/30 backdrop-blur-sm m-0.5";
  const tagKeyClass = "text-text-secondary font-semibold";
  const tagRemoveClass = "cursor-pointer text-text-muted transition-all hover:text-danger flex items-center";

  const renderSubnetRow = (subnet, depth = 0) => {
    const hasChildren = subnet.children && subnet.children.length > 0;
    const isExpanded = expandedIds.has(subnet.id);
    
    return (
      <React.Fragment key={subnet.id}>
        <tr className={trClass}>
          <td className={tdClass} style={{ paddingLeft: `${16 + depth * 24}px`, fontWeight: 500 }}>
            <div className="flex items-center gap-2">
              {hasChildren ? (
                <button 
                  onClick={() => toggleExpand(subnet.id)}
                  className="bg-transparent border-none text-text-secondary cursor-pointer flex items-center"
                >
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </button>
              ) : <span className="w-4"></span>}
              {subnet.name}
            </div>
          </td>
          <td className={tdClass}>
            <span className={`${badgeInfoClass} mr-2`}>IPv{subnet.ip_version}</span>
            <span className={badgeInfoClass}>{subnet.cidr}</span>
          </td>
          <td className={tdClass}>{subnet.gateway || '-'}</td>
          <td className={tdClass}>{subnet.vlan_id || '-'}</td>
          <td className={tdClass}>
            <div className="flex flex-wrap gap-1">
              {subnet.tags && Object.entries(subnet.tags).map(([k, v]) => (
                <span key={k} className={tagChipClass}>
                  <span className={tagKeyClass}>{k}:</span> {v}
                </span>
              ))}
            </div>
          </td>
          <td className={tdClass}>
            <Link to={`/subnets/${subnet.id}`} className={`${btnSecondaryClass} !px-3 !py-1.5 !text-xs`}>
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
    <div className="flex-1 p-8">
      <header className="h-[var(--spacing-header)] bg-[#0f1115]/80 backdrop-blur-xl border-b border-white/10 flex items-center justify-between px-8 sticky top-0 z-30 -mt-8 -mx-8 mb-8">
        <h1 className="text-xl font-semibold">Manage Subnets</h1>
        <div className="flex items-center gap-4">
          <button className={btnSecondaryClass} onClick={handleExport}>
            <Download size={16} /> Export CSV
          </button>
          <button className={btnSecondaryClass} onClick={() => { setIsImportModalOpen(true); setImportResult(null); }}>
            <Upload size={16} /> Import CSV
          </button>
          <button className={btnPrimaryClass} onClick={() => setIsModalOpen(true)}>
            <Plus size={16} /> New Subnet
          </button>
        </div>
      </header>

      {error && !isModalOpen && (
        <div className={`${glassCardClass} ${badgeDangerClass} !block mb-6`}>
          {error}
        </div>
      )}

      <div className={`${glassCardClass} mb-6`}>
        <div className="relative w-[300px]">
          <Search size={18} className="absolute left-3 top-3.5 text-text-muted" />
          <input
            type="text"
            className={`${formInputClass} !pl-10`}
            placeholder="Search subnets..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className={tableContainerClass}>
        {loading ? (
          <div className="p-8 text-center">
            <div className="loader w-6 h-6 mx-auto"></div>
          </div>
        ) : (
          <table className={tableClass}>
            <thead>
              <tr>
                <th className={thClass}>Name</th>
                <th className={thClass}>Network (CIDR)</th>
                <th className={thClass}>Gateway</th>
                <th className={thClass}>VLAN</th>
                <th className={thClass}>Tags</th>
                <th className={thClass}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tree.length === 0 ? (
                <tr>
                  <td colSpan="6" className="text-center p-8 text-text-muted">
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
        <div className={modalOverlayClass}>
          <div className={modalContentClass}>
            <div className={modalHeaderClass}>
              <h2 className={modalTitleClass}>Create Subnet</h2>
              <button className={modalCloseClass} onClick={() => setIsModalOpen(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleCreate}>
              <div className={modalBodyClass}>
                {error && (
                  <div className={`${badgeDangerClass} !block mb-4`}>
                    {error}
                  </div>
                )}
                
                <div className={formGroupClass}>
                  <label className={formLabelClass}>Parent Subnet (Optional)</label>
                  <select 
                    className={formInputClass}
                    value={formData.parent_id}
                    onChange={(e) => setFormData({ ...formData, parent_id: e.target.value })}
                  >
                    <option value="">-- None (Root Subnet) --</option>
                    {subnets.map(s => (
                      <option key={s.id} value={s.id}>{s.name} ({s.cidr})</option>
                    ))}
                  </select>
                </div>

                <div className={formGroupClass}>
                  <label className={formLabelClass}>Discovery Profile (Optional)</label>
                  <select 
                    className={formInputClass}
                    value={formData.discovery_profile_id}
                    onChange={(e) => setFormData({ ...formData, discovery_profile_id: e.target.value })}
                  >
                    <option value="">-- None --</option>
                    {profiles.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>

                <div className={formGroupClass}>
                  <label className={formLabelClass}>Name *</label>
                  <input
                    required
                    type="text"
                    className={formInputClass}
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Office LAN"
                  />
                </div>
                <div className={formGroupClass}>
                  <label className={formLabelClass}>Network CIDR *</label>
                  <input
                    required
                    type="text"
                    className={formInputClass}
                    value={formData.cidr}
                    onChange={(e) => setFormData({ ...formData, cidr: e.target.value })}
                    placeholder="e.g. 10.0.1.0/24"
                  />
                </div>
                <div className="flex gap-4">
                  <div className={`${formGroupClass} flex-1`}>
                    <label className={formLabelClass}>Gateway IP (Optional)</label>
                    <input
                      type="text"
                      className={formInputClass}
                      value={formData.gateway}
                      onChange={(e) => setFormData({ ...formData, gateway: e.target.value })}
                      placeholder="e.g. 10.0.1.1"
                    />
                  </div>
                  <div className={`${formGroupClass} flex-1`}>
                    <label className={formLabelClass}>VLAN ID (Optional)</label>
                    <input
                      type="number"
                      className={formInputClass}
                      value={formData.vlan_id}
                      onChange={(e) => setFormData({ ...formData, vlan_id: e.target.value })}
                      placeholder="1-4095"
                    />
                  </div>
                </div>

                <div className={formGroupClass}>
                  <label className={formLabelClass}>Custom Tags</label>
                  <div className="flex gap-2 mb-3">
                    <input
                      type="text"
                      className={formInputClass}
                      placeholder="Key (e.g. env)"
                      value={tagKey}
                      onChange={(e) => setTagKey(e.target.value)}
                    />
                    <input
                      type="text"
                      className={formInputClass}
                      placeholder="Value (e.g. prod)"
                      value={tagValue}
                      onChange={(e) => setTagValue(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                    />
                    <button type="button" className={btnSecondaryClass} onClick={addTag}>Add</button>
                  </div>
                  
                  {Object.keys(formData.tags).length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2 p-2 bg-black/20 rounded-xl min-h-[44px]">
                      {Object.entries(formData.tags).map(([k, v]) => (
                        <span key={k} className={tagChipClass}>
                          <span className={tagKeyClass}>{k}:</span> {v}
                          <button type="button" className={tagRemoveClass} onClick={() => removeTag(k)}>
                            <X size={12} />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

              </div>
              <div className={modalFooterClass}>
                <button type="button" className={btnSecondaryClass} onClick={() => setIsModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className={btnPrimaryClass}>
                  Create Subnet
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {isImportModalOpen && (
        <div className={modalOverlayClass}>
          <div className={modalContentClass}>
            <div className={modalHeaderClass}>
              <h2 className={modalTitleClass}>Bulk Import Subnets</h2>
              <button className={modalCloseClass} onClick={() => setIsImportModalOpen(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleImport}>
              <div className={modalBodyClass}>
                {importResult?.error && (
                  <div className={`${badgeDangerClass} !block mb-4`}>
                    {importResult.error}
                  </div>
                )}
                {importResult && !importResult.error && (
                  <div className={`${glassCardClass} mb-4`}>
                    <h3 className="text-success mb-2 font-semibold">Import Complete</h3>
                    <p>Successfully imported: {importResult.imported} subnets</p>
                    {importResult.errors?.length > 0 && (
                      <div className="mt-3">
                        <p className="text-danger font-semibold">Errors ({importResult.errors.length}):</p>
                        <ul className="mt-1 pl-5 text-sm text-text-muted max-h-[150px] overflow-y-auto list-disc">
                          {importResult.errors.map((err, i) => <li key={i}>{err}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
                <div className={formGroupClass}>
                  <label className={formLabelClass}>CSV File</label>
                  <input
                    type="file"
                    accept=".csv"
                    className={`${formInputClass} !p-2`}
                    onChange={(e) => setImportFile(e.target.files[0])}
                    required
                  />
                  <small className="text-text-muted block mt-2 text-xs">
                    CSV must include 'name' and 'cidr' columns. Optional: 'gateway', 'vlan_id', 'description', 'parent_id', 'tags' (as JSON).
                  </small>
                </div>
              </div>
              <div className={modalFooterClass}>
                <button type="button" className={btnSecondaryClass} onClick={() => setIsImportModalOpen(false)}>
                  Close
                </button>
                <button type="submit" className={btnPrimaryClass} disabled={importing || !importFile}>
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
