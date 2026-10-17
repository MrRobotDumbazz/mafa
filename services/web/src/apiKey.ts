const STORAGE_KEY = 'forte_api_key'

export function getApiKey(): string {
  return localStorage.getItem(STORAGE_KEY) ?? ''
}

export function setApiKey(key: string): void {
  if (key.trim()) {
    localStorage.setItem(STORAGE_KEY, key.trim())
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

export function hasApiKey(): boolean {
  return !!localStorage.getItem(STORAGE_KEY)
}
