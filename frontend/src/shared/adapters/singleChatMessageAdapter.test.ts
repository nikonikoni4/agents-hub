import { describe, it, expect } from 'vitest';
import { adaptSingleChatMessages } from './singleChatMessageAdapter';
import type { SingleChatMessageApiItem } from '@/shared/types';

describe('adaptSingleChatMessages', () => {
  it('should convert single chat messages to unified message format', () => {
    const input: SingleChatMessageApiItem[] = [
      {
        id: '1',
        role: 'user',
        content: 'Hello',
        timestamp: '2024-01-01T00:00:00Z',
        model: 'claude',
      },
      {
        id: '2',
        role: 'assistant',
        content: 'Hi there',
        timestamp: '2024-01-01T00:00:01Z',
        model: 'claude',
      },
    ];

    const result = adaptSingleChatMessages(input);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      id: 1,
      speaker: 'user',
      content: 'Hello',
      timestamp: '2024-01-01T00:00:00Z',
      platform: 'claude',
      modified_files: [],
      permission_request: undefined,
    });
    expect(result[1]).toEqual({
      id: 2,
      speaker: 'assistant',
      content: 'Hi there',
      timestamp: '2024-01-01T00:00:01Z',
      platform: 'claude',
      modified_files: [],
      permission_request: undefined,
    });
  });

  it('should default platform to claude when model is missing', () => {
    const input: SingleChatMessageApiItem[] = [
      {
        id: '1',
        role: 'user',
        content: 'Test',
        timestamp: '2024-01-01T00:00:00Z',
        model: null,
      },
    ];

    const result = adaptSingleChatMessages(input);

    expect(result).toHaveLength(1);
    expect(result[0]!.platform).toBe('claude');
  });

  it('should parse string ids as numbers', () => {
    const input: SingleChatMessageApiItem[] = [
      {
        id: '42',
        role: 'user',
        content: 'Message',
        timestamp: '2024-01-01T00:00:00Z',
        model: 'claude',
      },
    ];

    const result = adaptSingleChatMessages(input);

    expect(result).toHaveLength(1);
    expect(result[0]!.id).toBe(42);
    expect(typeof result[0]!.id).toBe('number');
  });

  it('should map role assistant to speaker assistant', () => {
    const input: SingleChatMessageApiItem[] = [
      {
        id: '1',
        role: 'assistant',
        content: 'Response',
        timestamp: '2024-01-01T00:00:00Z',
        model: 'claude',
      },
    ];

    const result = adaptSingleChatMessages(input);

    expect(result).toHaveLength(1);
    expect(result[0]!.speaker).toBe('assistant');
  });

  it('should handle empty message list', () => {
    const result = adaptSingleChatMessages([]);

    expect(result).toEqual([]);
  });

  it('should always initialize modified_files and permission_request', () => {
    const input: SingleChatMessageApiItem[] = [
      {
        id: '1',
        role: 'user',
        content: 'Test',
        timestamp: '2024-01-01T00:00:00Z',
        model: 'claude',
      },
    ];

    const result = adaptSingleChatMessages(input);

    expect(result).toHaveLength(1);
    expect(result[0]!.modified_files).toEqual([]);
    expect(result[0]!.permission_request).toBeUndefined();
  });
});
