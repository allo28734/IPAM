import { useState, useEffect } from 'react';
import { Network, Server, HardDrive, Activity } from 'lucide-react';
import { Link } from 'react-router-dom';
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

  // Shared classes
  const glassCardClass = "bg-bg-card backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-md transition-all hover:shadow-lg hover:border-white/20";
  const btnPrimaryClass = "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm cursor-pointer transition-all border-none outline-none bg-accent-primary text-white shadow-[0_4px_12px_var(--color-accent-glow)] hover:bg-accent-hover hover:-translate-y-0.5 hover:shadow-[0_6px_16px_var(--color-accent-glow)]";
  const btnSecondaryClass = "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm cursor-pointer transition-all border border-white/10 outline-none bg-bg-tertiary text-text-primary hover:bg-white/10 hover:border-white/20";

  return (
    <div className="flex-1 p-8">
      <header className="h-[var(--spacing-header)] bg-[#0f1115]/80 backdrop-blur-xl border-b border-white/10 flex items-center justify-between px-8 sticky top-0 z-30 -mt-8 -mx-8 mb-8">
        <h1 className="text-xl font-semibold">Dashboard Overview</h1>
      </header>

      {error && (
        <div className="bg-danger-bg text-danger border border-danger/20 rounded-2xl p-4 mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center p-16">
          <div className="loader w-6 h-6"></div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className={`${glassCardClass} flex flex-col`}>
              <div className="flex justify-between items-start mb-4">
                <span className="text-text-secondary text-sm font-medium">Total Subnets</span>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/5 text-accent-primary">
                  <Network size={20} />
                </div>
              </div>
              <div className="text-3xl font-bold mb-2">{stats.total_subnets}</div>
              <div className="text-xs text-text-muted">Managed address spaces</div>
            </div>

            <div className={`${glassCardClass} flex flex-col`}>
              <div className="flex justify-between items-start mb-4">
                <span className="text-text-secondary text-sm font-medium">Tracked IPs</span>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/5 text-accent-primary">
                  <Server size={20} />
                </div>
              </div>
              <div className="text-3xl font-bold mb-2">{stats.total_ips}</div>
              <div className="text-xs text-text-muted">Active allocations</div>
            </div>

            <div className={`${glassCardClass} flex flex-col`}>
              <div className="flex justify-between items-start mb-4">
                <span className="text-text-secondary text-sm font-medium">Assigned Hosts</span>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/5 text-accent-primary">
                  <HardDrive size={20} />
                </div>
              </div>
              <div className="text-3xl font-bold mb-2">{stats.assigned_ips}</div>
              <div className="text-xs text-text-muted">Devices on network</div>
            </div>

            <div className={`${glassCardClass} flex flex-col`}>
              <div className="flex justify-between items-start mb-4">
                <span className="text-text-secondary text-sm font-medium">Overall Utilization</span>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/5 text-accent-primary">
                  <Activity size={20} />
                </div>
              </div>
              <div className="text-3xl font-bold mb-2">{stats.overall_utilization.toFixed(1)}%</div>
              <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden mt-2">
                <div 
                  className="h-full bg-gradient-to-r from-accent-hover to-accent-primary rounded-full transition-all duration-500 ease-out" 
                  style={{ width: `${stats.overall_utilization}%` }}
                ></div>
              </div>
            </div>
          </div>

          <div className={glassCardClass}>
            <h2 className="mb-4 text-lg font-semibold">Quick Actions</h2>
            <div className="flex gap-4">
              <Link to="/subnets" className={btnPrimaryClass}>
                <Network size={16} /> Manage Subnets
              </Link>
              <Link to="/audit" className={btnSecondaryClass}>
                <Activity size={16} /> View Audit Log
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;
