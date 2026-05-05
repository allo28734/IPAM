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
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <Network className="sidebar-brand-icon" size={24} />
            <span>IPAM Core</span>
          </div>
        </div>
        
        <nav className="sidebar-nav">
          <NavLink 
            to="/" 
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            end
          >
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </NavLink>
          
          <NavLink 
            to="/subnets" 
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Network size={20} />
            <span>Subnets</span>
          </NavLink>

          <NavLink 
            to="/audit" 
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <History size={20} />
            <span>Audit Log</span>
          </NavLink>

          {features.enable_network_discovery && (
            <NavLink 
              to="/discovery-profiles" 
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Scan size={20} />
              <span>Discovery</span>
            </NavLink>
          )}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

export default Layout;
