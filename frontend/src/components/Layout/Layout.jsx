import { useState, useEffect } from 'react';
import { Network, LayoutDashboard, History, Scan, Plug, ClipboardCheck, ShieldAlert, X } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import api from '../../lib/axios';

const Layout = ({ children, securityWarnings = {} }) => {
  const [features, setFeatures] = useState({ enable_network_discovery: true });
  const [pendingCount, setPendingCount] = useState(0);
  const [bannerDismissed, setBannerDismissed] = useState(
    () => sessionStorage.getItem('db_password_warning_dismissed') === 'true'
  );

  const handleDismissBanner = () => {
    setBannerDismissed(true);
    sessionStorage.setItem('db_password_warning_dismissed', 'true');
  };

  useEffect(() => {
    api.get('/system/features')
      .then(res => setFeatures(res.data))
      .catch(err => console.error("Failed to fetch features", err));
    api.get('/pending-subnets/count')
      .then(res => setPendingCount(res.data.count || 0))
      .catch(() => {});  // Silently fail if user is readonly
  }, []);
  return (
    <div className="flex min-h-screen">
      {/* Sidebar Navigation */}
      <aside className="w-[var(--spacing-sidebar)] bg-bg-secondary border-r border-white/10 flex flex-col fixed h-screen z-40 shadow-lg">
        <div className="h-[var(--spacing-header)] flex items-center px-6 border-b border-white/10">
          <div className="text-xl font-bold bg-gradient-to-br from-white to-slate-400 bg-clip-text text-transparent flex items-center gap-3">
            <Network className="text-accent-primary drop-shadow-[0_0_8px_var(--color-accent-glow)]" size={24} />
            <span>IPAM Core</span>
          </div>
        </div>
        
        <nav className="flex-1 px-4 py-6 flex flex-col gap-2">
          <NavLink 
            to="/" 
            className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-md font-medium transition-all duration-200 cursor-pointer ${isActive ? 'bg-indigo-500/10 text-accent-primary border-l-3 border-accent-primary' : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'}`}
            end
          >
            {({ isActive }) => (
              <>
                <LayoutDashboard size={20} className={`transition-all duration-200 ${isActive ? 'drop-shadow-[0_0_4px_var(--color-accent-glow)]' : ''}`} />
                <span>Dashboard</span>
              </>
            )}
          </NavLink>
          
          <NavLink 
            to="/subnets" 
            className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-md font-medium transition-all duration-200 cursor-pointer ${isActive ? 'bg-indigo-500/10 text-accent-primary border-l-3 border-accent-primary' : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'}`}
          >
            {({ isActive }) => (
              <>
                <Network size={20} className={`transition-all duration-200 ${isActive ? 'drop-shadow-[0_0_4px_var(--color-accent-glow)]' : ''}`} />
                <span>Subnets</span>
              </>
            )}
          </NavLink>

          <NavLink 
            to="/audit" 
            className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-md font-medium transition-all duration-200 cursor-pointer ${isActive ? 'bg-indigo-500/10 text-accent-primary border-l-3 border-accent-primary' : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'}`}
          >
            {({ isActive }) => (
              <>
                <History size={20} className={`transition-all duration-200 ${isActive ? 'drop-shadow-[0_0_4px_var(--color-accent-glow)]' : ''}`} />
                <span>Audit Log</span>
              </>
            )}
          </NavLink>

          {features.enable_network_discovery && (
            <NavLink 
              to="/discovery-profiles" 
              className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-md font-medium transition-all duration-200 cursor-pointer ${isActive ? 'bg-indigo-500/10 text-accent-primary border-l-3 border-accent-primary' : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'}`}
            >
              {({ isActive }) => (
                <>
                  <Scan size={20} className={`transition-all duration-200 ${isActive ? 'drop-shadow-[0_0_4px_var(--color-accent-glow)]' : ''}`} />
                  <span>Discovery</span>
                </>
              )}
            </NavLink>
          )}

          <NavLink 
            to="/integrations" 
            className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-md font-medium transition-all duration-200 cursor-pointer ${isActive ? 'bg-indigo-500/10 text-accent-primary border-l-3 border-accent-primary' : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'}`}
          >
            {({ isActive }) => (
              <>
                <Plug size={20} className={`transition-all duration-200 ${isActive ? 'drop-shadow-[0_0_4px_var(--color-accent-glow)]' : ''}`} />
                <span>Integrations</span>
              </>
            )}
          </NavLink>

          <NavLink 
            to="/approval-queue" 
            className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-md font-medium transition-all duration-200 cursor-pointer ${isActive ? 'bg-indigo-500/10 text-accent-primary border-l-3 border-accent-primary' : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'}`}
          >
            {({ isActive }) => (
              <>
                <ClipboardCheck size={20} className={`transition-all duration-200 ${isActive ? 'drop-shadow-[0_0_4px_var(--color-accent-glow)]' : ''}`} />
                <span>Approval Queue</span>
                {pendingCount > 0 && (
                  <span className="ml-auto inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full text-[10px] font-bold bg-warning text-black animate-pulse">
                    {pendingCount}
                  </span>
                )}
              </>
            )}
          </NavLink>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 ml-[var(--spacing-sidebar)] flex flex-col min-h-screen">
        {/* Security Warning Banner */}
        {securityWarnings.usingDefaultDbPassword && !bannerDismissed && (
          <div className="mx-4 mt-4 flex items-center gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 backdrop-blur-sm px-4 py-3 text-amber-200 shadow-lg shadow-amber-500/5">
            <ShieldAlert size={20} className="shrink-0 text-amber-400" />
            <p className="flex-1 text-sm font-medium">
              <span className="font-bold text-amber-300">Security Warning:</span>{' '}
              You are using the default database password. Please update{' '}
              <code className="rounded bg-amber-500/20 px-1.5 py-0.5 text-xs font-mono text-amber-200">DB_PASSWORD</code>{' '}
              in your <code className="rounded bg-amber-500/20 px-1.5 py-0.5 text-xs font-mono text-amber-200">.env</code> file and restart.
            </p>
            <button
              onClick={handleDismissBanner}
              className="shrink-0 rounded p-1 text-amber-400 hover:bg-amber-500/20 hover:text-amber-200 transition-colors"
              title="Dismiss for this session"
            >
              <X size={16} />
            </button>
          </div>
        )}
        {children}
      </main>
    </div>
  );
};

export default Layout;

