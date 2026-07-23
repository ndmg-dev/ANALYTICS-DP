import { useState, type FormEvent, type ReactNode } from 'react';
import { Lock } from 'lucide-react';
import { getToken, setToken } from '../lib/api';

export function LoginGate({ children }: { children: ReactNode }) {
  const [authorized, setAuthorized] = useState(!!getToken());
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      if (!response.ok) {
        setError('Senha incorreta.');
        return;
      }
      const data = await response.json();
      setToken(data.token);
      setAuthorized(true);
    } catch {
      setError('Erro ao conectar. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  if (authorized) return <>{children}</>;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm bg-sidebar border border-border rounded-xl p-8 shadow-2xl">
        <div className="w-12 h-12 rounded-full bg-gold/10 flex items-center justify-center text-gold mb-4 mx-auto">
          <Lock size={22} />
        </div>
        <h1 className="text-lg font-medium text-text-primary text-center mb-1">Acesso Restrito</h1>
        <p className="text-sm text-text-muted text-center mb-6">Analytics Platform</p>
        <input
          type="password"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Senha de acesso"
          className="w-full bg-background border border-border rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-gold mb-3"
        />
        {error && <p className="text-sm text-danger mb-3">{error}</p>}
        <button
          type="submit"
          disabled={loading || !password}
          className="w-full px-4 py-2 rounded-lg bg-gold text-background font-medium hover:bg-gold/90 transition-colors disabled:opacity-50"
        >
          {loading ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}
