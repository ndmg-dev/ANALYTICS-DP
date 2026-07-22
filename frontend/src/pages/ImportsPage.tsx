import { useState, useRef } from 'react';
import { Upload, FileUp, CheckCircle2, Loader2, AlertTriangle, Info } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import toast from 'react-hot-toast';

export function ImportsPage() {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { data: history = [], isLoading } = useQuery({
    queryKey: ['imports'],
    queryFn: () => api.get('/imports/'),
    refetchInterval: 3000 // Poll every 3 seconds for updates
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.post('/imports/upload', formData);
    },
    onMutate: (file) => {
      toast.loading(`Enviando ${file.name}...`, { id: file.name });
    },
    onSuccess: (_, file) => {
      toast.success(`${file.name} enviado! Processando...`, { id: file.name });
      queryClient.invalidateQueries({ queryKey: ['imports'] });
      queryClient.invalidateQueries({ queryKey: ['latest-snapshot'] });
    },
    onError: (err, file) => {
      toast.error(`Erro ao enviar ${file.name}: ${err.message}`, { id: file.name });
    }
  });

  const handleFiles = (files: FileList | File[]) => {
    const validFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.xls'));
    
    if (validFiles.length === 0) {
      toast.error("Nenhum arquivo .xls válido encontrado. Apenas .xls (Excel 97-2003) é suportado no momento.");
      return;
    }
    
    validFiles.forEach((file, index) => {
      // Small delay for multiple files so toasts don't overlap awkwardly and mutations don't conflict
      setTimeout(() => {
        uploadMutation.mutate(file);
      }, index * 300);
    });
  };

  const retryMutation = useMutation({
    mutationFn: (importId: number) => api.post(`/imports/${importId}/retry`),
    onSuccess: () => {
      toast.success('Reprocessamento iniciado.');
      queryClient.invalidateQueries({ queryKey: ['imports'] });
    },
    onError: (err: any) => {
      toast.error(`Erro ao reprocessar: ${err.message}`);
    }
  });

  const RETRYABLE_STATUSES = ['Falha', 'Aguardando Revisão'];

  const getStatusDisplay = (status: string) => {
    switch(status) {
      case 'Concluído': return { icon: <CheckCircle2 size={14} />, classes: 'bg-success/10 text-success border border-success/20' };
      case 'Falha':
      case 'Aguardando Revisão':
        return { icon: <AlertTriangle size={14} />, classes: 'bg-danger/10 text-danger border border-danger/20' };
      case 'Recebido':
      case 'Na Fila':
      case 'Em Processamento':
        return { icon: <Loader2 size={14} className="animate-spin" />, classes: 'bg-warning/10 text-warning border border-warning/20' };
      default: return { icon: <Info size={14} />, classes: 'bg-info/10 text-info border border-info/20' };
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">Importações</h1>
        <p className="text-text-muted text-sm mt-1">Envie planilhas do Domínio para gerar novos snapshots</p>
      </div>

      {/* Upload Zone */}
      <div 
        className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center transition-colors duration-200 ${
          isDragging ? 'border-gold bg-gold/5' : 'border-border bg-card/30'
        }`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => { 
          e.preventDefault(); 
          setIsDragging(false); 
          if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
          }
        }}
      >
        <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4 text-gold">
          {uploadMutation.isPending ? <Loader2 size={32} className="animate-spin" /> : <Upload size={32} />}
        </div>
        <h3 className="text-lg font-medium text-text-primary">Arraste as planilhas do Domínio (.xls)</h3>
        <p className="text-sm text-text-muted mt-2 text-center max-w-md">
          O sistema extrairá os colaboradores ativos automaticamente. Você pode enviar vários arquivos de uma vez.
        </p>
        
        <input 
          type="file" 
          accept=".xls,.XLS" 
          multiple
          className="hidden" 
          ref={fileInputRef}
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFiles(e.target.files);
            }
            // Clear value to allow selecting the same file again
            if (fileInputRef.current) {
              fileInputRef.current.value = '';
            }
          }}
        />
        
        <button 
          className="btn-primary mt-6 flex items-center gap-2"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadMutation.isPending}
        >
          <FileUp size={18} />
          {uploadMutation.isPending ? 'Enviando...' : 'Selecionar Arquivo'}
        </button>
      </div>

      {/* History Table */}
      <div className="glass-card overflow-hidden">
        <div className="p-5 border-b border-border">
          <h3 className="text-lg font-medium text-text-primary">Histórico de Importações</h3>
        </div>
        <div className="overflow-x-auto">
          {isLoading ? (
            <div className="p-8 text-center text-text-muted">Carregando histórico...</div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-text-muted">
                <tr>
                  <th className="px-6 py-3 font-medium">Arquivo</th>
                  <th className="px-6 py-3 font-medium">Data</th>
                  <th className="px-6 py-3 font-medium">Registros</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-text-muted">
                      Nenhuma importação realizada ainda.
                    </td>
                  </tr>
                ) : (
                  history.map((row: any) => (
                    <tr key={row.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4 font-medium text-text-primary">{row.filename}</td>
                      <td className="px-6 py-4 text-text-muted">{row.date}</td>
                      <td className="px-6 py-4 text-text-muted">{row.records || '-'}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${getStatusDisplay(row.status).classes}`}>
                          {getStatusDisplay(row.status).icon}
                          {row.status}
                        </span>
                        {row.error_message && (
                          <p className="text-xs text-danger/80 mt-1 max-w-sm">{row.error_message}</p>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {RETRYABLE_STATUSES.includes(row.status) && (
                          <button
                            className="text-xs text-gold hover:underline disabled:opacity-50"
                            disabled={retryMutation.isPending}
                            onClick={() => retryMutation.mutate(row.id)}
                          >
                            Reprocessar
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
