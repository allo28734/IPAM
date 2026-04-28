import { Network, LayoutDashboard, History } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const Layout = ({ children }) => {
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
