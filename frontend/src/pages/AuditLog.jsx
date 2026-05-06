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

  return (
    <div className="content-area">
      <header className="header" style={{ margin: '-32px -32px 32px -32px' }}>
        <h1 className="page-title">Audit Log</h1>
      </header>

      <div className="glass-card" style={{ marginBottom: '24px', padding: '16px 24px', display: 'flex', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Filter size={16} color="var(--text-muted)" />
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: 500 }}>Filters:</span>
        </div>
        
        <select 
          className="form-input" 
          style={{ width: '200px', padding: '8px 12px' }}
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          <option value="">All Entity Types</option>
          <option value="subnet">Subnet</option>
          <option value="ip_address">IP Address</option>
        </select>

        <select 
          className="form-input" 
          style={{ width: '200px', padding: '8px 12px' }}
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

      <div className="glass-card">
        {loading ? (
          <div style={{ padding: '64px', textAlign: 'center' }}>
            <div className="loader" style={{ margin: '0 auto' }}></div>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Entity Type</th>
                  <th>Entity ID</th>
                  <th>Action</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      No audit logs found.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id}>
                      <td style={{ color: 'var(--text-secondary)' }}>
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td>
                        <span className={`badge ${log.entity_type === 'subnet' ? 'badge-info' : 'badge-warning'}`}>
                          {log.entity_type}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'monospace' }}>{log.entity_id}</td>
                      <td>
                        <span className={`badge ${
                          ['created', 'assigned'].includes(log.action) ? 'badge-success' :
                          ['deleted', 'released'].includes(log.action) ? 'badge-danger' : 'badge-warning'
                        }`}>
                          {log.action}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: '300px' }}>
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
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
