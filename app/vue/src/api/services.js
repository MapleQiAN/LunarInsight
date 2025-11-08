import api from './index'

// Dashboard
export const getDashboardStats = () => api.get('/graph/stats')

// Upload
export const uploadFile = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/uploads', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const startIngestion = (documentId) => 
  api.post(`/ingest/${documentId}`)

// Graph
export const getGraphData = (limit = 100) => 
  api.get('/graph/query', {
    params: {
      cypher: `MATCH (n)-[r]->(m) RETURN n, r, m LIMIT ${limit}`
    }
  })

// Query
export const executeCypherQuery = (cypher) => 
  api.get('/graph/query', { params: { cypher } })

export const getNodes = (label = null, limit = 100) => {
  const params = { limit }
  if (label) {
    params.label = label
  }
  return api.get('/graph/nodes', { params })
}

export const getEdges = (relType = null, limit = 100) => {
  const params = { limit }
  if (relType) {
    params.rel_type = relType
  }
  return api.get('/graph/edges', { params })
}

// Status
export const getJobStatus = (jobId) => 
  api.get(`/ingest/status/${jobId}`)

// Settings
export const getSettings = () => 
  api.get('/settings/')

export const updateAISettings = (settings) => 
  api.post('/settings/ai', settings)

export const testAIConnection = (settings) => 
  api.post('/settings/test-connection', settings)

export const getOllamaModels = () => 
  api.get('/settings/ollama/models')

