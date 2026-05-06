import React, { useState, useEffect, useCallback } from 'react';
import { CheckCircle, XCircle, Clock, Filter, CheckSquare, XSquare, ChevronDown, Network, AlertTriangle, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../lib/axios';

const VENDOR_META = {
  meraki: { label: 'Cisco Meraki', color: '#00D474', icon: '🌐' },
  fortigate: { label: 'Fortinet FortiGate', color: '#EE3124', icon: '🛡️' },
  aruba_central: { label: 'Aruba Central', color: '#FF8300', icon: '📡' },
  paloalto: { label: 'Palo Alto Networks', color: '#FA582D', icon: '🔥' },
};

const STATUS_BADGE = {
  pending: { bg: 'bg-warning-bg', text: 'text-warning', border: 'border-warning/20', icon: Clock },
  approved: { bg: 'bg-success-bg', text: 'text-success', border: 'border-success/20', icon: CheckCircle },
  dismissed: { bg: 'bg-white/5', text: 'text-text-muted', border: 'border-white/10', icon: XCircle },
};

const ApprovalQueue = () => {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [processingIds, setProcessingIds] = useState(new Set());
  const [error, setError] = useState(null);

  // Shared classes
  const glassCardClass = "bg-bg-card backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-md transition-all hover:shadow-lg hover:border-white/20";
  const btnPrimaryClass = "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm cursor-pointer transition-all border-none outline-none bg-accent-primary text-white shadow-[0_4px_12px_var(--color-accent-glow)] hover:bg-accent-hover hover:-translate-y-0.5 hover:shadow-[0_6px_16px_var(--color-accent-glow)]";
  const btnSecondaryClass = "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm cursor-pointer transition-all border border-white/10 outline-none bg-bg-tertiary text-text-primary hover:bg-white/10 hover:border-white/20";
  const btnSuccessClass = "inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl font-medium text-sm cursor-pointer transition-all border border-success/30 outline-none bg-success-bg text-success hover:bg-success/20";
  const btnDangerClass = "inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl font-medium text-sm cursor-pointer transition-all border border-danger/30 outline-none bg-danger-bg text-danger hover:bg-danger/20";
  const tableContainerClass = "w-full overflow-x-auto rounded-xl border border-white/10 bg-bg-secondary";
  const tableClass = "w-full border-collapse text-left";
  const thClass = "p-4 text-xs font-semibold uppercase text-text-secondary border-b border-white/10 bg-black/20 tracking-wider";
  const tdClass = "p-4 text-sm border-b border-white/5 align-middle";
  const trClass = "transition-all hover:bg-white/5 group";

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/pending-subnets', { params: { status: statusFilter } });
      setItems(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error('Failed to fetch pending subnets:', err);
      setError('Failed to load approval queue.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleApprove = async (id) => {
    setProcessingIds(prev => new Set(prev).add(id));
    try {
      await api.post(`/pending-subnets/${id}/approve`, {});
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to approve subnet');
    } finally {
      setProcessingIds(prev => { const n = new Set(prev); n.delete(id); return n; });
    }
  };

  const handleDismiss = async (id) => {
    setProcessingIds(prev => new Set(prev).add(id));
    try {
      await api.post(`/pending-subnets/${id}/dismiss`);
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to dismiss subnet');
    } finally {
      setProcessingIds(prev => { const n = new Set(prev); n.delete(id); return n; });
    }
  };

  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return;
    const params = new URLSearchParams();
    selectedIds.forEach(id => params.append('id', id));
    try {
      const res = await api.post(`/pending-subnets/bulk/approve?${params.toString()}`);
      setSelectedIds(new Set());
      fetchData();
      if (res.data.errors?.length > 0) {
        alert(`Approved: ${res.data.approved}\nErrors:\n${res.data.errors.join('\n')}`);
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Bulk approve failed');
    }
  };

  const handleBulkDismiss = async () => {
    if (selectedIds.size === 0) return;
    const params = new URLSearchParams();
    selectedIds.forEach(id => params.append('id', id));
    try {
      await api.post(`/pending-subnets/bulk/dismiss?${params.toString()}`);
      setSelectedIds(new Set());
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Bulk dismiss failed');
    }
  };

  const toggleSelect = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === items.filter(i => i.status === 'pending').length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.filter(i => i.status === 'pending').map(i => i.id)));
    }
  };

  const formatDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleString();
  };

  const pendingItems = items.filter(i => i.status === 'pending');

  return (
    <div className="flex-1 p-8">
      <header className="h-[var(--spacing-header)] bg-[#0f1115]/80 backdrop-blur-xl border-b border-white/10 flex items-center justify-between px-8 sticky top-0 z-30 -mt-8 -mx-8 mb-8">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">Approval Queue</h1>
          {total > 0 && statusFilter === 'pending' && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-warning-bg text-warning border border-warning/20">
              {total}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {selectedIds.size > 0 && (
            <>
              <button className={btnSuccessClass} onClick={handleBulkApprove}>
                <CheckSquare size={16} /> Approve ({selectedIds.size})
              </button>
              <button className={btnDangerClass} onClick={handleBulkDismiss}>
                <XSquare size={16} /> Dismiss ({selectedIds.size})
              </button>
              <div className="w-px h-8 bg-white/10" />
            </>
          )}
          <div className="relative">
            <select
              className="appearance-none bg-bg-tertiary border border-white/10 rounded-xl px-4 py-2.5 pr-8 text-sm text-text-primary cursor-pointer focus:outline-none focus:border-accent-primary"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setSelectedIds(new Set()); }}
            >
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="dismissed">Dismissed</option>
              <option value="all">All</option>
            </select>
            <ChevronDown size={14} className="absolute right-3 top-3.5 text-text-muted pointer-events-none" />
          </div>
        </div>
      </header>

      {error && (
        <div className="mb-6 px-4 py-3 rounded-xl bg-danger-bg border border-danger/20 text-danger text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="loader w-8 h-8" />
        </div>
      ) : items.length === 0 ? (
        <div className={`${glassCardClass} text-center py-16`}>
          <CheckCircle size={48} className="mx-auto mb-4 text-success" />
          <h2 className="text-lg font-semibold text-text-primary mb-2">
            {statusFilter === 'pending' ? 'No subnets awaiting approval' : `No ${statusFilter} subnets`}
          </h2>
          <p className="text-text-muted max-w-md mx-auto">
            {statusFilter === 'pending'
              ? 'When integrations discover new subnets (with auto-create disabled), they will appear here for your review.'
              : 'Try changing the filter to see other entries.'
            }
          </p>
          <Link to="/integrations" className={`${btnSecondaryClass} mt-6 inline-flex`}>
            <ExternalLink size={14} /> Go to Integrations
          </Link>
        </div>
      ) : (
        <div className={tableContainerClass}>
          <table className={tableClass}>
            <thead>
              <tr>
                {statusFilter === 'pending' && (
                  <th className={`${thClass} w-12`}>
                    <input
                      type="checkbox"
                      className="w-4 h-4 accent-accent-primary cursor-pointer"
                      checked={selectedIds.size > 0 && selectedIds.size === pendingItems.length}
                      onChange={toggleSelectAll}
                    />
                  </th>
                )}
                <th className={thClass}>Network</th>
                <th className={thClass}>Name</th>
                <th className={thClass}>Gateway</th>
                <th className={thClass}>VLAN</th>
                <th className={thClass}>Source</th>
                <th className={thClass}>Discovered</th>
                <th className={thClass}>Status</th>
                <th className={thClass}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => {
                const meta = VENDOR_META[item.vendor] || { label: item.vendor, color: '#6366f1', icon: '🔌' };
                const statusStyle = STATUS_BADGE[item.status] || STATUS_BADGE.pending;
                const StatusIcon = statusStyle.icon;
                const isProcessing = processingIds.has(item.id);
                const isPending = item.status === 'pending';

                return (
                  <tr key={item.id} className={trClass}>
                    {statusFilter === 'pending' && (
                      <td className={tdClass}>
                        {isPending && (
                          <input
                            type="checkbox"
                            className="w-4 h-4 accent-accent-primary cursor-pointer"
                            checked={selectedIds.has(item.id)}
                            onChange={() => toggleSelect(item.id)}
                          />
                        )}
                      </td>
                    )}
                    <td className={tdClass}>
                      <div className="flex items-center gap-2">
                        <Network size={14} className="text-accent-primary" />
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-info-bg text-info border border-info/20">
                          IPv{item.ip_version}
                        </span>
                        <code className="text-sm font-mono text-text-primary">{item.cidr}</code>
                      </div>
                    </td>
                    <td className={tdClass}>{item.name || '—'}</td>
                    <td className={tdClass}>{item.gateway || '—'}</td>
                    <td className={tdClass}>{item.vlan_id || '—'}</td>
                    <td className={tdClass}>
                      <div className="flex items-center gap-2">
                        <span
                          className="w-5 h-5 rounded flex items-center justify-center text-xs"
                          style={{ background: `${meta.color}20`, border: `1px solid ${meta.color}40` }}
                        >
                          {meta.icon}
                        </span>
                        <span className="text-xs text-text-secondary">{meta.label}</span>
                      </div>
                    </td>
                    <td className={tdClass}>
                      <span className="text-xs text-text-muted">{formatDate(item.discovered_at)}</span>
                    </td>
                    <td className={tdClass}>
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${statusStyle.bg} ${statusStyle.text} ${statusStyle.border} border capitalize`}>
                        <StatusIcon size={12} />
                        {item.status}
                      </span>
                    </td>
                    <td className={tdClass}>
                      {isPending ? (
                        <div className="flex items-center gap-2">
                          <button
                            className={`${btnSuccessClass} !px-3 !py-1.5 !text-xs`}
                            onClick={() => handleApprove(item.id)}
                            disabled={isProcessing}
                          >
                            <CheckCircle size={12} /> Approve
                          </button>
                          <button
                            className={`${btnDangerClass} !px-3 !py-1.5 !text-xs`}
                            onClick={() => handleDismiss(item.id)}
                            disabled={isProcessing}
                          >
                            <XCircle size={12} /> Dismiss
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-text-muted">
                          {item.resolved_at ? formatDate(item.resolved_at) : '—'}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ApprovalQueue;
