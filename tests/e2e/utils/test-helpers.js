const { expect } = require('@playwright/test');
const path = require('path');

/**
 * テストヘルパー関数とユーティリティ
 */
class TestHelpers {
  constructor(page) {
    this.page = page;
  }

  /**
   * ファイルアップロード処理
   * @param {string} fileName - アップロードするファイル名
   * @param {Object} options - オプション設定
   */
  async uploadFile(fileName, options = {}) {
    const {
      waitForUpload = true,
      expectSuccess = true,
      timeout = 30000
    } = options;

    const filePath = path.join(__dirname, '..', 'fixtures', fileName);
    
    // ファイルアップロード
    const fileChooserPromise = this.page.waitForEvent('filechooser');
    await this.page.locator('button.upload-button-primary').click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);

    if (waitForUpload) {
      if (expectSuccess) {
        // アップロード成功トーストを待機
        await this.page.waitForSelector('.p-toast-message-success', { timeout });
        await expect(this.page.getByText('アップロード完了')).toBeVisible();
      } else {
        // エラートーストを待機
        await this.page.waitForSelector('.p-toast-message-error', { timeout });
      }
    }

    return { filePath, fileName };
  }

  /**
   * タスクの完了を待機
   * @param {string} taskId - タスクID
   * @param {number} timeout - タイムアウト（ミリ秒）
   */
  async waitForTaskCompletion(taskId, timeout = 5 * 60 * 1000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const taskStatus = await this.getTaskStatus(taskId);
      
      if (taskStatus === 'completed') {
        return true;
      } else if (taskStatus === 'failed') {
        throw new Error(`Task ${taskId} failed`);
      }
      
      // 2秒待機
      await this.page.waitForTimeout(2000);
    }
    
    throw new Error(`Task ${taskId} did not complete within ${timeout}ms`);
  }

  /**
   * タスクステータスを取得
   * @param {string} taskId - タスクID
   */
  async getTaskStatus(taskId) {
    const taskRow = this.page.locator(`tr.task-row-${taskId}`);
    const statusBadge = taskRow.locator('[data-testid="status-badge"]');
    const statusText = await statusBadge.textContent();
    return statusText.toLowerCase();
  }

  /**
   * 進捗の更新を監視
   * @param {string} taskId - タスクID
   * @param {number} minProgress - 最小進捗パーセンテージ
   */
  async waitForProgress(taskId, minProgress = 10) {
    const progressBar = this.page.locator(`tr.task-row-${taskId} [data-testid="progress-bar-${taskId}"]`);
    
    await expect(progressBar).toBeVisible();
    
    // 進捗が指定値以上になるまで待機
    await this.page.waitForFunction(
      ({ taskId, minProgress }) => {
        const progressElement = document.querySelector(`[data-testid="progress-bar-${taskId}"]`);
        if (!progressElement) return false;
        
        const progressValue = parseInt(progressElement.getAttribute('aria-valuenow')) || 0;
        return progressValue >= minProgress;
      },
      { taskId, minProgress },
      { timeout: 60000 }
    );
  }

  /**
   * WebSocket接続を監視
   */
  async monitorWebSocketConnection() {
    const wsMessages = [];
    
    this.page.on('websocket', ws => {
      console.log(`WebSocket opened: ${ws.url()}`);
      
      ws.on('framesent', event => {
        console.log(`WebSocket sent: ${event.payload}`);
      });
      
      ws.on('framereceived', event => {
        const message = JSON.parse(event.payload);
        wsMessages.push(message);
        console.log(`WebSocket received:`, message);
      });
      
      ws.on('close', () => {
        console.log('WebSocket closed');
      });
    });
    
    return wsMessages;
  }

  /**
   * トースト通知をチェック
   * @param {string} expectedMessage - 期待するメッセージ
   * @param {string} type - 通知タイプ ('success', 'error', 'info', 'warn')
   */
  async checkToastNotification(expectedMessage, type = 'success') {
    const toastSelector = `.p-toast-message-${type}`;
    await this.page.waitForSelector(toastSelector, { timeout: 10000 });
    
    const toastText = await this.page.locator(toastSelector).textContent();
    expect(toastText).toContain(expectedMessage);
    
    // トーストが自動で消えるまで待機
    await this.page.waitForSelector(toastSelector, { state: 'hidden', timeout: 10000 });
  }

  /**
   * レスポンシブ表示をテスト
   * @param {Object} viewport - ビューポート設定
   */
  async testResponsiveLayout(viewport) {
    await this.page.setViewportSize(viewport);
    await this.page.waitForTimeout(1000); // レイアウト調整を待機
    
    // 主要要素の表示確認
    await expect(this.page.locator('header.app-header')).toBeVisible();
    await expect(this.page.locator('button.upload-button-primary')).toBeVisible();
    await expect(this.page.locator('div.task-list')).toBeVisible();
  }

  /**
   * APIレスポンスを監視
   * @param {string} apiPath - 監視するAPIパス
   */
  async interceptApiCall(apiPath) {
    const responses = [];
    
    await this.page.route(`**/api/v1${apiPath}`, route => {
      route.continue();
    });
    
    this.page.on('response', response => {
      if (response.url().includes(`/api/v1${apiPath}`)) {
        responses.push({
          status: response.status(),
          url: response.url(),
          headers: response.headers()
        });
      }
    });
    
    return responses;
  }

  /**
   * ダウンロードファイルをチェック
   * @param {string} expectedFileName - 期待するファイル名
   */
  async checkDownloadedFile(expectedFileName) {
    const downloadPromise = this.page.waitForEvent('download');
    
    // ダウンロードボタンをクリック
    await this.page.locator('[data-testid="download-button"]').click();
    
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(expectedFileName);
    
    // ファイルを保存
    const downloadPath = path.join(__dirname, '..', '..', 'test-downloads', expectedFileName);
    await download.saveAs(downloadPath);
    
    return downloadPath;
  }

  /**
   * エラーメッセージを確認
   * @param {string} expectedError - 期待するエラーメッセージ
   */
  async checkErrorMessage(expectedError) {
    const errorDialog = this.page.locator('[data-testid="error-dialog"]');
    await expect(errorDialog).toBeVisible();
    
    const errorText = await errorDialog.locator('.error-message').textContent();
    expect(errorText).toContain(expectedError);
    
    // エラーダイアログを閉じる
    await this.page.locator('[data-testid="error-dialog-close"]').click();
    await expect(errorDialog).not.toBeVisible();
  }

  /**
   * タスク詳細モーダルを開く
   * @param {string} taskId - タスクID
   */
  async openTaskDetailModal(taskId) {
    const taskRow = this.page.locator(`tr.task-row-${taskId}`);
    await taskRow.click();

    const modal = this.page.locator('[data-testid="task-detail-modal"]');
    await expect(modal).toBeVisible();
    
    return modal;
  }

  /**
   * 処理ステップの確認
   * @param {Array} expectedSteps - 期待する処理ステップ
   */
  async checkProcessingSteps(expectedSteps) {
    const timeline = this.page.locator('[data-testid="processing-timeline"]');
    await expect(timeline).toBeVisible();
    
    for (const step of expectedSteps) {
      const stepElement = this.page.locator(`[data-testid="step-${step.name}"]`);
      await expect(stepElement).toBeVisible();
      
      if (step.status) {
        const statusElement = stepElement.locator('[data-testid="step-status"]');
        await expect(statusElement).toHaveAttribute('data-status', step.status);
      }
    }
  }

  /**
   * 複数ファイルの同時アップロード
   * @param {Array} fileNames - アップロードするファイル名の配列
   */
  async uploadMultipleFiles(fileNames) {
    const filePaths = fileNames.map(name => 
      path.join(__dirname, '..', 'fixtures', name)
    );
    
    const fileChooserPromise = this.page.waitForEvent('filechooser');
    await this.page.locator('button.upload-button-primary').click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePaths);
    
    // 各ファイルのアップロード完了を待機
    for (const fileName of fileNames) {
      await this.page.waitForSelector(`[data-testid*="${fileName}"]`, { timeout: 30000 });
    }
    
    return filePaths;
  }

  /**
   * パフォーマンス指標を測定
   */
  async measurePerformance() {
    const performanceMetrics = await this.page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0];
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0,
        firstContentfulPaint: performance.getEntriesByType('paint')[1]?.startTime || 0
      };
    });
    
    return performanceMetrics;
  }
}

module.exports = { TestHelpers };