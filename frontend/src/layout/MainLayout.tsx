import { Outlet, NavLink } from 'react-router-dom';
import { LayoutDashboard, UploadCloud, FileCheck, Users } from 'lucide-react';

export function MainLayout() {
  return (
    <div className="flex h-screen bg-background text-text-primary overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-sidebar border-r border-border flex flex-col">
        <div className="p-6">
          <h1 className="text-xl font-bold tracking-wider text-text-primary">
            MENDONÇA <span className="text-gold">GALVÃO</span>
          </h1>
          <p className="text-xs text-text-muted mt-1 uppercase tracking-widest">Analytics Platform</p>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          <NavLink to="/" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </NavLink>
          <NavLink to="/imports" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <UploadCloud size={20} />
            <span>Importações</span>
          </NavLink>
          <NavLink to="/quality" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <FileCheck size={20} />
            <span>Qualidade dos Dados</span>
          </NavLink>
          <NavLink to="/employees" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <Users size={20} />
            <span>Colaboradores</span>
          </NavLink>
        </nav>
        

      </aside>
      
      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Topbar */}
        <header className="h-16 border-b border-border bg-background/80 backdrop-blur-md flex items-center justify-between px-8 shrink-0">
          <h2 className="font-medium text-text-muted">Workforce Overview</h2>
          <div className="flex items-center gap-4">
            <div className="w-8 h-8 rounded-full bg-sidebar border border-border flex items-center justify-center">
              <span className="text-sm font-semibold text-gold">MG</span>
            </div>
          </div>
        </header>
        
        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
