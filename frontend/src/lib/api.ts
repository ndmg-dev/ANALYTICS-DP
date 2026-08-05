const API_BASE = '/api/v1';
const TOKEN_KEY = 'dp_access_token';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

const authHeaders = (): Record<string, string> => {
  const token = getToken();
  return token ? { 'X-Access-Token': token } : {};
};

const handleResponse = async (response: Response) => {
  if (response.status === 401) {
    clearToken();
    window.location.reload();
    throw new Error('Sessão expirada');
  }
  if (!response.ok) throw new Error('API request failed');
  return response.json();
};

/** Appends query params, skipping null/undefined so callers don't have to
 *  build the query string by hand for every optional filter. */
export const withQuery = (endpoint: string, params: Record<string, any> = {}) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      search.append(key, String(value));
    }
  });
  const qs = search.toString();
  return qs ? `${endpoint}?${qs}` : endpoint;
};

export const api = {
  get: async (endpoint: string) => {
    const response = await fetch(`${API_BASE}${endpoint}`, { headers: authHeaders() });
    return handleResponse(response);
  },
  post: async (endpoint: string, body?: FormData) => {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: authHeaders(),
      body
    });
    return handleResponse(response);
  },
  patch: async (endpoint: string, body: any) => {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body)
    });
    return handleResponse(response);
  },
  postJson: async (endpoint: string, body: any) => {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body)
    });
    return handleResponse(response);
  },
  put: async (endpoint: string, body: any) => {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body)
    });
    return handleResponse(response);
  }
};
