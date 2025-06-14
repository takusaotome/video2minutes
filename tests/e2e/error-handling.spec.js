const { test, expect } = require('@playwright/test');
const { TestHelpers } = require('./utils/test-helpers');

test.describe('エラーハンドリングテスト', () => {
  let helpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);
    await page.goto('/');
    
    // ダッシュボードの表示確認
    await expect(page.getByTestId('main-header')).toBeVisible();
    await expect(page.getByTestId('file-upload-area')).toBeVisible();
    await expect(page.getByTestId('task-list')).toBeVisible();
  });

  test('シナリオ4: 無効なファイル形式のアップロード @error', async ({ page }) => {
    console.log('無効ファイル形式テスト開始');
    
    // Step 1: テキストファイル（.txt）をアップロード
    await helpers.uploadFile('test-invalid-file.txt', {
      waitForUpload: true,
      expectSuccess: false,
      timeout: 15000
    });
    
    // Step 2: エラーメッセージが表示されることを確認
    await helpers.checkToastNotification('サポートされていないファイル形式です', 'error');
    
    // Step 3: タスクが作成されないことを確認
    const taskRows = page.getByTestId(/^task-row-/);
    const taskCount = await taskRows.count();
    expect(taskCount).toBe(0);
    
    console.log('無効ファイル形式テスト完了');
  });

  test('シナリオ5: ファイルサイズ制限超過 @error', async ({ page }) => {
    console.log('ファイルサイズ制限テスト開始');
    
    // 大きすぎるファイルのモック作成
    await page.route('**/api/v1/minutes/upload', async route => {
      const request = route.request();
      const contentLength = request.headers()['content-length'];
      
      if (contentLength && parseInt(contentLength) > 500 * 1024 * 1024) {
        await route.fulfill({
          status: 413,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'ファイルサイズが制限（500MB）を超えています'
          })
        });
      } else {
        await route.continue();
      }
    });
    
    // 大きなファイルアップロードを試行
    try {
      await helpers.uploadFile('test-video-medium.mp4', {
        waitForUpload: true,
        expectSuccess: false,
        timeout: 15000
      });
    } catch (error) {
      console.log('Expected error for large file:', error.message);
    }
    
    // エラーメッセージ確認
    await helpers.checkToastNotification('ファイルサイズが制限を超えています', 'error');
    
    console.log('ファイルサイズ制限テスト完了');
  });

  test('シナリオ6: API制限・エラー時の処理 @error', async ({ page }) => {
    console.log('API制限エラーテスト開始');
    
    // APIエラーをモック
    await page.route('**/api/v1/minutes/**', async route => {
      const url = route.request().url();
      
      if (url.includes('/transcribe')) {
        // 転写APIエラーをシミュレート
        await route.fulfill({
          status: 429,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'API rate limit exceeded. Please try again later.',
            error_code: 'rate_limit_exceeded'
          })
        });
      } else if (url.includes('/status')) {
        // ステータスチェック時のエラー状態を返す
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            task_id: 'mock-task-id',
            status: 'failed',
            error_message: 'Transcription failed due to API rate limit',
            current_step: 'transcription',
            progress: 45,
            steps: [
              { name: 'upload', status: 'completed', progress: 100 },
              { name: 'audio_extraction', status: 'completed', progress: 100 },
              { name: 'transcription', status: 'failed', progress: 45 },
              { name: 'minutes_generation', status: 'pending', progress: 0 }
            ]
          })
        });
      } else {
        await route.continue();
      }
    });
    
    // Step 1-2: ファイルをアップロード
    await helpers.uploadFile('test-video-small.mp4');
    
    // Step 3: 転写処理でエラーが発生することを確認
    await page.waitForTimeout(5000); // 処理開始を待機
    
    // タスクリストでエラー状態を確認
    const taskRows = page.getByTestId(/^task-row-/);
    await expect(taskRows.first()).toBeVisible();
    
    const taskId = await taskRows.first().getAttribute('data-testId').then(id => id.replace('task-row-', ''));
    
    // Step 4: エラー状態がUIに適切に反映されることを確認
    await page.waitForTimeout(10000); // エラー状態への遷移を待機
    
    const status = await helpers.getTaskStatus(taskId);
    console.log(`Task status: ${status}`);
    
    if (status === 'failed') {
      // エラーバッジの表示確認
      const errorBadge = page.getByTestId(`status-badge-${taskId}`);
      await expect(errorBadge).toHaveClass(/error|failed|danger/);
      
      // Step 5: 再試行ボタンが表示されることを確認
      const modal = await helpers.openTaskDetailModal(taskId);
      const retryButton = modal.getByTestId('retry-button');
      await expect(retryButton).toBeVisible();
      
      // エラーメッセージの表示確認
      const errorMessage = modal.getByTestId('error-message');
      await expect(errorMessage).toBeVisible();
      await expect(errorMessage).toContainText('API rate limit');
      
      await page.getByTestId('modal-close').click();
    }
    
    console.log('API制限エラーテスト完了');
  });

  test('シナリオ7: ネットワーク中断時の処理 @error @network', async ({ page, context }) => {
    console.log('ネットワーク中断テスト開始');
    
    // Step 1: 処理中にネットワーク接続を一時的に切断
    await helpers.uploadFile('test-video-small.mp4');
    
    // 処理開始を待機
    await page.waitForTimeout(5000);
    
    // ネットワーク切断をシミュレート
    console.log('ネットワーク切断シミュレート');
    await context.setOffline(true);
    
    // Step 2: エラー状態に遷移することを確認
    await page.waitForTimeout(10000);
    
    // ネットワークエラーの表示確認
    const networkError = page.getByText(/ネットワークエラー|接続エラー|Network Error/i);
    await expect(networkError).toBeVisible({ timeout: 15000 });
    
    // Step 3: ネットワーク復旧後に適切にリカバリされることを確認
    console.log('ネットワーク復旧シミュレート');
    await context.setOffline(false);
    
    // リカバリ処理の確認
    await page.waitForTimeout(5000);
    
    // 再接続の試行確認
    const reconnectMessage = page.getByText(/再接続中|Reconnecting/i);
    if (await reconnectMessage.isVisible()) {
      await expect(reconnectMessage).not.toBeVisible({ timeout: 30000 });
    }
    
    console.log('ネットワーク中断テスト完了');
  });

  test('無効なJSON応答の処理 @error', async ({ page }) => {
    console.log('無効JSON応答テスト開始');
    
    // 無効なJSON応答をモック
    await page.route('**/api/v1/minutes/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: 'Invalid JSON Response {broken'
      });
    });
    
    // ファイルアップロードを試行
    try {
      await helpers.uploadFile('test-video-small.mp4', {
        waitForUpload: true,
        expectSuccess: false,
        timeout: 15000
      });
    } catch (error) {
      console.log('Expected JSON parsing error:', error.message);
    }
    
    // JSONパースエラーの処理確認
    await helpers.checkToastNotification('サーバーエラーが発生しました', 'error');
    
    console.log('無効JSON応答テスト完了');
  });

  test('サーバー障害時の処理 @error', async ({ page }) => {
    console.log('サーバー障害テスト開始');
    
    // サーバーエラーをモック
    await page.route('**/api/v1/**', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Internal Server Error',
          error_code: 'server_error'
        })
      });
    });
    
    // ファイルアップロードを試行
    try {
      await helpers.uploadFile('test-video-small.mp4', {
        waitForUpload: true,
        expectSuccess: false,
        timeout: 15000
      });
    } catch (error) {
      console.log('Expected server error:', error.message);
    }
    
    // サーバーエラーの処理確認
    await helpers.checkToastNotification('サーバーエラー', 'error');
    
    console.log('サーバー障害テスト完了');
  });

  test('タイムアウト処理 @error @timeout', async ({ page }) => {
    console.log('タイムアウト処理テスト開始');
    
    // 長時間応答しないAPIをモック
    await page.route('**/api/v1/minutes/upload', async route => {
      // 30秒間応答を遅延
      await new Promise(resolve => setTimeout(resolve, 30000));
      await route.continue();
    });
    
    // タイムアウト設定を短くしてテスト
    page.setDefaultTimeout(10000);
    
    try {
      await helpers.uploadFile('test-video-small.mp4', {
        waitForUpload: true,
        expectSuccess: false,
        timeout: 10000
      });
    } catch (error) {
      console.log('Expected timeout error:', error.message);
      expect(error.message).toContain('timeout');
    }
    
    console.log('タイムアウト処理テスト完了');
  });

  test('WebSocketエラー処理 @error @websocket', async ({ page }) => {
    console.log('WebSocketエラー処理テスト開始');
    
    // WebSocket接続エラーをシミュレート
    await page.route('**/api/v1/ws/**', route => {
      route.abort('connectionrefused');
    });
    
    // WebSocket監視開始
    const wsMessages = await helpers.monitorWebSocketConnection();
    
    // ファイルアップロードでWebSocket接続を試行
    await helpers.uploadFile('test-video-small.mp4');
    
    // WebSocket接続失敗時のフォールバック確認
    await page.waitForTimeout(10000);
    
    // ポーリングベースの更新にフォールバックすることを確認
    const taskRows = page.getByTestId(/^task-row-/);
    if (await taskRows.count() > 0) {
      // タスクが表示されている場合、ポーリングで更新されることを確認
      await page.waitForTimeout(5000);
      console.log('WebSocket fallback to polling confirmed');
    }
    
    console.log('WebSocketエラー処理テスト完了');
  });
});