import api from './index'

// Types
export interface DashboardStats {
  total_nodes: number
  total_edges: number
  node_labels: Record<string, number>
  edge_types: Record<string, number>
}

export interface UploadResponse {
  documentId: string
  filename: string
  checksum: string
  status: string
  jobId?: string
  message?: string
  path?: string
  sourceUrl?: string
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
  jobId?: string
  documentId?: string
  status: string
  progress?: number
  message?: string
  error?: string
  stats?: {
    chunks: number
    triplets: number
    concepts: number
    textLength?: number
  }
  ai_mode?: boolean
  ai_stats?: {
    total_tokens?: number
    prompt_tokens?: number
    completion_tokens?: number
    model?: string
  }
  insights?: string[]
}

export interface AIProvider {
  id: string
  name: string
  default_model: string
  requires_api_key: boolean
}

export interface AISettings {
  ai_provider: string
  ai_api_key?: string
  ai_model?: string
  ai_base_url?: string
  // 旧配置（向后兼容）
  openai_api_key?: string
  openai_model?: string
  openai_base_url?: string
  ollama_base_url?: string
  ollama_model?: string
}

export interface Settings extends AISettings {
  neo4j_uri: string
  neo4j_user: string
  redis_url: string
  [key: string]: any
}

// Dashboard
export const getDashboardStats = (): Promise<DashboardStats> => 
  api.get('/graph/stats')

// Upload - 统一使用 /uploads/process 接口，自动处理
export const uploadFile = (
  file: File, 
  options?: {
    enableAI?: boolean
    userPrompt?: string
    optimizePrompt?: boolean
  }
): Promise<UploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('auto_process', 'true')
  
  if (options?.enableAI) {
    formData.append('enable_ai_segmentation', 'true')
    if (options.userPrompt) {
      formData.append('user_prompt', options.userPrompt)
    }
    if (options.optimizePrompt !== undefined) {
      formData.append('optimize_prompt', options.optimizePrompt.toString())
    }
  }
  
  return api.post('/uploads/process', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const uploadText = (
  content: string, 
  title?: string, 
  autoProcess: boolean = true,
  options?: {
    enableAI?: boolean
    userPrompt?: string
    optimizePrompt?: boolean
  }
): Promise<UploadResponse> => {
  const payload: any = { 
    content, 
    title, 
    auto_process: autoProcess 
  }
  
  if (options?.enableAI) {
    payload.enable_ai_segmentation = true
    if (options.userPrompt) {
      payload.user_prompt = options.userPrompt
    }
    if (options.optimizePrompt !== undefined) {
      payload.optimize_prompt = options.optimizePrompt
    }
  }
  
  return api.post('/uploads/text', payload)
}

export const uploadUrl = (
  url: string, 
  title?: string, 
  autoProcess: boolean = true,
  options?: {
    enableAI?: boolean
    userPrompt?: string
    optimizePrompt?: boolean
  }
): Promise<UploadResponse> => {
  const payload: any = { 
    url, 
    title, 
    auto_process: autoProcess 
  }
  
  if (options?.enableAI) {
    payload.enable_ai_segmentation = true
    if (options.userPrompt) {
      payload.user_prompt = options.userPrompt
    }
    if (options.optimizePrompt !== undefined) {
      payload.optimize_prompt = options.optimizePrompt
    }
  }
  
  return api.post('/uploads/url', payload)
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

// Status - 统一使用 /uploads/status 接口
export const getJobStatus = (jobId: string): Promise<JobStatus> => 
  api.get(`/uploads/status/${jobId}`)

// Settings
export const getAIProviders = (): Promise<{ providers: AIProvider[] }> => 
  api.get('/settings/ai-providers')

export const getSettings = (): Promise<Settings> => 
  api.get('/settings/')

export const updateAISettings = (settings: AISettings): Promise<any> => 
  api.post('/settings/ai', settings)

export const testAIConnection = (settings: AISettings): Promise<any> => 
  api.post('/settings/test-connection', settings)

export const getOllamaModels = (): Promise<{ success: boolean; models: string[]; message?: string }> => 
  api.get('/settings/ollama/models')

