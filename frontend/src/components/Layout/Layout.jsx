import { useState, useEffect } from 'react';
import { Network, LayoutDashboard, History, Scan } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import api from '../../lib/axios';

const Layout = ({ children }) => {
  const [features, setFeatures] = useState({ enable_network_discovery: true });

  useEffect(() => {
    api.get('/system/features')
      .then(res => setFeatures(res.data))
      .catch(err => console.error("Failed to fetch features", err));
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
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 ml-[var(--spacing-sidebar)] flex flex-col min-h-screen">
        {children}
      </main>
    </div>
  );
};

export default Layout;
