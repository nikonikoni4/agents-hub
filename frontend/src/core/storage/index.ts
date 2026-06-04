/**
 * IndexedDB Storage
 *
 * 职责：
 * - 持久化存储 last_view_at 记录
 * - 提供读取、写入、批量写入 API
 *
 * 架构约束：
 * - 单例模式
 * - 异步 API
 * - 错误处理
 */

const DB_NAME = 'agents-hub-storage';
const STORE_NAME = 'session-views';
const DB_VERSION = 1;

/**
 * Storage 类（单例）
 */
export class Storage {
  private db: IDBDatabase | null = null;
  private initPromise: Promise<void> | null = null;

  /**
   * 初始化 IndexedDB
   */
  async init(): Promise<void> {
    // 防止重复初始化
    if (this.initPromise) {
      return this.initPromise;
    }

    this.initPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        reject(new Error('Failed to open IndexedDB'));
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // 创建 object store（如果不存在）
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'group_chat_id' });
        }
      };
    });

    return this.initPromise;
  }

  /**
   * 读取所有 last_view_at 记录
   *
   * @returns { group_chat_id: last_view_at }
   */
  async getLastViewRecords(): Promise<Record<string, string>> {
    await this.ensureInitialized();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.getAll();

      request.onsuccess = () => {
        const records = request.result as Array<{ group_chat_id: string; last_view_at: string }>;
        const result: Record<string, string> = {};

        records.forEach((record) => {
          result[record.group_chat_id] = record.last_view_at;
        });

        resolve(result);
      };

      request.onerror = () => {
        reject(new Error('Failed to read last_view records'));
      };
    });
  }

  /**
   * 写入单条 last_view_at 记录
   *
   * @param groupChatId - 群聊 ID
   * @param timestamp - ISO 8601 时间戳
   */
  async setLastView(groupChatId: string, timestamp: string): Promise<void> {
    await this.ensureInitialized();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.put({
        group_chat_id: groupChatId,
        last_view_at: timestamp,
      });

      request.onsuccess = () => resolve();
      request.onerror = () => reject(new Error('Failed to write last_view record'));
    });
  }

  /**
   * 批量写入 last_view_at 记录
   *
   * @param records - 记录数组
   */
  async batchSetLastView(records: Array<{ id: string; timestamp: string }>): Promise<void> {
    await this.ensureInitialized();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(STORE_NAME, 'readwrite');
      const store = transaction.objectStore(STORE_NAME);

      records.forEach((record) => {
        store.put({
          group_chat_id: record.id,
          last_view_at: record.timestamp,
        });
      });

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(new Error('Failed to batch write last_view records'));
    });
  }

  /**
   * 确保已初始化
   */
  private async ensureInitialized(): Promise<void> {
    if (!this.db) {
      await this.init();
    }
  }
}

// 导出单例
export const storage = new Storage();
