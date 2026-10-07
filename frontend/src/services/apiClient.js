// One place for all calls to the backend. Every component's API file builds on this.
export function getToken() {
  try {
    return sessionStorage.getItem('token');
  } catch {
    return null;
  }
}

export async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`/api/v1${path}`, {
    ...options,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    // response had no JSON body
  }
  if (res.status === 401 && token) {
    // The token expired or was rejected. Clear it and go back to the login page.
    try {
      sessionStorage.clear();
    } catch {
      // ignore
    }
    window.location.assign('/login');
  }
  if (!res.ok) {
    const err = new Error((data && data.error) || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}
