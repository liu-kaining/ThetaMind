import { apiClient } from "./client"

export interface TaskExecutionEvent {
  type: "start" | "success" | "error" | "retry" | "info" | "progress"
  message: string
  timestamp: string
}

export interface TaskResponse {
  id: string
  task_type: string
  status: "PENDING" | "PROCESSING" | "SUCCESS" | "FAILED"
  result_ref: string | null
  error_message: string | null
  metadata: Record<string, any> | null
  execution_history?: TaskExecutionEvent[] | null
  prompt_used?: string | null
  model_used?: string | null
  started_at?: string | null
  retry_count: number
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface TaskListParams {
  limit?: number
  skip?: number
}

export interface TaskCreateRequest {
  task_type: string
  metadata?: Record<string, any> | null
}

export const taskService = {
  /**
   * Create a new background task
   */
  createTask: async (request: TaskCreateRequest): Promise<TaskResponse> => {
    const response = await apiClient.post<TaskResponse>("/api/v1/tasks", request)
    return response.data
  },

  /**
   * Get list of tasks for the current user
   */
  getTasks: async (params?: TaskListParams): Promise<TaskResponse[]> => {
    const response = await apiClient.get<TaskResponse[]>("/api/v1/tasks", {
      params: {
        limit: params?.limit ?? 20,
        skip: params?.skip ?? 0,
      },
    })
    return response.data
  },

  /**
   * Get a specific task by ID
   */
  getTask: async (id: string): Promise<TaskResponse> => {
    const response = await apiClient.get<TaskResponse>(`/api/v1/tasks/${id}`)
    return response.data
  },

  /**
   * Delete a task by ID
   */
  deleteTask: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/tasks/${id}`)
  },
}

