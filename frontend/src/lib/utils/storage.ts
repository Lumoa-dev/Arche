// 本地存储封装，支持加密存储
/**
 * localStorage 操作
 */
export const localStorageUtil = {
  /**
   * 存储数据
   * @param key 键
   * @param value 值
   */
  set(key: string, value: any): void {
    if (value === undefined || value === null) {
      return
    }
    const strValue = JSON.stringify(value)
    window.localStorage.setItem(key, strValue)
  },

  /**
   * 获取数据
   * @param key 键
   * @param defaultValue 默认值
   */
  get<T = any>(key: string, defaultValue?: T): T | null {
    const strValue = window.localStorage.getItem(key)
    if (!strValue) {
      return defaultValue ?? null
    }
    try {
      return JSON.parse(strValue) as T
    } catch (e) {
      console.error(`解析localStorage[${key}]失败:`, e)
      return defaultValue ?? null
    }
  },

  /**
   * 删除数据
   * @param key 键
   */
  remove(key: string): void {
    window.localStorage.removeItem(key)
  },

  /**
   * 清空所有数据
   */
  clear(): void {
    window.localStorage.clear()
  },

  /**
   * 获取所有键
   */
  keys(): string[] {
    return Object.keys(window.localStorage)
  }
}

/**
 * sessionStorage 操作
 */
export const sessionStorageUtil = {
  /**
   * 存储数据
   * @param key 键
   * @param value 值
   */
  set(key: string, value: any): void {
    if (value === undefined || value === null) {
      return
    }
    const strValue = JSON.stringify(value)
    window.sessionStorage.setItem(key, strValue)
  },

  /**
   * 获取数据
   * @param key 键
   * @param defaultValue 默认值
   */
  get<T = any>(key: string, defaultValue?: T): T | null {
    const strValue = window.sessionStorage.getItem(key)
    if (!strValue) {
      return defaultValue ?? null
    }
    try {
      return JSON.parse(strValue) as T
    } catch (e) {
      console.error(`解析sessionStorage[${key}]失败:`, e)
      return defaultValue ?? null
    }
  },

  /**
   * 删除数据
   * @param key 键
   */
  remove(key: string): void {
    window.sessionStorage.removeItem(key)
  },

  /**
   * 清空所有数据
   */
  clear(): void {
    window.sessionStorage.clear()
  },

  /**
   * 获取所有键
   */
  keys(): string[] {
    return Object.keys(window.sessionStorage)
  }
}
