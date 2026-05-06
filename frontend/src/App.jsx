import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet, useNavigate } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import api from './lib/axios';

import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Subnets from './pages/Subnets';
import SubnetDetail from './pages/SubnetDetail';
import AuditLog from './pages/AuditLog';
import SetupWizard from './pages/SetupWizard';
import SSOSuccess from './pages/SSOSuccess';
import DiscoveryProfiles from './pages/DiscoveryProfiles';

function SetupCheck({ children }) {
  const [checking, setChecking] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/auth/setup-status')
      .then(res => {
        if (res.data.needs_setup) {
          navigate('/setup');
        }
      })
      .catch(err => {
        console.error("Failed to check setup status", err);
      })
      .finally(() => {
        setChecking(false);
      });
  }, [navigate]);

  if (checking) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;

  return children;
}

/**
 * Route guard — redirects to /login if no JWT token is stored.
 */
function ProtectedRoute() {
  const token = localStorage.getItem('access_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}

function App() {
  return (
    <Router>
      <SetupCheck>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/setup" element={<SetupWizard />} />
          <Route path="/sso-success" element={<SSOSuccess />} />

          {/* Protected routes — wrapped in Layout */}
          <Route element={<ProtectedRoute />}>
            <Route
              element={
                <Layout>
                  <Outlet />
                </Layout>
              }
            >
              <Route path="/" element={<Dashboard />} />
              <Route path="/subnets" element={<Subnets />} />
              <Route path="/subnets/:id" element={<SubnetDetail />} />
              <Route path="/audit" element={<AuditLog />} />
              <Route path="/discovery-profiles" element={<DiscoveryProfiles />} />
            </Route>
          </Route>
        </Routes>
      </SetupCheck>
    </Router>
  );
}

export default App;
