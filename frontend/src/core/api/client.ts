/**
 * API Client 基础设施
 *
 * 提供统一的 HTTP 请求封装、错误处理和 Mock 支持
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import type { ErrorResponse } from '@/shared/types';

// ==================== 类型定义 ====================

/**
 * 修正后的 Axios 实例类型
 * 由于响应拦截器返回 response.data，实际返回类型是 T 而不是 AxiosResponse<T>
 */
interface ApiClient extends Omit<AxiosInstance, 'get' | 'post' | 'put' | 'patch' | 'delete'> {
  get<T = any>(url: string, config?: any): Promise<T>;
  post<T = any>(url: string, data?: any, config?: any): Promise<T>;
  put<T = any>(url: string, data?: any, config?: any): Promise<T>;
  patch<T = any>(url: string, data?: any, config?: any): Promise<T>;
  delete<T = any>(url: string, config?: any): Promise<T>;
}

// ==================== API 错误类 ====================

/**
 * 统一的 API 错误类
 */
export class ApiError extends Error {
  code: string;
  status: number;
  data?: any;

  constructor(code: string, message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.data = data;
  }

  /**
   * 从后端错误响应创建 ApiError
   */
  static fromResponse(error: AxiosError<ErrorResponse>): ApiError {
    const response = error.response;
    if (response?.data) {
      return new ApiError(
        response.data.error_code || 'UNKNOWN_ERROR',
        response.data.message || error.message,
        response.status,
        response.data
      );
    }

    // 网络错误或其他错误
    return new ApiError('NETWORK_ERROR', error.message || '网络请求失败', 0);
  }
}

// ==================== Axios 实例配置 ====================

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const timeout = 30000; // 30 秒超时

const apiClient = axios.create({
  baseURL,
  timeout,
  headers: {
    'Content-Type': 'application/json',
  },
}) as ApiClient;

// ==================== 请求拦截器 ====================

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 添加认证 token（如有）
    const token = localStorage.getItem('auth_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 开发模式下打印请求日志
    if (import.meta.env.DEV && import.meta.env.VITE_DEBUG === 'true') {
      console.log('[API Request]', config.method?.toUpperCase(), config.url, config.data);
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ==================== 响应拦截器 ====================

apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // 开发模式下打印响应日志
    if (import.meta.env.DEV && import.meta.env.VITE_DEBUG === 'true') {
      console.log('[API Response]', response.config.url, response.data);
    }

    // 直接返回 data，简化调用
    return response.data;
  },
  (error: AxiosError<ErrorResponse>) => {
    // 将 Axios 错误转换为 ApiError
    const apiError = ApiError.fromResponse(error);

    // 开发模式下打印错误日志
    if (import.meta.env.DEV) {
      console.error('[API Error]', apiError);
    }

    return Promise.reject(apiError);
  }
);

// ==================== Mock 支持 ====================

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

/**
 * 可 Mock 的请求包装
 *
 * 根据环境变量决定返回 mock 数据还是真实请求
 */
export async function mockableRequest<T>(realRequest: () => Promise<T>, mockData: T): Promise<T> {
  if (USE_MOCK) {
    // Mock 模式：延迟 200-500ms 模拟网络延迟
    const delay = 200 + Math.random() * 300;
    return new Promise((resolve) => {
      setTimeout(() => resolve(mockData), delay);
    });
  }

  return realRequest();
}

// ==================== 导出 ====================

export default apiClient;
export { USE_MOCK };
