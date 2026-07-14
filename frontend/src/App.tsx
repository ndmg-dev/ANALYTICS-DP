import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { MainLayout } from './layout/MainLayout';
import { DashboardPage } from './pages/DashboardPage';
import { ImportsPage } from './pages/ImportsPage';
import { EmployeesPage } from './pages/EmployeesPage';
import { QualityPage } from './pages/QualityPage';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster position="top-right" toastOptions={{ className: 'bg-card text-text-primary border border-border' }} />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="imports" element={<ImportsPage />} />
            <Route path="quality" element={<QualityPage />} />
            <Route path="employees" element={<EmployeesPage />} />
            <Route path="settings" element={<div className="text-text-muted">Configurações (Em breve)</div>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
