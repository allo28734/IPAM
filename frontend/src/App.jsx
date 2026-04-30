import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Layout from './components/Layout/Layout';

import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Subnets from './pages/Subnets';
import SubnetDetail from './pages/SubnetDetail';
import AuditLog from './pages/AuditLog';

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
      <Routes>
        {/* Public route */}
        <Route path="/login" element={<Login />} />

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
          </Route>
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
