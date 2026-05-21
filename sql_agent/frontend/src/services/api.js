const BASE = '/api'

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      // ignore parse error
    }
    throw new Error(detail)
  }
  return res.json()
}

export async function runTextQuery(query, dialect = 'Oracle') {
  const res = await fetch(`${BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, dialect }),
  })
  return handleResponse(res)
}

export async function runVoiceQuery(audioBlob, filename, dialect = 'Oracle') {
  const form = new FormData()
  form.append('audio', audioBlob, filename)
  const res = await fetch(`${BASE}/voice?dialect=${encodeURIComponent(dialect)}`, {
    method: 'POST',
    body: form,
  })
  return handleResponse(res)
}

export async function checkHealth() {
  try {
    const res = await fetch(`${BASE}/health`)
    return res.ok
  } catch {
    return false
  }
}
