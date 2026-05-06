import { useState, useEffect } from 'react';
import { History, Search, Filter } from 'lucide-react';
import api from '../lib/axios';

const AuditLog = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('');
  const [filterAction, setFilterAction] = useState('');

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterType) params.entity_type = filterType;
      if (filterAction) params.action = filterAction;
      
      const response = await api.get('/audit', { params });
      setLogs(response.data.items);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [filterType, filterAction]);

  // Shared classes
  const glassCardClass = "bg-bg-card backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-md transition-all hover:shadow-lg hover:border-white/20";
  const formInputClass = "w-full px-4 py-3 bg-black/20 border border-white/10 rounded-xl text-text-primary text-sm transition-all focus:outline-none focus:border-accent-primary focus:ring-3 focus:ring-indigo-500/20";
  const tableContainerClass = "w-full overflow-x-auto rounded-xl border border-white/10 bg-bg-secondary";
  const tableClass = "w-full border-collapse text-left";
  const thClass = "p-4 text-xs font-semibold uppercase text-text-secondary border-b border-white/10 bg-black/20 tracking-wider";
  const tdClass = "p-4 text-sm border-b border-white/5 align-middle group-last:border-none";
  const trClass = "transition-all hover:bg-white/5 group";
  
  const badgeClass = "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border";
  const badgeInfoClass = `${badgeClass} bg-info-bg text-info border-info/20`;
  const badgeWarningClass = `${badgeClass} bg-warning-bg text-warning border-warning/20`;
  const badgeSuccessClass = `${badgeClass} bg-success-bg text-success border-success/20`;
  const badgeDangerClass = `${badgeClass} bg-danger-bg text-danger border-danger/20`;

  return (
    <div className="flex-1 p-8">
      <header className="h-[var(--spacing-header)] bg-[#0f1115]/80 backdrop-blur-xl border-b border-white/10 flex items-center justify-between px-8 sticky top-0 z-30 -mt-8 -mx-8 mb-8">
        <h1 className="text-xl font-semibold">Audit Log</h1>
      </header>

      <div className={`${glassCardClass} mb-6 flex gap-4 p-4`}>
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-text-muted" />
          <span className="text-text-secondary text-sm font-medium">Filters:</span>
        </div>
        
        <select 
          className={`${formInputClass} !w-[200px] !py-2 !px-3`}
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          <option value="">All Entity Types</option>
          <option value="subnet">Subnet</option>
          <option value="ip_address">IP Address</option>
        </select>

        <select 
          className={`${formInputClass} !w-[200px] !py-2 !px-3`}
          value={filterAction}
          onChange={(e) => setFilterAction(e.target.value)}
        >
          <option value="">All Actions</option>
          <option value="created">Created</option>
          <option value="updated">Updated</option>
          <option value="deleted">Deleted</option>
          <option value="assigned">Assigned</option>
          <option value="released">Released</option>
        </select>
      </div>

      <div className={glassCardClass}>
        {loading ? (
          <div className="p-16 text-center">
            <div className="loader w-6 h-6 mx-auto"></div>
          </div>
        ) : (
          <div className={tableContainerClass}>
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>Timestamp</th>
                  <th className={thClass}>Entity Type</th>
                  <th className={thClass}>Entity ID</th>
                  <th className={thClass}>Action</th>
                  <th className={thClass}>Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="text-center p-8 text-text-muted">
                      No audit logs found.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className={trClass}>
                      <td className={`${tdClass} text-text-secondary`}>
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className={tdClass}>
                        <span className={log.entity_type === 'subnet' ? badgeInfoClass : badgeWarningClass}>
                          {log.entity_type}
                        </span>
                      </td>
                      <td className={`${tdClass} font-mono`}>{log.entity_id}</td>
                      <td className={tdClass}>
                        <span className={
                          ['created', 'assigned'].includes(log.action) ? badgeSuccessClass :
                          ['deleted', 'released'].includes(log.action) ? badgeDangerClass : badgeWarningClass
                        }>
                          {log.action}
                        </span>
                      </td>
                      <td className={`${tdClass} text-xs text-text-muted max-w-[300px]`}>
                        <pre className="m-0 whitespace-pre-wrap font-inherit">
                          {log.details}
                        </pre>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditLog;
