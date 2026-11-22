
const API_BASE_URL = 'http://localhost:8000'

export async function getParkingStatus() {
  const response = await fetch(`${API_BASE_URL}/api/parking/status`)

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export async function checkBackend() {
  const response = await fetch(`${API_BASE_URL}/`)

  if (!response.ok) {
    throw new Error(`Backend error: ${response.status}`)
  }

  return response.json()
}
