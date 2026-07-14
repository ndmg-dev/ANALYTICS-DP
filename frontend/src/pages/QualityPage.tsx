import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { ShieldAlert, AlertTriangle, Info } from 'lucide-react';

export function QualityPage() {
  const { data: latestSnapshot, isLoading: isLoadingSnapshot } = useQuery({
    queryKey: ['latest-snapshot'],
    queryFn: () => api.get('/imports/latest-snapshot')
  });

  const snapshotId = latestSnapshot?.snapshot_id;

  const { data: findings = [], isLoading } = useQuery({
    queryKey: ['quality', snapshotId],
    queryFn: () => api.get(`/quality/snapshot/${snapshotId}`),
    enabled: !!snapshotId
  });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">Qualidade dos Dados</h1>
        <p className="text-text-muted text-sm mt-1">Análise de integridade para o snapshot: {latestSnapshot?.reference_date || 'Atual'}</p>
      </div>

      <div className="glass-card overflow-hidden">
        <div className="p-5 border-b border-border">
          <h3 className="text-lg font-medium text-text-primary flex items-center gap-2">
            <ShieldAlert size={20} className="text-gold" />
            Problemas Detectados
          </h3>
        </div>
        
        <div className="p-5">
          {isLoadingSnapshot || isLoading ? (
            <div className="text-center text-text-muted py-8">Analisando qualidade dos dados...</div>
          ) : !snapshotId ? (
            <div className="text-center text-text-muted py-8">Nenhum dado disponível. Realize uma importação.</div>
          ) : findings.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-16 h-16 rounded-full bg-success/10 flex items-center justify-center text-success mb-4">
                <ShieldAlert size={32} />
              </div>
              <h3 className="text-lg font-medium text-text-primary">Dados 100% Íntegros</h3>
              <p className="text-sm text-text-muted mt-2 max-w-sm">
                Não foram encontrados problemas estruturais, valores faltantes críticos ou formatações inválidas neste snapshot.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {findings.map((f: any) => (
                <div key={f.id} className={`p-4 rounded-lg border flex items-start gap-3 ${
                  f.severity === 'CRITICAL' ? 'bg-danger/5 border-danger/20 text-danger' :
                  f.severity === 'WARNING' ? 'bg-warning/5 border-warning/20 text-warning' :
                  'bg-info/5 border-info/20 text-info'
                }`}>
                  <div className="mt-0.5">
                    {f.severity === 'CRITICAL' ? <AlertTriangle size={18} /> :
                     f.severity === 'WARNING' ? <AlertTriangle size={18} /> :
                     <Info size={18} />}
                  </div>
                  <div>
                    <p className="text-sm font-medium">{f.category} (Registro #{f.affected_record_code || 'Geral'})</p>
                    <p className="text-sm opacity-80 mt-1">{f.description}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
