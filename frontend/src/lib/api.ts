const API_BASE = '/api/v1';

export const api = {
  get: async (endpoint: string) => {
    const response = await fetch(`${API_BASE}${endpoint}`);
    if (!response.ok) throw new Error('API request failed');
    return response.json();
  },
  post: async (endpoint: string, body: FormData) => {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      body
    });
    if (!response.ok) throw new Error('API request failed');
    return response.json();
  },
  put: async (endpoint: string, body: any) => {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!response.ok) throw new Error('API request failed');
    return response.json();
  }
};
