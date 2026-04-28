import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout/Layout';

import Dashboard from './pages/Dashboard';
import Subnets from './pages/Subnets';
import SubnetDetail from './pages/SubnetDetail';
import AuditLog from './pages/AuditLog';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/subnets" element={<Subnets />} />
          <Route path="/subnets/:id" element={<SubnetDetail />} />
          <Route path="/audit" element={<AuditLog />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
