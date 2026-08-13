import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, withQuery } from '../lib/api';
import { CompanySelect } from '../components/CompanySelect';
import { useCompanies } from '../lib/useCompanies';
import { Users, FileUser, Edit2, X, Download, ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';
import toast from 'react-hot-toast';
import ExcelJS from 'exceljs';
import { saveAs } from 'file-saver';

type SortKey = 'code' | 'name' | 'job_title' | 'category' | 'company' | 'admission_date'
  | 'salary' | 'provision_vacation' | 'provision_vacation_bonus' | 'provision_thirteenth'
  | 'provision_fgts' | 'provision_social_security' | 'provisions_total';
type SortDirection = 'asc' | 'desc';

const COLUMNS: { key: SortKey; label: string; title?: string }[] = [
  { key: 'code', label: 'Código' },
  { key: 'name', label: 'Nome' },
  { key: 'job_title', label: 'Cargo' },
  { key: 'category', label: 'Categoria' },
  { key: 'company', label: 'Empresa' },
  { key: 'admission_date', label: 'Admissão' },
  { key: 'salary', label: 'Salário' },
  { key: 'provision_vacation', label: 'Férias 1/12', title: 'Provisão mensal de férias: 1/12 do salário (8,333%)' },
  { key: 'provision_vacation_bonus', label: '1/3 Férias', title: 'Provisão mensal do terço constitucional: 1/36 do salário (2,778%)' },
  { key: 'provision_thirteenth', label: '13º 1/12', title: 'Provisão mensal de 13º salário: 1/12 do salário (8,333%)' },
  { key: 'provision_fgts', label: 'FGTS s/ Prov.', title: 'FGTS 8% sobre férias, 1/3 e 13º (1,556% do salário)' },
  { key: 'provision_social_security', label: 'INSS s/ Prov.', title: 'INSS, RAT e Terceiros 28,8% sobre as provisões (5,6% do salário). Zero no Simples Nacional.' },
  { key: 'provisions_total', label: 'Total Provisões', title: 'Simples Nacional: 21% do salário. Regime Normal: 26,6%.' },
];

const PROVISION_KEYS: SortKey[] = [
  'provision_vacation', 'provision_vacation_bonus', 'provision_thirteenth',
  'provision_fgts', 'provision_social_security', 'provisions_total'
];

const formatBRL = (value: any) =>
  typeof value === 'number'
    ? value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : '-';

/** Sort value for a column: dates and salary compare numerically, everything
 *  else as text. Returns null for missing values so they can be pushed to the
 *  bottom regardless of direction — a blank admission date sorting "earliest"
 *  would otherwise bury the real data. */
const sortValue = (emp: any, key: SortKey): string | number | null => {
  const raw = emp[key];
  if (raw === null || raw === undefined || raw === '' || raw === 'N/A') return null;
  if (key === 'salary' || PROVISION_KEYS.includes(key)) return typeof raw === 'number' ? raw : null;
  if (key === 'admission_date') {
    const time = new Date(raw).getTime();
    return Number.isNaN(time) ? null : time;
  }
  return String(raw);
};

export function EmployeesPage() {
  const queryClient = useQueryClient();
  const [selectedEmp, setSelectedEmp] = useState<any>(null);
  const [notes, setNotes] = useState('');

  // The company filter is applied server-side, so the option list comes from
  // the company registry rather than from whatever rows happen to be loaded.
  const [filterCompanyId, setFilterCompanyId] = useState<number | null>(null);
  const [filterDate, setFilterDate] = useState('');
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const { data: companies = [] } = useCompanies();

  const { data: latestSnapshot, isLoading: isLoadingSnapshot } = useQuery({
    queryKey: ['latest-snapshot'],
    queryFn: () => api.get('/imports/latest-snapshot')
  });

  const snapshotId = latestSnapshot?.snapshot_id;

  const { data: employees = [], isLoading } = useQuery({
    queryKey: ['employees', snapshotId, filterCompanyId],
    queryFn: () => api.get(withQuery(`/employees/snapshot/${snapshotId}`, { company_id: filterCompanyId })),
    enabled: !!snapshotId
  });

  const filteredEmployees = employees.filter((emp: any) => {
    let match = true;
    if (filterDate) {
      const empDate = emp.admission_date ? new Date(emp.admission_date).toISOString().split('T')[0] : '';
      if (empDate !== filterDate) match = false;
    }
    return match;
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      // Third click on the same column clears the sort and restores the
      // order the API returned.
      if (sortDirection === 'asc') setSortDirection('desc');
      else { setSortKey(null); setSortDirection('asc'); }
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  const sortedEmployees = sortKey
    ? [...filteredEmployees].sort((a: any, b: any) => {
        const va = sortValue(a, sortKey);
        const vb = sortValue(b, sortKey);
        if (va === null && vb === null) return 0;
        if (va === null) return 1;   // blanks always last
        if (vb === null) return -1;
        const cmp = typeof va === 'number' && typeof vb === 'number'
          ? va - vb
          : String(va).localeCompare(String(vb), 'pt-BR', { sensitivity: 'base', numeric: true });
        return sortDirection === 'asc' ? cmp : -cmp;
      })
    : filteredEmployees;

  const updateNote = useMutation({
    mutationFn: (data: { company: string, company_id: number, code: string, notes: string }) => api.put('/employees/notes', data),
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
      company_id: selectedEmp.company_id,
      code: selectedEmp.code,
      notes: notes
    });
  };

  const handleExportExcel = async () => {
    if (sortedEmployees.length === 0) {
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
      { header: 'Regime', key: 'tax_regime', width: 18 },
      { header: 'Admissão', key: 'admission_date', width: 15 },
      { header: 'Salário', key: 'salary', width: 18 },
      { header: 'Férias 1/12', key: 'provision_vacation', width: 16 },
      { header: '1/3 Férias 1/12', key: 'provision_vacation_bonus', width: 16 },
      { header: '13º 1/12', key: 'provision_thirteenth', width: 16 },
      { header: 'FGTS s/ Provisões', key: 'provision_fgts', width: 18 },
      { header: 'INSS s/ Provisões', key: 'provision_social_security', width: 18 },
      { header: 'Total Provisões', key: 'provisions_total', width: 18 },
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

    // Export follows what's on screen, sorting included.
    sortedEmployees.forEach((emp: any) => {
      worksheet.addRow({
        code: `#${emp.code}`,
        name: emp.name,
        job_title: emp.job_title,
        category: emp.category || '-',
        company: emp.company || '-',
        tax_regime: emp.tax_regime_label || '-',
        admission_date: emp.admission_date ? new Date(emp.admission_date).toLocaleDateString('pt-BR') : '-',
        // Money goes out as numbers with a currency format, not as text, so
        // the exported sheet can be summed and sorted in Excel.
        salary: emp.salary ?? null,
        provision_vacation: emp.provision_vacation ?? null,
        provision_vacation_bonus: emp.provision_vacation_bonus ?? null,
        provision_thirteenth: emp.provision_thirteenth ?? null,
        provision_fgts: emp.provision_fgts ?? null,
        provision_social_security: emp.provision_social_security ?? null,
        provisions_total: emp.provisions_total ?? null,
        notes: emp.notes || '-'
      });
    });

    ['salary', 'provision_vacation', 'provision_vacation_bonus', 'provision_thirteenth',
     'provision_fgts', 'provision_social_security', 'provisions_total']
      .forEach(key => { worksheet.getColumn(key).numFmt = 'R$ #,##0.00'; });

    const buffer = await workbook.xlsx.writeBuffer();
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const today = new Date().toISOString().split('T')[0];
    const companyName = companies.find(c => c.id === filterCompanyId)?.name ?? 'Todas';
    const slug = companyName.replace(/[^\w]+/g, '_').replace(/^_|_$/g, '');
    saveAs(blob, `Colaboradores_${slug}_${today}.xlsx`);
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
          <CompanySelect
            value={filterCompanyId}
            onChange={setFilterCompanyId}
            label="Filtrar por Empresa"
          />


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
            Total: {sortedEmployees.length}
          </div>
        </div>
        
        <div className="overflow-x-auto">
          {isLoadingSnapshot || isLoading ? (
            <div className="p-8 text-center text-text-muted">Carregando colaboradores...</div>
          ) : !snapshotId ? (
            <div className="p-8 text-center text-text-muted">Nenhum dado disponível. Realize uma importação.</div>
          ) : sortedEmployees.length === 0 ? (
            <div className="p-8 text-center text-text-muted">Nenhum colaborador encontrado neste snapshot.</div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-text-muted">
                <tr>
                  {COLUMNS.map(({ key, label, title }) => {
                    const isActive = sortKey === key;
                    return (
                      <th key={key} className="px-6 py-3 font-medium whitespace-nowrap">
                        <button
                          onClick={() => toggleSort(key)}
                          className={`flex items-center gap-1.5 transition-colors hover:text-text-primary ${isActive ? 'text-gold' : ''}`}
                          title={title ?? `Ordenar por ${label}`}
                        >
                          {label}
                          {!isActive
                            ? <ChevronsUpDown size={13} className="opacity-30" />
                            : sortDirection === 'asc'
                              ? <ChevronUp size={13} />
                              : <ChevronDown size={13} />}
                        </button>
                      </th>
                    );
                  })}
                  <th className="px-6 py-3 font-medium">Observações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {sortedEmployees.map((emp: any) => (
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
                    <td className="px-6 py-4 text-text-muted whitespace-nowrap">{formatBRL(emp.salary)}</td>
                    <td className="px-6 py-4 text-text-muted whitespace-nowrap">{formatBRL(emp.provision_vacation)}</td>
                    <td className="px-6 py-4 text-text-muted whitespace-nowrap">{formatBRL(emp.provision_vacation_bonus)}</td>
                    <td className="px-6 py-4 text-text-muted whitespace-nowrap">{formatBRL(emp.provision_thirteenth)}</td>
                    <td className="px-6 py-4 text-text-muted whitespace-nowrap">{formatBRL(emp.provision_fgts)}</td>
                    <td className="px-6 py-4 text-text-muted whitespace-nowrap" title={emp.tax_regime_label}>{formatBRL(emp.provision_social_security)}</td>
                    <td className="px-6 py-4 text-gold whitespace-nowrap">{formatBRL(emp.provisions_total)}</td>
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
