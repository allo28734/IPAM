import React, { useState, useEffect, useCallback } from 'react';
import { Plus, X, Plug, RefreshCw, CheckCircle, XCircle, AlertTriangle, Trash2, Settings, Zap, Clock } from 'lucide-react';
import api from '../lib/axios';

// Vendor display metadata
const VENDOR_META = {
  meraki: { label: 'Cisco Meraki', color: '#00D474', icon: '🌐' },
  fortigate: { label: 'Fortinet FortiGate', color: '#EE3124', icon: '🛡️' },
  aruba_central: { label: 'Aruba Central', color: '#FF8300', icon: '📡' },
  paloalto: { label: 'Palo Alto Networks', color: '#FA582D', icon: '🔥' },
};

const STATUS_STYLES = {
  success: { bg: 'bg-success-bg', text: 'text-success', border: 'border-success/20', label: 'Synced' },
  failed: { bg: 'bg-danger-bg', text: 'text-danger', border: 'border-danger/20', label: 'Failed' },
  in_progress: { bg: 'bg-warning-bg', text: 'text-warning', border: 'border-warning/20', label: 'Syncing...' },
  never: { bg: 'bg-white/5', text: 'text-text-muted', border: 'border-white/10', label: 'Never synced' },
};

const Integrations = () => {
  const [providers, setProviders] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState(null);
  const [error, setError] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [syncingIds, setSyncingIds] = useState(new Set());
  const [testingIds, setTestingIds] = useState(new Set());

  const emptyForm = {
    name: '', vendor: '', base_url: '', api_key: '',
    username: '', password: '', extra_config: {},
    auto_create_subnets: false, is_enabled: true,
  };
  const [formData, setFormData] = useState(emptyForm);

  // Shared Tailwind classes (consistent with existing pages)
  const glassCardClass = "bg-bg-card backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-md transition-all hover:shadow-lg hover:border-white/20";
  const btnPrimaryClass = "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm cursor-pointer transition-all border-none outline-none bg-accent-primary text-white shadow-[0_4px_12px_var(--color-accent-glow)] hover:bg-accent-hover hover:-translate-y-0.5 hover:shadow-[0_6px_16px_var(--color-accent-glow)]";
  const btnSecondaryClass = "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm cursor-pointer transition-all border border-white/10 outline-none bg-bg-tertiary text-text-primary hover:bg-white/10 hover:border-white/20";
  const btnDangerClass = "inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl font-medium text-sm cursor-pointer transition-all border border-danger/30 outline-none bg-danger-bg text-danger hover:bg-danger/20";
  const btnSuccessClass = "inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl font-medium text-sm cursor-pointer transition-all border border-success/30 outline-none bg-success-bg text-success hover:bg-success/20";
  const formInputClass = "w-full px-4 py-3 bg-black/20 border border-white/10 rounded-xl text-text-primary text-sm transition-all focus:outline-none focus:border-accent-primary focus:ring-3 focus:ring-indigo-500/20";
  const formLabelClass = "block mb-2 text-sm font-medium text-text-secondary";
  const formGroupClass = "mb-5";
  const modalOverlayClass = "fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100] animate-[fadeIn_0.2s_forwards]";
  const modalContentClass = "bg-bg-secondary border border-white/10 rounded-2xl w-full max-w-[600px] shadow-2xl transform scale-95 animate-[scaleIn_0.2s_0.05s_forwards] max-h-[90vh] overflow-y-auto";
  const modalHeaderClass = "p-5 px-6 border-b border-white/10 flex justify-between items-center sticky top-0 bg-bg-secondary z-10";
  const modalTitleClass = "text-lg font-semibold";
  const modalCloseClass = "bg-transparent border-none text-text-secondary cursor-pointer transition-all hover:text-text-primary flex items-center";
  const modalBodyClass = "p-6";
  const modalFooterClass = "px-6 py-4 border-t border-white/10 flex justify-end gap-3 bg-black/20 rounded-b-2xl sticky bottom-0";

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [providersRes, vendorsRes] = await Promise.all([
        api.get('/integrations'),
        api.get('/integrations/vendors'),
      ]);
      setProviders(providersRes.data.items || []);
      setVendors(vendorsRes.data || []);
    } catch (err) {
      console.error('Failed to fetch integrations:', err);
      setError('Failed to load integrations.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const selectedVendorMeta = vendors.find(v => v.id === formData.vendor);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const payload = { ...formData };
      if (!payload.base_url) delete payload.base_url;
      if (!payload.api_key) delete payload.api_key;
      if (!payload.username) delete payload.username;
      if (!payload.password) delete payload.password;
      if (Object.keys(payload.extra_config).length === 0) delete payload.extra_config;
      await api.post('/integrations', payload);
      setIsModalOpen(false);
      setFormData(emptyForm);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create integration.');
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const payload = { ...formData };
      // Only send fields that have values
      Object.keys(payload).forEach(k => {
        if (payload[k] === '' || payload[k] === null || payload[k] === undefined) {
          delete payload[k];
        }
      });
      if (payload.extra_config && Object.keys(payload.extra_config).length === 0) {
        delete payload.extra_config;
      }
      await api.put(`/integrations/${editingProvider.id}`, payload);
      setIsEditModalOpen(false);
      setEditingProvider(null);
      setFormData(emptyForm);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update integration.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this integration?')) return;
    try {
      await api.delete(`/integrations/${id}`);
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete integration.');
    }
  };

  const handleTestConnection = async (id) => {
    setTestingIds(prev => new Set(prev).add(id));
    setTestResults(prev => ({ ...prev, [id]: null }));
    try {
      const res = await api.post(`/integrations/${id}/test`);
      setTestResults(prev => ({ ...prev, [id]: res.data }));
    } catch (err) {
      setTestResults(prev => ({ ...prev, [id]: { ok: false, message: err.response?.data?.detail || 'Test failed' } }));
    } finally {
      setTestingIds(prev => { const next = new Set(prev); next.delete(id); return next; });
    }
  };

  const handleSync = async (id) => {
    setSyncingIds(prev => new Set(prev).add(id));
    try {
      await api.post(`/integrations/${id}/sync`);
      // Poll for update after short delay
      setTimeout(() => {
        fetchData();
        setSyncingIds(prev => { const next = new Set(prev); next.delete(id); return next; });
      }, 3000);
    } catch (err) {
      alert(err.response?.data?.detail || 'Sync failed');
      setSyncingIds(prev => { const next = new Set(prev); next.delete(id); return next; });
    }
  };

  const openEditModal = (provider) => {
    setEditingProvider(provider);
    setFormData({
      name: provider.name,
      vendor: provider.vendor,
      base_url: provider.base_url || '',
      api_key: '',
      username: provider.username || '',
      password: '',
      extra_config: provider.extra_config || {},
      auto_create_subnets: provider.auto_create_subnets,
      is_enabled: provider.is_enabled,
    });
    setError(null);
    setIsEditModalOpen(true);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never';
    const d = new Date(dateStr);
    return d.toLocaleString();
  };

  const renderExtraConfigFields = () => {
    if (!selectedVendorMeta?.extra_config_fields?.length) return null;
    return selectedVendorMeta.extra_config_fields.map(field => (
      <div key={field.key} className={formGroupClass}>
        <label className={formLabelClass}>
          {field.label} {field.required && <span className="text-danger">*</span>}
        </label>
        {field.type === 'boolean' ? (
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              className="w-5 h-5 accent-accent-primary"
              checked={formData.extra_config?.[field.key] || false}
              onChange={(e) => setFormData(prev => ({
                ...prev,
                extra_config: { ...prev.extra_config, [field.key]: e.target.checked }
              }))}
            />
            <span className="text-sm text-text-secondary">{field.help}</span>
          </label>
        ) : (
          <>
            <input
              type="text"
              className={formInputClass}
              value={formData.extra_config?.[field.key] || ''}
              onChange={(e) => setFormData(prev => ({
                ...prev,
                extra_config: { ...prev.extra_config, [field.key]: e.target.value }
              }))}
              placeholder={field.help}
              required={field.required}
            />
          </>
        )}
      </div>
    ));
  };

  const renderProviderCard = (provider) => {
    const meta = VENDOR_META[provider.vendor] || { label: provider.vendor, color: '#6366f1', icon: '🔌' };
    const status = STATUS_STYLES[provider.last_sync_status] || STATUS_STYLES.never;
    const testResult = testResults[provider.id];
    const isSyncing = syncingIds.has(provider.id);
    const isTesting = testingIds.has(provider.id);

    return (
      <div key={provider.id} className={`${glassCardClass} relative overflow-hidden`}>
        {/* Vendor accent bar */}
        <div
          className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl"
          style={{ background: `linear-gradient(90deg, ${meta.color}, ${meta.color}88)` }}
        />

        <div className="flex items-start justify-between mb-4 pt-1">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-xl"
              style={{ background: `${meta.color}20`, border: `1px solid ${meta.color}40` }}
            >
              {meta.icon}
            </div>
            <div>
              <h3 className="font-semibold text-text-primary">{provider.name}</h3>
              <p className="text-xs text-text-muted">{meta.label}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${status.bg} ${status.text} ${status.border} border`}>
              {provider.last_sync_status === 'success' && <CheckCircle size={12} className="mr-1" />}
              {provider.last_sync_status === 'failed' && <XCircle size={12} className="mr-1" />}
              {provider.last_sync_status === 'in_progress' && <RefreshCw size={12} className="mr-1 animate-spin" />}
              {status.label}
            </span>
            {!provider.is_enabled && (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-white/5 text-text-muted border border-white/10">
                Disabled
              </span>
            )}
          </div>
        </div>

        {/* Details row */}
        <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
          <div>
            <span className="text-text-muted text-xs block">Last Sync</span>
            <span className="text-text-secondary flex items-center gap-1">
              <Clock size={12} /> {formatDate(provider.last_sync_at)}
            </span>
          </div>
          <div>
            <span className="text-text-muted text-xs block">Auto-Create Subnets</span>
            <span className={`text-xs font-medium ${provider.auto_create_subnets ? 'text-success' : 'text-text-muted'}`}>
              {provider.auto_create_subnets ? 'Enabled' : 'Approval Queue'}
            </span>
          </div>
          {provider.base_url && (
            <div className="col-span-2">
              <span className="text-text-muted text-xs block">Endpoint</span>
              <span className="text-text-secondary text-xs truncate block">{provider.base_url}</span>
            </div>
          )}
        </div>

        {/* Error message */}
        {provider.last_sync_error && (
          <div className="mb-4 px-3 py-2 rounded-lg bg-danger-bg border border-danger/20 text-xs text-danger flex items-start gap-2">
            <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
            <span className="line-clamp-2">{provider.last_sync_error}</span>
          </div>
        )}

        {/* Test result toast */}
        {testResult && (
          <div className={`mb-4 px-3 py-2 rounded-lg text-xs flex items-start gap-2 border ${testResult.ok
            ? 'bg-success-bg border-success/20 text-success'
            : 'bg-danger-bg border-danger/20 text-danger'
          }`}>
            {testResult.ok ? <CheckCircle size={14} className="flex-shrink-0 mt-0.5" /> : <XCircle size={14} className="flex-shrink-0 mt-0.5" />}
            <span>{testResult.message}</span>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-2 pt-3 border-t border-white/5">
          <button
            className={`${btnSuccessClass} !px-3 !py-1.5 !text-xs`}
            onClick={() => handleTestConnection(provider.id)}
            disabled={isTesting}
          >
            {isTesting ? <RefreshCw size={12} className="animate-spin" /> : <Zap size={12} />}
            Test
          </button>
          <button
            className={`${btnPrimaryClass} !px-3 !py-1.5 !text-xs`}
            onClick={() => handleSync(provider.id)}
            disabled={isSyncing || !provider.is_enabled}
          >
            {isSyncing ? <RefreshCw size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            Sync Now
          </button>
          <button
            className={`${btnSecondaryClass} !px-3 !py-1.5 !text-xs`}
            onClick={() => openEditModal(provider)}
          >
            <Settings size={12} /> Edit
          </button>
          <button
            className={`${btnDangerClass} !px-3 !py-1.5 !text-xs ml-auto`}
            onClick={() => handleDelete(provider.id)}
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>
    );
  };

  const renderFormFields = () => (
    <>
      <div className={formGroupClass}>
        <label className={formLabelClass}>Name *</label>
        <input
          required
          type="text"
          className={formInputClass}
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="e.g. HQ Meraki Org"
        />
      </div>

      {!editingProvider && (
        <div className={formGroupClass}>
          <label className={formLabelClass}>Vendor *</label>
          <div className="grid grid-cols-2 gap-3">
            {vendors.map(v => {
              const meta = VENDOR_META[v.id] || { label: v.name, color: '#6366f1', icon: '🔌' };
              const isSelected = formData.vendor === v.id;
              return (
                <button
                  key={v.id}
                  type="button"
                  className={`flex items-center gap-3 p-3 rounded-xl border transition-all text-left cursor-pointer ${
                    isSelected
                      ? 'border-accent-primary bg-accent-primary/10 shadow-[0_0_12px_var(--color-accent-glow)]'
                      : 'border-white/10 bg-black/20 hover:border-white/20 hover:bg-white/5'
                  }`}
                  onClick={() => setFormData({ ...formData, vendor: v.id, extra_config: {} })}
                >
                  <span className="text-xl">{meta.icon}</span>
                  <div>
                    <div className="text-sm font-medium text-text-primary">{meta.label}</div>
                    <div className="text-xs text-text-muted truncate max-w-[140px]">{v.description}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {(selectedVendorMeta?.requires_base_url || editingProvider) && (
        <div className={formGroupClass}>
          <label className={formLabelClass}>
            API Base URL {selectedVendorMeta?.requires_base_url && <span className="text-danger">*</span>}
          </label>
          <input
            type="text"
            className={formInputClass}
            value={formData.base_url}
            onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
            placeholder="https://192.168.1.1 or https://api-gateway.example.com"
            required={selectedVendorMeta?.requires_base_url}
          />
        </div>
      )}

      {(selectedVendorMeta?.supports_api_key !== false || editingProvider) && (
        <div className={formGroupClass}>
          <label className={formLabelClass}>
            API Key / Token {editingProvider && <span className="text-xs text-text-muted">(leave blank to keep existing)</span>}
          </label>
          <input
            type="password"
            className={formInputClass}
            value={formData.api_key}
            onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
            placeholder="Enter API key or token"
          />
        </div>
      )}

      {(selectedVendorMeta?.supports_username_password || editingProvider) && (
        <>
          <div className="flex gap-4">
            <div className={`${formGroupClass} flex-1`}>
              <label className={formLabelClass}>Username / Client ID</label>
              <input
                type="text"
                className={formInputClass}
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                placeholder="Username or Client ID"
              />
            </div>
            <div className={`${formGroupClass} flex-1`}>
              <label className={formLabelClass}>
                Password / Secret {editingProvider && <span className="text-xs text-text-muted">(blank = keep)</span>}
              </label>
              <input
                type="password"
                className={formInputClass}
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder="Password or Client Secret"
              />
            </div>
          </div>
        </>
      )}

      {renderExtraConfigFields()}

      <div className="flex gap-6 mt-2">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            className="w-5 h-5 accent-accent-primary"
            checked={formData.auto_create_subnets}
            onChange={(e) => setFormData({ ...formData, auto_create_subnets: e.target.checked })}
          />
          <div>
            <span className="text-sm text-text-primary font-medium">Auto-create subnets</span>
            <p className="text-xs text-text-muted">Automatically create discovered subnets (otherwise held for approval)</p>
          </div>
        </label>
      </div>

      <div className="flex gap-6 mt-4">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            className="w-5 h-5 accent-success"
            checked={formData.is_enabled}
            onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
          />
          <div>
            <span className="text-sm text-text-primary font-medium">Enable integration</span>
            <p className="text-xs text-text-muted">Include in periodic background sync (every 30 minutes)</p>
          </div>
        </label>
      </div>
    </>
  );

  return (
    <div className="flex-1 p-8">
      <header className="h-[var(--spacing-header)] bg-[#0f1115]/80 backdrop-blur-xl border-b border-white/10 flex items-center justify-between px-8 sticky top-0 z-30 -mt-8 -mx-8 mb-8">
        <h1 className="text-xl font-semibold">Integrations</h1>
        <button className={btnPrimaryClass} onClick={() => { setFormData(emptyForm); setError(null); setIsModalOpen(true); }}>
          <Plus size={16} /> Add Integration
        </button>
      </header>

      {error && !isModalOpen && !isEditModalOpen && (
        <div className="mb-6 px-4 py-3 rounded-xl bg-danger-bg border border-danger/20 text-danger text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="loader w-8 h-8" />
        </div>
      ) : providers.length === 0 ? (
        <div className={`${glassCardClass} text-center py-16`}>
          <Plug size={48} className="mx-auto mb-4 text-text-muted" />
          <h2 className="text-lg font-semibold text-text-primary mb-2">No integrations configured</h2>
          <p className="text-text-muted mb-6 max-w-md mx-auto">
            Connect to your network infrastructure platforms to automatically pull device, client, and subnet data into IPAM.
          </p>
          <button className={btnPrimaryClass} onClick={() => { setFormData(emptyForm); setError(null); setIsModalOpen(true); }}>
            <Plus size={16} /> Add Your First Integration
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {providers.map(renderProviderCard)}
        </div>
      )}

      {/* Create Modal */}
      {isModalOpen && (
        <div className={modalOverlayClass}>
          <div className={modalContentClass}>
            <div className={modalHeaderClass}>
              <h2 className={modalTitleClass}>Add Integration</h2>
              <button className={modalCloseClass} onClick={() => setIsModalOpen(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleCreate}>
              <div className={modalBodyClass}>
                {error && (
                  <div className="mb-4 px-3 py-2 rounded-lg bg-danger-bg border border-danger/20 text-xs text-danger">
                    {error}
                  </div>
                )}
                {renderFormFields()}
              </div>
              <div className={modalFooterClass}>
                <button type="button" className={btnSecondaryClass} onClick={() => setIsModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className={btnPrimaryClass} disabled={!formData.vendor || !formData.name}>
                  Create Integration
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isEditModalOpen && editingProvider && (
        <div className={modalOverlayClass}>
          <div className={modalContentClass}>
            <div className={modalHeaderClass}>
              <h2 className={modalTitleClass}>Edit Integration — {editingProvider.name}</h2>
              <button className={modalCloseClass} onClick={() => { setIsEditModalOpen(false); setEditingProvider(null); }}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleUpdate}>
              <div className={modalBodyClass}>
                {error && (
                  <div className="mb-4 px-3 py-2 rounded-lg bg-danger-bg border border-danger/20 text-xs text-danger">
                    {error}
                  </div>
                )}
                {renderFormFields()}
              </div>
              <div className={modalFooterClass}>
                <button type="button" className={btnSecondaryClass} onClick={() => { setIsEditModalOpen(false); setEditingProvider(null); }}>
                  Cancel
                </button>
                <button type="submit" className={btnPrimaryClass}>
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Integrations;
