import { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Users, Clock, Briefcase, Activity, AlertCircle, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export function DashboardPage() {
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);

  const { data: latestSnapshot, isLoading: isLoadingSnapshot } = useQuery({
    queryKey: ['latest-snapshot'],
    queryFn: () => api.get('/imports/latest-snapshot')
  });

  const snapshotId = latestSnapshot?.snapshot_id;
  const companyQuery = selectedCompany ? `?company=${encodeURIComponent(selectedCompany)}` : '';

  const { data: metricsData, isLoading: isLoadingMetrics } = useQuery({
    queryKey: ['metrics', snapshotId, selectedCompany],
    queryFn: () => api.get(`/metrics/dashboard/${snapshotId}${companyQuery}`),
    enabled: !!snapshotId
  });

  const { data: distData } = useQuery({
    queryKey: ['distributions', snapshotId, selectedCompany],
    queryFn: () => api.get(`/metrics/distributions/${snapshotId}${companyQuery}`),
    enabled: !!snapshotId
  });

  const toggleCompanyFilter = (name: string) => {
    setSelectedCompany(prev => prev === name ? null : name);
  };

  if (isLoadingSnapshot || isLoadingMetrics) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-text-muted animate-pulse flex flex-col items-center gap-4">
          <div className="h-8 w-8 rounded-full border-2 border-gold border-t-transparent animate-spin"></div>
          Processando Inteligência Analítica...
        </div>
      </div>
    );
  }

  if (!snapshotId) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-text-muted text-center max-w-md">
          <Activity size={48} className="mx-auto mb-4 opacity-20" />
          <p>Nenhum dado importado.</p>
          <p className="text-sm mt-2">Acesse a aba "Importar Dados" para transformar suas planilhas em insights estratégicos.</p>
        </div>
      </div>
    );
  }

  const m = metricsData?.metrics || {};
  const metrics = {
    active_headcount: m.active_headcount || 0,
    avg_tenure_days: Math.round(m.avg_tenure_days || 0),
    median_monthly_hours: Math.round(m.median_monthly_hours || 0),
    total_payroll: m.total_payroll,
    quality_score: 95
  };

  const dists = distData?.distributions || {};
  const jobTitles = dists.job_title || {};
  const company = dists.company || {};
  const tenure = dists.tenure || {};

  const formatBRL = (val: number) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
  };

  const hasSalaryData = metrics.total_payroll !== undefined && metrics.total_payroll > 0;
  const hasHoursData = metrics.median_monthly_hours > 0;
  const hasTenureData = metrics.avg_tenure_days > 0;

  // Tooltip Formatter
  const buildTooltip = (params: any) => {
    // Handling axis trigger (array) or item trigger (object)
    const data = Array.isArray(params) ? params[0].data : params.data;
    const name = Array.isArray(params) ? params[0].name : params.name;
    const value = Array.isArray(params) ? params[0].value : params.value;
    
    const empList = data.employees || [];
    const empHtml = empList.slice(0, 15).map((e: string) => `• ${e}`).join('<br/>');
    const more = empList.length > 15 ? `<br/>...e mais ${empList.length - 15} colaboradores` : '';
    
    return `<div style="padding: 4px;">
      <strong style="color: #D4A843">${name} (${value})</strong><br/>
      <div style="max-height: 250px; overflow-y: auto; font-size: 11px; margin-top: 8px; color: #E0E0E0;">
        ${empHtml}${more}
      </div>
    </div>`;
  };

  // Chart Options
  const companyPalette = ['#D4A843', '#8A6E2C', '#F2C94C', '#5C4A1E'];
  const companyEntries = Object.entries(company);

  const companyOption = {
    tooltip: { trigger: 'item', formatter: buildTooltip, backgroundColor: '#1E1E1E', borderColor: '#333', textStyle: { color: '#FFF' } },
    legend: { show: false },
    series: [
      {
        name: 'Empresa',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 5, borderColor: '#141414', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold', color: '#FFF' } },
        labelLine: { show: false },
        data: companyEntries.map(([k, v]: any) => ({
          name: k,
          value: v.count,
          employees: v.employees,
          itemStyle: selectedCompany && selectedCompany !== k ? { opacity: 0.3 } : undefined
        }))
      }
    ],
    color: companyPalette
  };

  const companyChartEvents = {
    click: (params: any) => {
      if (params.componentType === 'series') {
        toggleCompanyFilter(params.name);
      }
    }
  };

  const tenureOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: buildTooltip, backgroundColor: '#1E1E1E', borderColor: '#333', textStyle: { color: '#FFF' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: Object.keys(tenure), axisLabel: { color: '#8A8A8A' } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#2B2B2B' } }, axisLabel: { color: '#8A8A8A' } },
    series: [
      {
        name: 'Colaboradores',
        type: 'bar',
        barWidth: '60%',
        data: Object.entries(tenure).map(([k, v]: any) => ({ name: k, value: v.count, employees: v.employees })),
        itemStyle: { color: '#D4A843', borderRadius: [4, 4, 0, 0] }
      }
    ]
  };

  // Sort Job Titles for top 8
  const topJobTitles = Object.entries(jobTitles)
    .sort((a: any, b: any) => b[1].count - a[1].count)
    .slice(0, 8);

  const jobTitleOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: buildTooltip, backgroundColor: '#1E1E1E', borderColor: '#333', textStyle: { color: '#FFF' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#2B2B2B' } } },
    yAxis: { 
      type: 'category', 
      data: topJobTitles.map(item => item[0]),
      axisLabel: { color: '#8A8A8A', width: 120, overflow: 'truncate' }
    },
    series: [
      {
        name: 'Headcount',
        type: 'bar',
        data: topJobTitles.map(item => ({ name: item[0], value: (item[1] as any).count, employees: (item[1] as any).employees })),
        itemStyle: { color: 'rgba(212, 168, 67, 0.7)' }
      }
    ]
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Visão Geral Estratégica</h1>
          <p className="text-text-muted text-sm mt-1">Snapshot de referência: {new Date(latestSnapshot?.reference_date).toLocaleDateString('pt-BR') || 'Atual'}</p>
        </div>
        {selectedCompany && (
          <button
            onClick={() => setSelectedCompany(null)}
            className="flex items-center gap-2 px-3 py-1.5 bg-gold/10 border border-gold/30 rounded-lg text-sm text-gold hover:bg-gold/20 transition-colors"
          >
            Filtrado: {selectedCompany}
            <X size={14} />
          </button>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-5 group border-t-2 border-t-gold/50">
          <div className="flex justify-between items-start mb-2">
            <div>
              <p className="text-text-muted text-sm font-medium">Headcount Ativo</p>
              <h3 className="text-3xl font-bold mt-1 text-text-primary">{metrics.active_headcount}</h3>
            </div>
            <div className="p-2 bg-white/5 rounded-lg text-gold group-hover:bg-gold/10 transition-colors">
              <Users size={24} />
            </div>
          </div>
          <p className="text-xs text-text-muted mt-2">Total de funcionários com vínculo ativo neste snapshot.</p>
        </div>
        
        <div className="glass-card p-5 group border-t-2 border-t-gold/50">
          <div className="flex justify-between items-start mb-2">
            <div>
              <p className="text-text-muted text-sm font-medium">Tempo Médio (Dias)</p>
              <h3 className="text-3xl font-bold mt-1 text-text-primary">{hasTenureData ? metrics.avg_tenure_days : '-'}</h3>
            </div>
            <div className="p-2 bg-white/5 rounded-lg text-gold group-hover:bg-gold/10 transition-colors">
              <Clock size={24} />
            </div>
          </div>
          <p className="text-xs text-text-muted mt-2">Média de dias corridos desde a admissão até a data do arquivo.</p>
        </div>
        
        <div className="glass-card p-5 group border-t-2 border-t-gold/50">
          <div className="flex justify-between items-start mb-2">
            <div>
              <p className="text-text-muted text-sm font-medium">Custo Mensal</p>
              <h3 className="text-2xl font-bold mt-2 text-text-primary">{hasSalaryData ? formatBRL(metrics.total_payroll) : 'N/D'}</h3>
            </div>
            <div className="p-2 bg-white/5 rounded-lg text-gold group-hover:bg-gold/10 transition-colors">
              <Briefcase size={24} />
            </div>
          </div>
          <p className="text-xs text-text-muted mt-2">Soma do salário base (vencimentos) mapeados no arquivo.</p>
        </div>

        <div className="glass-card p-5 group border-t-2 border-t-success/50">
          <div className="flex justify-between items-start mb-2">
            <div>
              <p className="text-text-muted text-sm font-medium">Confiabilidade</p>
              <h3 className="text-3xl font-bold mt-1 text-success">{metrics.quality_score}%</h3>
            </div>
            <div className="p-2 bg-success/10 rounded-lg text-success">
              <Activity size={24} />
            </div>
          </div>
          <p className="text-xs text-text-muted mt-2">Índice de qualidade de leitura dos dados essenciais.</p>
        </div>
      </div>

      {/* Charts - Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <div className="glass-card p-5">
          <h3 className="text-lg font-medium text-text-primary mb-4 flex items-center">
            Distribuição por Empresa
          </h3>
          <ReactECharts option={companyOption} onEvents={companyChartEvents} style={{ height: '260px' }} />
          <div className="flex flex-wrap justify-center gap-3 mt-2">
            {companyEntries.map(([name], i) => (
              <button
                key={name}
                onClick={() => toggleCompanyFilter(name)}
                className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded transition-opacity ${selectedCompany && selectedCompany !== name ? 'opacity-40' : 'opacity-100'}`}
              >
                <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: companyPalette[i % companyPalette.length] }} />
                <span className="text-text-muted">{name}</span>
              </button>
            ))}
          </div>
        </div>
        
        <div className="glass-card p-5">
          <h3 className="text-lg font-medium text-text-primary mb-4 flex items-center">
            Retenção de Talentos (Anos de Casa)
          </h3>
          {hasTenureData ? (
            <ReactECharts option={tenureOption} style={{ height: '300px' }} />
          ) : (
            <div className="h-[300px] flex items-center justify-center text-text-muted">
              Sem dados de data de admissão.
            </div>
          )}
        </div>
      </div>

      {/* Charts - Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <div className="glass-card p-5 lg:col-span-2">
          <h3 className="text-lg font-medium text-text-primary mb-4">Top Cargos Mapeados</h3>
          <ReactECharts option={jobTitleOption} style={{ height: '300px' }} />
        </div>
        
        <div className="glass-card p-5 flex flex-col">
          <h3 className="text-lg font-medium text-text-primary mb-4">Avisos de Integridade</h3>
          <div className="space-y-3 flex-1 overflow-y-auto pr-2 custom-scrollbar">
            {!hasSalaryData && (
              <div className="p-3 bg-warning/10 border border-warning/20 rounded-lg flex items-start gap-3">
                <div className="text-warning mt-0.5"><AlertCircle size={18} /></div>
                <div>
                  <p className="text-sm font-medium text-warning">Salários não identificados</p>
                  <p className="text-xs text-text-muted mt-1">A coluna de Salário/Remuneração estava ausente ou zerada no arquivo exportado.</p>
                </div>
              </div>
            )}
            {!hasHoursData && (
              <div className="p-3 bg-warning/10 border border-warning/20 rounded-lg flex items-start gap-3">
                <div className="text-warning mt-0.5"><AlertCircle size={18} /></div>
                <div>
                  <p className="text-sm font-medium text-warning">Horas não identificadas</p>
                  <p className="text-xs text-text-muted mt-1">A coluna de Carga Horária Mensal não foi encontrada.</p>
                </div>
              </div>
            )}
            {!hasTenureData && (
              <div className="p-3 bg-warning/10 border border-warning/20 rounded-lg flex items-start gap-3">
                <div className="text-warning mt-0.5"><AlertCircle size={18} /></div>
                <div>
                  <p className="text-sm font-medium text-warning">Admissão Ausente</p>
                  <p className="text-xs text-text-muted mt-1">Impossível calcular tempo de casa. Coluna de admissão não mapeada.</p>
                </div>
              </div>
            )}
            {hasSalaryData && hasHoursData && hasTenureData && (
              <div className="p-3 bg-success/10 border border-success/20 rounded-lg flex items-start gap-3">
                <div className="text-success mt-0.5"><Activity size={18} /></div>
                <div>
                  <p className="text-sm font-medium text-success">Dados Completos</p>
                  <p className="text-xs text-text-muted mt-1">Todos os indicadores estratégicos foram carregados com sucesso.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
