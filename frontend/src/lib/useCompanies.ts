import { useQuery } from '@tanstack/react-query';
import { api } from './api';

export type TaxRegime = 'NORMAL' | 'SIMPLES_NACIONAL';

export const TAX_REGIME_LABELS: Record<TaxRegime, string> = {
  NORMAL: 'Regime Normal',
  SIMPLES_NACIONAL: 'Simples Nacional'
};

export interface CompanyOption {
  id: number;
  name: string;
  cnpj: string | null;
  tax_regime: TaxRegime;
  tax_regime_label: string;
  employee_count: number;
}

/** The company registry, shared by every company filter in the app. */
export function useCompanies() {
  return useQuery<CompanyOption[]>({
    queryKey: ['companies'],
    queryFn: () => api.get('/companies/'),
    staleTime: 60_000
  });
}
