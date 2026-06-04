import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiError } from './client';
import type { AxiosError } from 'axios';
import type { ErrorResponse } from '@/shared/types';

describe('ApiError', () => {
  it('构造函数设置所有字段', () => {
    const err = new ApiError('TEST_CODE', '测试消息', 404, { detail: 'not found' });
    expect(err.name).toBe('ApiError');
    expect(err.code).toBe('TEST_CODE');
    expect(err.message).toBe('测试消息');
    expect(err.status).toBe(404);
    expect(err.data).toEqual({ detail: 'not found' });
  });

  it('继承自 Error', () => {
    const err = new ApiError('CODE', 'msg', 500);
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(ApiError);
  });

  describe('fromResponse', () => {
    it('从有 response.data 的 AxiosError 创建', () => {
      const axiosError = {
        message: 'Request failed',
        response: {
          status: 400,
          data: {
            error_code: 'VALIDATION_ERROR',
            message: '参数无效',
          } as ErrorResponse,
        },
      } as AxiosError<ErrorResponse>;

      const apiError = ApiError.fromResponse(axiosError);
      expect(apiError.code).toBe('VALIDATION_ERROR');
      expect(apiError.message).toBe('参数无效');
      expect(apiError.status).toBe(400);
      expect(apiError.data).toEqual({ error_code: 'VALIDATION_ERROR', message: '参数无效' });
    });

    it('response.data 为空时使用默认值', () => {
      const axiosError = {
        message: 'Network Error',
        response: undefined,
      } as unknown as AxiosError<ErrorResponse>;

      const apiError = ApiError.fromResponse(axiosError);
      expect(apiError.code).toBe('NETWORK_ERROR');
      expect(apiError.message).toBe('Network Error');
      expect(apiError.status).toBe(0);
    });

    it('response.data 缺少字段时使用默认值', () => {
      const axiosError = {
        message: 'Server Error',
        response: {
          status: 500,
          data: {} as ErrorResponse,
        },
      } as AxiosError<ErrorResponse>;

      const apiError = ApiError.fromResponse(axiosError);
      expect(apiError.code).toBe('UNKNOWN_ERROR');
      expect(apiError.message).toBe('Server Error');
      expect(apiError.status).toBe(500);
    });
  });
});

describe('mockableRequest', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('USE_MOCK=true 时返回 mock 数据', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const { mockableRequest } = await import('./client');
    const mockData = { id: 1, name: 'mock' };
    const realRequest = vi.fn();

    const result = await mockableRequest(realRequest, mockData);
    expect(result).toEqual(mockData);
    expect(realRequest).not.toHaveBeenCalled();
  });

  it('USE_MOCK=false 时调用 realRequest', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    const { mockableRequest } = await import('./client');
    const realData = { id: 2, name: 'real' };
    const realRequest = vi.fn().mockResolvedValue(realData);

    const result = await mockableRequest(realRequest, { id: 0, name: 'mock' });
    expect(result).toEqual(realData);
    expect(realRequest).toHaveBeenCalledOnce();
  });
});
