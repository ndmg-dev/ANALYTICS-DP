import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { Users, FileUser } from 'lucide-react';

export function EmployeesPage() {
  const { data: latestSnapshot, isLoading: isLoadingSnapshot } = useQuery({
    queryKey: ['latest-snapshot'],
    queryFn: () => api.get('/imports/latest-snapshot')
  });

  const snapshotId = latestSnapshot?.snapshot_id;

  const { data: employees = [], isLoading } = useQuery({
    queryKey: ['employees', snapshotId],
    queryFn: () => api.get(`/employees/snapshot/${snapshotId}`),
    enabled: !!snapshotId
  });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">Colaboradores</h1>
        <p className="text-text-muted text-sm mt-1">Lista de colaboradores ativos do snapshot: {latestSnapshot?.reference_date || 'Atual'}</p>
      </div>

      <div className="glass-card overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <h3 className="text-lg font-medium text-text-primary flex items-center gap-2">
            <Users size={20} className="text-gold" />
            Quadro de Funcionários
          </h3>
          <div className="px-3 py-1 bg-white/5 rounded-lg text-sm text-text-muted">
            Total: {employees.length}
          </div>
        </div>
        
        <div className="overflow-x-auto">
          {isLoadingSnapshot || isLoading ? (
            <div className="p-8 text-center text-text-muted">Carregando colaboradores...</div>
          ) : !snapshotId ? (
            <div className="p-8 text-center text-text-muted">Nenhum dado disponível. Realize uma importação.</div>
          ) : employees.length === 0 ? (
            <div className="p-8 text-center text-text-muted">Nenhum colaborador encontrado neste snapshot.</div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-text-muted">
                <tr>
                  <th className="px-6 py-3 font-medium">Código</th>
                  <th className="px-6 py-3 font-medium">Nome</th>
                  <th className="px-6 py-3 font-medium">Cargo</th>
                  <th className="px-6 py-3 font-medium">Empresa</th>
                  <th className="px-6 py-3 font-medium">Admissão</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {employees.map((emp: any) => (
                  <tr key={emp.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4 text-text-muted">#{emp.code}</td>
                    <td className="px-6 py-4 font-medium text-text-primary flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-gold">
                        <FileUser size={14} />
                      </div>
                      {emp.name}
                    </td>
                    <td className="px-6 py-4 text-text-muted">{emp.job_title}</td>
                    <td className="px-6 py-4 text-text-muted">{emp.company || '-'}</td>
                    <td className="px-6 py-4 text-text-muted">{emp.admission_date ? new Date(emp.admission_date).toLocaleDateString('pt-BR') : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
