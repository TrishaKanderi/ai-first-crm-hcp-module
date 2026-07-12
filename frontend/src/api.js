import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

export const listInteractions = (hcpName) =>
  api.get('/api/interactions/', { params: hcpName ? { hcp_name: hcpName } : {} })

export const createInteraction = (payload) => api.post('/api/interactions/', payload)

export const updateInteraction = (id, payload) => api.patch(`/api/interactions/${id}`, payload)

export const sendChatMessage = (message, activeInteractionId) =>
  api.post('/api/chat/', { message, active_interaction_id: activeInteractionId ?? null })
