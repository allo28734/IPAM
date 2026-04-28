import { useState, useEffect } from 'react';
import { Network, Server, HardDrive, Activity } from 'lucide-react';
import api from '../lib/axios';

const Dashboard = () => {
  const [stats, setStats] = useState({
    total_subnets: 0,
    total_ips: 0,
    assigned_ips: 0,
    reserved_ips: 0,
    overall_utilization: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get('/dashboard/stats');
        setStats(response.data);
      } catch (err) {
        console.error('Error fetching dashboard stats:', err);
        setError('Failed to load dashboard statistics.');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  return (
    <div className="content-area">
      <header className="header" style={{ margin: '-32px -32px 32px -32px' }}>
        <h1 className="page-title">Dashboard Overview</h1>
      </header>

      {error && (
        <div className="glass-card badge-danger" style={{ marginBottom: '24px', padding: '16px' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '64px' }}>
          <div className="loader"></div>
        </div>
      ) : (
        <>
          <div className="stats-grid">
            <div className="glass-card stat-card">
              <div className="stat-header">
                <span className="stat-title">Total Subnets</span>
                <div className="stat-icon">
                  <Network size={20} />
                </div>
              </div>
              <div className="stat-value">{stats.total_subnets}</div>
              <div className="stat-desc">Managed address spaces</div>
            </div>

            <div className="glass-card stat-card">
              <div className="stat-header">
                <span className="stat-title">Tracked IPs</span>
                <div className="stat-icon">
                  <Server size={20} />
                </div>
              </div>
              <div className="stat-value">{stats.total_ips}</div>
              <div className="stat-desc">Active allocations</div>
            </div>

            <div className="glass-card stat-card">
              <div className="stat-header">
                <span className="stat-title">Assigned Hosts</span>
                <div className="stat-icon">
                  <HardDrive size={20} />
                </div>
              </div>
              <div className="stat-value">{stats.assigned_ips}</div>
              <div className="stat-desc">Devices on network</div>
            </div>

            <div className="glass-card stat-card">
              <div className="stat-header">
                <span className="stat-title">Overall Utilization</span>
                <div className="stat-icon">
                  <Activity size={20} />
                </div>
              </div>
              <div className="stat-value">{stats.overall_utilization.toFixed(1)}%</div>
              <div className="progress-bg">
                <div 
                  className="progress-bar" 
                  style={{ width: `${stats.overall_utilization}%` }}
                ></div>
              </div>
            </div>
          </div>

          <div className="glass-card">
            <h2 style={{ marginBottom: '16px', fontSize: '1.1rem' }}>Quick Actions</h2>
            <div style={{ display: 'flex', gap: '16px' }}>
              <a href="/subnets" className="btn btn-primary">
                <Network size={16} /> Manage Subnets
              </a>
              <a href="/audit" className="btn btn-secondary">
                <Activity size={16} /> View Audit Log
              </a>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;
