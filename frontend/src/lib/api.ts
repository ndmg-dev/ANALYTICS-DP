const API_BASE = 'http://localhost:8000/api/v1';

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
  }
};
