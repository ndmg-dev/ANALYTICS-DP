import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, withQuery } from '../lib/api';
import { CompanySelect } from '../components/CompanySelect';
import { TAX_REGIME_LABELS, type TaxRegime } from '../lib/useCompanies';
import { Calculator, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

const formatBRL = (value: any) =>
  typeof value === 'number'
    ? value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : '-';

const formatPct = (rate: number) =>
  `${(rate * 100).toLocaleString('pt-BR', { minimumFractionDigits: 3, maximumFractionDigits: 3 })}%`;

export function PersonnelCostPage() {
  const queryClient = useQueryClient();
  const [filterCompanyId, setFilterCompanyId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['personnel-cost', filterCompanyId],
    queryFn: () => api.get(withQuery('/metrics/personnel-cost', { company_id: filterCompanyId }))
  });

  const updateRegime = useMutation({
    mutationFn: ({ companyId, regime }: { companyId: number, regime: TaxRegime }) =>
      api.patch(`/companies/${companyId}`, { tax_regime: regime }),
    onSuccess: () => {
      toast.success('Regime tributário atualizado.');
      queryClient.invalidateQueries({ queryKey: ['personnel-cost'] });
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['employees'] });
    },
    onError: (err: any) => toast.error(`Erro ao atualizar regime: ${err.message}`)
  });

  const rates = data?.rates;
  const companies = data?.companies ?? [];
  const totals = data?.totals;
  const missingSalary = totals?.headcount_without_salary ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Custo de Pessoal</h1>
          <p className="text-text-muted text-sm mt-1">
            Provisões trabalhistas mensais acumuladas sobre a folha, por empresa e regime tributário.
          </p>
        </div>
        <CompanySelect value={filterCompanyId} onChange={setFilterCompanyId} />
      </div>

      {/* The rate table behind every number on this page. The three
          provisions are identical in both regimes; only the employer social
          security load differs, so the two columns sit side by side. */}
      {rates && (
        <div className="glass-card overflow-hidden">
          <div className="p-5 border-b border-border">
            <h3 className="text-lg font-medium text-text-primary">Composição das Provisões</h3>
            <p className="text-text-muted text-xs mt-1">Percentuais aplicados sobre o salário-base de cada colaborador.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-text-muted">
                <tr>
                  <th className="px-6 py-3 font-medium">Componente</th>
                  <th className="px-6 py-3 font-medium">Fórmula</th>
                  <th className="px-6 py-3 font-medium text-right">Simples Nacional</th>
                  <th className="px-6 py-3 font-medium text-right">Regime Normal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {[
                  { label: 'Férias 1/12', formula: 'salário ÷ 12', key: 'vacation' },
                  { label: '1/3 sobre férias 1/12', formula: 'salário ÷ 36', key: 'vacation_bonus' },
                  { label: '13º salário 1/12', formula: 'salário ÷ 12', key: 'thirteenth' },
                  { label: 'FGTS sobre as provisões', formula: '8% das provisões', key: 'fgts' },
                  { label: 'INSS, RAT e Terceiros', formula: '28,8% das provisões', key: 'social_security' },
                ].map(({ label, formula, key }) => (
                  <tr key={key}>
                    <td className="px-6 py-3 text-text-primary">{label}</td>
                    <td className="px-6 py-3 text-text-muted text-xs">{formula}</td>
                    <td className="px-6 py-3 text-text-muted text-right">{formatPct(rates.SIMPLES_NACIONAL[key])}</td>
                    <td className="px-6 py-3 text-text-muted text-right">{formatPct(rates.NORMAL[key])}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-white/5 font-medium">
                <tr>
                  <td className="px-6 py-3 text-text-primary" colSpan={2}>Total sobre a folha</td>
                  <td className="px-6 py-3 text-gold text-right">{formatPct(rates.SIMPLES_NACIONAL.total)}</td>
                  <td className="px-6 py-3 text-gold text-right">{formatPct(rates.NORMAL.total)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {missingSalary > 0 && (
        <div className="p-4 bg-warning/10 border border-warning/20 rounded-lg flex items-start gap-3">
          <div className="text-warning mt-0.5"><AlertCircle size={18} /></div>
          <div>
            <p className="text-sm font-medium text-warning">
              {missingSalary} colaborador{missingSalary > 1 ? 'es' : ''} sem salário no arquivo importado
            </p>
            <p className="text-xs text-text-muted mt-1">
              As provisões abaixo cobrem apenas quem tem salário mapeado — o custo real é maior.
            </p>
          </div>
        </div>
      )}

      <div className="glass-card overflow-hidden">
        <div className="p-5 border-b border-border flex items-center gap-2">
          <Calculator size={20} className="text-gold" />
          <h3 className="text-lg font-medium text-text-primary">Provisões por Empresa</h3>
        </div>

        <div className="overflow-x-auto">
          {isLoading ? (
            <div className="p-8 text-center text-text-muted">Calculando provisões...</div>
          ) : companies.length === 0 ? (
            <div className="p-8 text-center text-text-muted">Nenhum dado disponível. Realize uma importação.</div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-white/5 text-text-muted">
                <tr>
                  <th className="px-6 py-3 font-medium">Empresa</th>
                  <th className="px-6 py-3 font-medium">Regime Tributário</th>
                  <th className="px-6 py-3 font-medium text-right">Colab.</th>
                  <th className="px-6 py-3 font-medium text-right">Folha Base</th>
                  <th className="px-6 py-3 font-medium text-right">Férias 1/12</th>
                  <th className="px-6 py-3 font-medium text-right">1/3 Férias</th>
                  <th className="px-6 py-3 font-medium text-right">13º 1/12</th>
                  <th className="px-6 py-3 font-medium text-right">FGTS</th>
                  <th className="px-6 py-3 font-medium text-right">INSS</th>
                  <th className="px-6 py-3 font-medium text-right">Provisões</th>
                  <th className="px-6 py-3 font-medium text-right">Custo Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {companies.map((row: any) => (
                  <tr key={row.company_id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4 font-medium text-text-primary">
                      {row.company}
                      {row.headcount_without_salary > 0 && (
                        <span className="block text-xs text-warning mt-0.5">
                          {row.headcount_without_salary} sem salário
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {/* Editable in place: the regime is a company attribute
                          nobody would think to look for on another screen. */}
                      <select
                        value={row.tax_regime}
                        disabled={updateRegime.isPending}
                        onChange={(e) => updateRegime.mutate({
                          companyId: row.company_id,
                          regime: e.target.value as TaxRegime
                        })}
                        className="bg-sidebar border border-border rounded-lg px-2 py-1.5 text-xs text-text-primary focus:outline-none focus:border-gold disabled:opacity-50"
                      >
                        {(Object.keys(TAX_REGIME_LABELS) as TaxRegime[]).map(regime => (
                          <option key={regime} value={regime}>{TAX_REGIME_LABELS[regime]}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-6 py-4 text-text-muted text-right">{row.headcount}</td>
                    <td className="px-6 py-4 text-text-muted text-right whitespace-nowrap">{formatBRL(row.salary_base)}</td>
                    <td className="px-6 py-4 text-text-muted text-right whitespace-nowrap">{formatBRL(row.vacation)}</td>
                    <td className="px-6 py-4 text-text-muted text-right whitespace-nowrap">{formatBRL(row.vacation_bonus)}</td>
                    <td className="px-6 py-4 text-text-muted text-right whitespace-nowrap">{formatBRL(row.thirteenth)}</td>
                    <td className="px-6 py-4 text-text-muted text-right whitespace-nowrap">{formatBRL(row.fgts)}</td>
                    <td className="px-6 py-4 text-text-muted text-right whitespace-nowrap">
                      {row.tax_regime === 'SIMPLES_NACIONAL'
                        ? <span className="text-text-muted/50" title="Isento no Simples Nacional">—</span>
                        : formatBRL(row.social_security)}
                    </td>
                    <td className="px-6 py-4 text-gold text-right whitespace-nowrap" title={`${formatPct(row.rates.total)} da folha`}>{formatBRL(row.total)}</td>
                    <td className="px-6 py-4 text-text-primary font-medium text-right whitespace-nowrap">{formatBRL(row.total_cost)}</td>
                  </tr>
                ))}
              </tbody>
              {totals && companies.length > 1 && (
                <tfoot className="bg-white/5 font-medium text-text-primary">
                  <tr>
                    <td className="px-6 py-4">Total</td>
                    <td className="px-6 py-4"></td>
                    <td className="px-6 py-4 text-right">{totals.headcount}</td>
                    <td className="px-6 py-4 text-right whitespace-nowrap">{formatBRL(totals.salary_base)}</td>
                    <td className="px-6 py-4 text-right whitespace-nowrap">{formatBRL(totals.vacation)}</td>
                    <td className="px-6 py-4 text-right whitespace-nowrap">{formatBRL(totals.vacation_bonus)}</td>
                    <td className="px-6 py-4 text-right whitespace-nowrap">{formatBRL(totals.thirteenth)}</td>
                    <td className="px-6 py-4 text-right whitespace-nowrap">{formatBRL(totals.fgts)}</td>
                    <td className="px-6 py-4 text-right whitespace-nowrap">{formatBRL(totals.social_security)}</td>
                    <td className="px-6 py-4 text-gold text-right whitespace-nowrap">{formatBRL(totals.total)}</td>
                    <td className="px-6 py-4 text-right whitespace-nowrap">{formatBRL(totals.total_cost)}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          )}
        </div>
      </div>

      <p className="text-xs text-text-muted">
        As três provisões são 1/12 da obrigação anual e não variam com o regime tributário. O
        que muda é o INSS patronal sobre elas: empresas do Simples Nacional são isentas, pois a
        contribuição já está no DAS. O FGTS incide nos dois regimes. A alíquota patronal de
        28,8% corresponde a INSS 20% + Terceiros 5,8% + RAT 3%, sem FAP.
      </p>
    </div>
  );
}
