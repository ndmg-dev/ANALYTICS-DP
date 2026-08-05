import { useQuery } from '@tanstack/react-query';
import { api } from './api';

export interface CompanyOption {
  id: number;
  name: string;
  cnpj: string | null;
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
