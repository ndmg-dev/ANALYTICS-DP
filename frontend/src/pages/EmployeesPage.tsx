import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { Users, FileUser, Edit2, X, Download } from 'lucide-react';
import toast from 'react-hot-toast';
import ExcelJS from 'exceljs';
import { saveAs } from 'file-saver';

export function EmployeesPage() {
  const queryClient = useQueryClient();
  const [selectedEmp, setSelectedEmp] = useState<any>(null);
  const [notes, setNotes] = useState('');

  const [filterCompany, setFilterCompany] = useState('');
  const [filterDate, setFilterDate] = useState('');

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

  const companies = Array.from(new Set(employees.map((e: any) => e.company || ''))).filter(Boolean) as string[];

  const filteredEmployees = employees.filter((emp: any) => {
    let match = true;
    if (filterCompany && emp.company !== filterCompany) match = false;
    if (filterDate) {
      const empDate = emp.admission_date ? new Date(emp.admission_date).toISOString().split('T')[0] : '';
      if (empDate !== filterDate) match = false;
    }
    return match;
  });

  const updateNote = useMutation({
    mutationFn: (data: { company: string, code: string, notes: string }) => api.put('/employees/notes', data),
    onSuccess: () => {
      toast.success('Observação salva com sucesso!');
      queryClient.invalidateQueries({ queryKey: ['employees', snapshotId] });
      setSelectedEmp(null);
    },
    onError: () => {
      toast.error('Erro ao salvar observação.');
    }
  });

  const handleSaveNote = () => {
    if (!selectedEmp) return;
    updateNote.mutate({
      company: selectedEmp.company,
      code: selectedEmp.code,
      notes: notes
    });
  };

  const handleExportExcel = async () => {
    if (filteredEmployees.length === 0) {
      toast.error('Nenhum dado para exportar.');
      return;
    }

    const workbook = new ExcelJS.Workbook();
    const worksheet = workbook.addWorksheet('Colaboradores');

    worksheet.columns = [
      { header: 'Código', key: 'code', width: 15 },
      { header: 'Nome', key: 'name', width: 40 },
      { header: 'Cargo', key: 'job_title', width: 30 },
      { header: 'Categoria', key: 'category', width: 15 },
      { header: 'Empresa', key: 'company', width: 45 },
      { header: 'Admissão', key: 'admission_date', width: 15 },
      { header: 'Salário', key: 'salary', width: 18 },
      { header: 'Observações', key: 'notes', width: 50 },
    ];

    const headerRow = worksheet.getRow(1);
    headerRow.eachCell((cell) => {
      cell.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'FF1a1a1a' }
      };
      cell.font = {
        color: { argb: 'FFd4af37' },
        bold: true
      };
      cell.alignment = { vertical: 'middle', horizontal: 'center' };
    });
    headerRow.height = 30;

    filteredEmployees.forEach((emp: any) => {
      worksheet.addRow({
        code: `#${emp.code}`,
        name: emp.name,
        job_title: emp.job_title,
        category: emp.category || '-',
        company: emp.company || '-',
        admission_date: emp.admission_date ? new Date(emp.admission_date).toLocaleDateString('pt-BR') : '-',
        salary: typeof emp.salary === 'number' ? emp.salary.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '-',
        notes: emp.notes || '-'
      });
    });

    const buffer = await workbook.xlsx.writeBuffer();
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const today = new Date().toISOString().split('T')[0];
    saveAs(blob, `Colaboradores_MG_${today}.xlsx`);
    toast.success('Excel gerado com sucesso!');
  };

  return (
    <div className="space-y-8 relative">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Colaboradores</h1>
          <p className="text-text-muted text-sm mt-1">Lista de colaboradores ativos do snapshot: {latestSnapshot?.reference_date ? new Date(latestSnapshot.reference_date).toLocaleDateString('pt-BR') : 'Atual'}</p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-text-muted">Filtrar por Empresa</label>
            <select
              value={filterCompany}
              onChange={(e) => setFilterCompany(e.target.value)}
              className="bg-sidebar border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-gold"
            >
              <option value="">Todas as Empresas</option>
              {companies.map((c, i) => (
                <option key={i} value={c}>{c}</option>
              ))}
            </select>
          </div>
          
          <div className="flex flex-col gap-1">
            <label className="text-xs text-text-muted">Filtrar por Admissão</label>
            <input
              type="date"
              value={filterDate}
              onChange={(e) => setFilterDate(e.target.value)}
              className="bg-sidebar border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-gold"
            />
          </div>
          
          <div className="flex flex-col gap-1 justify-end">
            <button
              onClick={handleExportExcel}
              className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-border hover:bg-white/10 rounded-lg text-text-primary text-sm font-medium transition-colors h-[38px]"
            >
              <Download size={16} className="text-gold" />
              Exportar Excel
            </button>
          </div>
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <h3 className="text-lg font-medium text-text-primary flex items-center gap-2">
            <Users size={20} className="text-gold" />
            Quadro de Funcionários
          </h3>
          <div className="px-3 py-1 bg-white/5 rounded-lg text-sm text-text-muted">
            Total: {filteredEmployees.length}
          </div>
        </div>
        
        <div className="overflow-x-auto">
          {isLoadingSnapshot || isLoading ? (
            <div className="p-8 text-center text-text-muted">Carregando colaboradores...</div>
          ) : !snapshotId ? (
            <div className="p-8 text-center text-text-muted">Nenhum dado disponível. Realize uma importação.</div>
          ) : filteredEmployees.length === 0 ? (
            <div className="p-8 text-center text-text-muted">Nenhum colaborador encontrado neste snapshot.</div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-text-muted">
                <tr>
                  <th className="px-6 py-3 font-medium">Código</th>
                  <th className="px-6 py-3 font-medium">Nome</th>
                  <th className="px-6 py-3 font-medium">Cargo</th>
                  <th className="px-6 py-3 font-medium">Categoria</th>
                  <th className="px-6 py-3 font-medium">Empresa</th>
                  <th className="px-6 py-3 font-medium">Admissão</th>
                  <th className="px-6 py-3 font-medium">Salário</th>
                  <th className="px-6 py-3 font-medium">Observações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredEmployees.map((emp: any) => (
                  <tr key={emp.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4 text-text-muted">#{emp.code}</td>
                    <td className="px-6 py-4 font-medium text-text-primary flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-gold min-w-[32px]">
                        <FileUser size={14} />
                      </div>
                      <span className="truncate max-w-[200px]" title={emp.name}>{emp.name}</span>
                    </td>
                    <td className="px-6 py-4 text-text-muted">
                      <span className="truncate block max-w-[150px]" title={emp.job_title}>{emp.job_title}</span>
                    </td>
                    <td className="px-6 py-4 text-text-muted">
                      <span className="px-2 py-1 bg-white/5 rounded text-xs whitespace-nowrap">{emp.category || '-'}</span>
                    </td>
                    <td className="px-6 py-4 text-text-muted">
                      <span className="truncate block max-w-[150px]" title={emp.company}>{emp.company || '-'}</span>
                    </td>
                    <td className="px-6 py-4 text-text-muted">{emp.admission_date ? new Date(emp.admission_date).toLocaleDateString('pt-BR') : '-'}</td>
                    <td className="px-6 py-4 text-text-muted">{typeof emp.salary === 'number' ? emp.salary.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '-'}</td>
                    <td className="px-6 py-4 text-text-muted">
                      <div className="flex items-center gap-3">
                        <span className="truncate block max-w-[100px]" title={emp.notes}>{emp.notes || '-'}</span>
                        <button 
                          onClick={() => {
                            setSelectedEmp(emp);
                            setNotes(emp.notes || '');
                          }}
                          className="text-gold hover:text-gold/80 transition-colors p-1"
                          title="Editar Observação"
                        >
                          <Edit2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {selectedEmp && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-sidebar border border-border rounded-xl w-full max-w-lg p-6 shadow-2xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-text-primary">
                Observação / Correção
              </h3>
              <button onClick={() => setSelectedEmp(null)} className="text-text-muted hover:text-text-primary">
                <X size={20} />
              </button>
            </div>
            
            <div className="mb-4">
              <p className="text-sm text-text-muted mb-1">Colaborador:</p>
              <p className="font-medium text-text-primary">{selectedEmp.name} (#{selectedEmp.code})</p>
            </div>

            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Digite correções ou anotações que devem persistir..."
              className="w-full h-32 bg-background border border-border rounded-lg p-3 text-text-primary focus:outline-none focus:border-gold resize-none"
            />
            
            <div className="flex justify-end gap-3 mt-6">
              <button 
                onClick={() => setSelectedEmp(null)}
                className="px-4 py-2 rounded-lg bg-white/5 text-text-primary hover:bg-white/10 transition-colors"
              >
                Cancelar
              </button>
              <button 
                onClick={handleSaveNote}
                disabled={updateNote.isPending}
                className="px-4 py-2 rounded-lg bg-gold text-background font-medium hover:bg-gold/90 transition-colors disabled:opacity-50"
              >
                {updateNote.isPending ? 'Salvando...' : 'Salvar Observação'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
