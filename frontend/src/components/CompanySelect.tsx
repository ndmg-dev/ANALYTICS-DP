import { useCompanies } from '../lib/useCompanies';

interface CompanySelectProps {
  value: number | null;
  onChange: (companyId: number | null) => void;
  label?: string;
  allLabel?: string;
  /** Hide companies with no active employees (default: true). */
  onlyWithEmployees?: boolean;
}

/** Company filter shared by the dashboard, the employee list and the upload
 *  form, so all three always offer the same set of companies. */
export function CompanySelect({
  value,
  onChange,
  label = 'Empresa',
  allLabel = 'Todas as Empresas',
  onlyWithEmployees = true
}: CompanySelectProps) {
  const { data: companies = [] } = useCompanies();
  const options = onlyWithEmployees
    ? companies.filter(c => c.employee_count > 0 || c.id === value)
    : companies;

  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-xs text-text-muted">{label}</label>}
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        className="bg-sidebar border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-gold"
      >
        <option value="">{allLabel}</option>
        {options.map(c => (
          <option key={c.id} value={c.id}>
            {c.name}{c.employee_count ? ` (${c.employee_count})` : ''}
          </option>
        ))}
      </select>
    </div>
  );
}
