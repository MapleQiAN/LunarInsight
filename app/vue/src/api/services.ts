import api from './index'

// Types
export interface DashboardStats {
  total_nodes: number
  total_edges: number
  node_labels: Record<string, number>
  edge_types: Record<string, number>
}

export interface UploadResponse {
  id: string
  filename: string
  file_size: number
  status: string
}

export interface IngestionResponse {
  job_id: string
  status: string
}

export interface GraphNode {
  id: string
  labels: string[]
  properties: Record<string, any>
}

export interface GraphEdge {
  id: string
  type: string
  source: string
  target: string
  properties: Record<string, any>
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface JobStatus {
  job_id: string
  status: string
  progress?: number
  message?: string
  error?: string
}

export interface AISettings {
  provider: string
  model_name: string
  api_key?: string
  base_url?: string
  temperature?: number
}

export interface Settings {
  ai: AISettings
  [key: string]: any
}

// Dashboard
export const getDashboardStats = (): Promise<DashboardStats> => 
  api.get('/graph/stats')

// Upload
export const uploadFile = (file: File): Promise<UploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/uploads', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const startIngestion = (documentId: string): Promise<IngestionResponse> => 
  api.post(`/ingest/${documentId}`)

// Graph
export const getGraphData = (limit: number = 100): Promise<GraphData> => 
  api.get('/graph/query', {
    params: {
      cypher: `MATCH (n)-[r]->(m) RETURN n, r, m LIMIT ${limit}`
    }
  })

// Query
export const executeCypherQuery = (cypher: string): Promise<any> => 
  api.get('/graph/query', { params: { cypher } })

export const getNodes = (label: string | null = null, limit: number = 100): Promise<GraphNode[]> => {
  const params: Record<string, any> = { limit }
  if (label) {
    params.label = label
  }
  return api.get('/graph/nodes', { params })
}

export const getEdges = (relType: string | null = null, limit: number = 100): Promise<GraphEdge[]> => {
  const params: Record<string, any> = { limit }
  if (relType) {
    params.rel_type = relType
  }
  return api.get('/graph/edges', { params })
}

// Status
export const getJobStatus = (jobId: string): Promise<JobStatus> => 
  api.get(`/ingest/status/${jobId}`)

// Settings
export const getSettings = (): Promise<Settings> => 
  api.get('/settings/')

export const updateAISettings = (settings: AISettings): Promise<any> => 
  api.post('/settings/ai', settings)

export const testAIConnection = (settings: AISettings): Promise<any> => 
  api.post('/settings/test-connection', settings)

export const getOllamaModels = (): Promise<string[]> => 
  api.get('/settings/ollama/models')

