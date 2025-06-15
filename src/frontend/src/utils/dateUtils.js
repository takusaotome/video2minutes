/**
 * 日時フォーマットユーティリティ
 * タイムゾーンの問題を解決し、統一された日時表示を提供
 */

/**
 * 日時をローカルタイムゾーンでフォーマット
 * @param {string|Date} timestamp - タイムスタンプ
 * @param {Object} options - フォーマットオプション
 * @returns {string} フォーマット済み日時
 */
export function formatDateTime(timestamp, options = {}) {
  if (!timestamp) return ''
  
  try {
    // 文字列の場合は適切にパース
    const date = typeof timestamp === 'string' 
      ? parseTimestamp(timestamp)
      : new Date(timestamp)
    
    if (isNaN(date.getTime())) {
      return ''
    }
    
    // デフォルトオプション
    const defaultOptions = {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      ...options
    }
    
    return date.toLocaleString('ja-JP', defaultOptions)
  } catch (error) {
    console.warn('日時フォーマットエラー:', error, timestamp)
    return ''
  }
}

/**
 * 日付のみをフォーマット
 * @param {string|Date} timestamp - タイムスタンプ
 * @returns {string} フォーマット済み日付
 */
export function formatDate(timestamp) {
  return formatDateTime(timestamp, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

/**
 * 時刻のみをフォーマット
 * @param {string|Date} timestamp - タイムスタンプ
 * @returns {string} フォーマット済み時刻
 */
export function formatTime(timestamp) {
  return formatDateTime(timestamp, {
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * 相対時間を表示（例：「3分前」「1時間前」）
 * @param {string|Date} timestamp - タイムスタンプ
 * @returns {string} 相対時間表示
 */
export function formatRelativeTime(timestamp) {
  if (!timestamp) return ''
  
  try {
    const date = typeof timestamp === 'string' 
      ? parseTimestamp(timestamp)
      : new Date(timestamp)
    
    if (isNaN(date.getTime())) {
      return ''
    }
    
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)
    
    if (diffMinutes < 1) {
      return 'たった今'
    } else if (diffMinutes < 60) {
      return `${diffMinutes}分前`
    } else if (diffHours < 24) {
      return `${diffHours}時間前`
    } else if (diffDays < 7) {
      return `${diffDays}日前`
    } else {
      // 1週間以上前は通常の日付表示
      return formatDate(timestamp)
    }
  } catch (error) {
    console.warn('相対時間フォーマットエラー:', error, timestamp)
    return formatDate(timestamp)
  }
}

/**
 * タイムスタンプ文字列を適切にパース
 * バックエンドからのUTC時刻やISO文字列を正しく処理
 * @param {string} timestampStr - タイムスタンプ文字列
 * @returns {Date} Dateオブジェクト
 */
function parseTimestamp(timestampStr) {
  // ISO形式やUTC文字列の場合
  if (timestampStr.includes('T') || timestampStr.includes('Z')) {
    return new Date(timestampStr)
  }
  
  // その他の形式
  const parsed = Date.parse(timestampStr)
  if (!isNaN(parsed)) {
    return new Date(parsed)
  }
  
  // フォールバック: 文字列をそのままDateコンストラクタに渡す
  return new Date(timestampStr)
}

/**
 * 処理時間を人間が読みやすい形式でフォーマット
 * @param {number} milliseconds - ミリ秒
 * @returns {string} フォーマット済み処理時間
 */
export function formatDuration(milliseconds) {
  if (!milliseconds || milliseconds < 0) return '0秒'
  
  const seconds = Math.floor(milliseconds / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  
  if (hours > 0) {
    const remainingMinutes = minutes % 60
    const remainingSeconds = seconds % 60
    return `${hours}時間${remainingMinutes}分${remainingSeconds}秒`
  } else if (minutes > 0) {
    const remainingSeconds = seconds % 60
    return `${minutes}分${remainingSeconds}秒`
  } else {
    return `${seconds}秒`
  }
}

/**
 * ファイルサイズを人間が読みやすい形式でフォーマット
 * @param {number} bytes - バイト数
 * @returns {string} フォーマット済みファイルサイズ
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * デバッグ用：タイムスタンプの詳細情報を表示
 * @param {string|Date} timestamp - タイムスタンプ
 */
export function debugTimestamp(timestamp) {
  if (process.env.NODE_ENV !== 'development') return
  
  console.group('🕐 タイムスタンプデバッグ')
  console.log('元の値:', timestamp)
  console.log('型:', typeof timestamp)
  
  try {
    const date = typeof timestamp === 'string' 
      ? parseTimestamp(timestamp)
      : new Date(timestamp)
    
    console.log('パース後のDate:', date)
    console.log('有効な日付:', !isNaN(date.getTime()))
    console.log('UTC文字列:', date.toISOString())
    console.log('ローカル文字列:', date.toLocaleString('ja-JP'))
    console.log('タイムゾーン:', Intl.DateTimeFormat().resolvedOptions().timeZone)
    console.log('フォーマット結果:', formatDateTime(timestamp))
  } catch (error) {
    console.error('エラー:', error)
  }
  
  console.groupEnd()
}