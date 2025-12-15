const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://vs-6lye.onrender.com'

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export interface AuditResult {
  audit_id: number
  url: string
  domain: string
  page_count: number
  packs: string[]
  plan: string
  scores: {
    overall: number
    by_category: Record<string, number>
  }
  findings: Finding[]
  timestamp: string
}

export interface Finding {
  id: string
  title: string
  category: string
  status: 'pass' | 'fail' | 'warning'
  confidence?: number
  evidence?: string[]
  why?: string
  fix?: string
  fix_snippet?: string
  acceptance_test?: string
}

export interface AuditHistoryItem {
  id: number
  url: string
  domain: string
  overall_score: number
  category_scores: Record<string, number>
  page_count: number
  created_at: string
}

export interface CitationResult {
  assistant: string
  cited: boolean
  response: string
}

export interface CitationStats {
  brand: string
  total_queries: number
  overall_rate: number
  chatgpt_rate?: number
  claude_rate?: number
}

export interface Plan {
  id: string
  name: string
  price: number
  max_pages: number
  packs: string[]
  features: string[]
}

export interface User {
  id: number
  email: string
  name?: string
  created_at: string
}

export interface AuthResponse {
  user: User
  token: string
}

class ApiClient {
  private baseUrl: string
  private token: string | null = null

  constructor() {
    this.baseUrl = API_URL
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('token')
    }
  }

  setToken(token: string) {
    this.token = token
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token)
    }
  }

  clearToken() {
    this.token = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token')
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
      })

      const data = await response.json()
      return data
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'An error occurred',
      }
    }
  }

  // Auth
  async signup(email: string, password: string, name?: string): Promise<ApiResponse<AuthResponse>> {
    return this.request<AuthResponse>('/api/v1/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    })
  }

  async login(email: string, password: string): Promise<ApiResponse<AuthResponse>> {
    return this.request<AuthResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async getMe(): Promise<ApiResponse<User>> {
    return this.request<User>('/api/v1/auth/me')
  }

  // Audits
  async runAudit(url: string, packs: string[] = ['base'], plan: string = 'quickscan'): Promise<ApiResponse<AuditResult>> {
    return this.request<AuditResult>('/api/audit', {
      method: 'POST',
      body: JSON.stringify({ url, packs, plan }),
    })
  }

  async getAuditHistory(domain?: string, limit: number = 10): Promise<ApiResponse<AuditHistoryItem[]>> {
    const params = new URLSearchParams()
    if (domain) params.append('domain', domain)
    params.append('limit', limit.toString())
    
    const result = await this.request<{ data: AuditHistoryItem[]; count: number }>(
      `/api/audit/history?${params.toString()}`
    )
    return {
      success: result.success,
      data: result.data?.data,
      error: result.error,
    }
  }

  async getAuditDetail(auditId: number): Promise<ApiResponse<AuditResult>> {
    const result = await this.request<{ data: AuditResult }>(`/api/audit/${auditId}`)
    return {
      success: result.success,
      data: result.data?.data,
      error: result.error,
    }
  }

  // Citations
  async trackCitations(brand: string, intent: string, assistants: string[] = ['chatgpt', 'claude']): Promise<ApiResponse<{ results: CitationResult[]; summary: any }>> {
    const result = await this.request<{ data: { results: CitationResult[]; summary: any } }>('/api/citations/track', {
      method: 'POST',
      body: JSON.stringify({ brand, intent, assistants }),
    })
    return {
      success: result.success,
      data: result.data?.data,
      error: result.error,
    }
  }

  async getCitationStats(brand: string): Promise<ApiResponse<CitationStats>> {
    const result = await this.request<{ data: CitationStats }>(`/api/citations/stats?brand=${encodeURIComponent(brand)}`)
    return {
      success: result.success,
      data: result.data?.data,
      error: result.error,
    }
  }

  // Plans
  async getPlans(): Promise<ApiResponse<Plan[]>> {
    const result = await this.request<{ data: Plan[] }>('/api/plans')
    return {
      success: result.success,
      data: result.data?.data,
      error: result.error,
    }
  }
}

export const apiClient = new ApiClient()
