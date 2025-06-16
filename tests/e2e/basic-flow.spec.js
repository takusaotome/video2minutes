const { test, expect } = require('@playwright/test');
const { TestHelpers } = require('./utils/test-helpers');

test.describe('基本的なファイルアップロード・処理フロー', () => {
  let helpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);
    await page.goto('/');
    
    // ダッシュボードの基本要素が表示されることを確認
    await expect(page.locator('header.app-header')).toBeVisible();
    await expect(page.locator('button.upload-button-primary')).toBeVisible();
    await expect(page.locator('div.task-list')).toBeVisible();
  });

  test('シナリオ1: 単一動画ファイルの正常処理 @basic', async ({ page }) => {
    // WebSocket監視を開始
    const wsMessages = await helpers.monitorWebSocketConnection();
    
    // Step 1-3: ファイルアップロード
    console.log('Step 1-3: ファイルアップロード開始');
    await helpers.uploadFile('test-video-small.mp4');
    
    // Step 4: タスク一覧に新しいタスクが追加されることを確認
    console.log('Step 4: タスク追加確認');
    const taskRows = page.locator('tr[class*="task-row-"]');
    await expect(taskRows.first()).toBeVisible();
    
    // タスクIDを取得
    const firstTaskRow = taskRows.first();
    const classAttr = await firstTaskRow.getAttribute('class');
    const taskId = classAttr.match(/task-row-([\w-]+)/)[1];
    
    // Step 5: タスクステータスが「processing」に変更されることを確認
    console.log('Step 5: 処理開始確認');
    await page.waitForTimeout(5000); // 処理開始を待機
    const status = await helpers.getTaskStatus(taskId);
    expect(['pending', 'processing'].includes(status)).toBeTruthy();
    
    // Step 6: 進捗バーの更新を確認
    console.log('Step 6: 進捗更新確認');
    await helpers.waitForProgress(taskId, 10);
    
    // Step 7: 処理ステップの順次更新を確認
    console.log('Step 7: 処理ステップ確認');
    const modal = await helpers.openTaskDetailModal(taskId);
    
    await helpers.checkProcessingSteps([
      { name: 'upload', status: 'completed' },
      { name: 'audio_extraction', status: 'processing' },
      { name: 'transcription', status: 'pending' },
      { name: 'minutes_generation', status: 'pending' }
    ]);
    
    // モーダルを閉じる
    await page.locator('[data-testid="modal-close"]').click();
    await expect(modal).not.toBeVisible();
    
    // Step 8-9: 処理完了まで待機
    console.log('Step 8-9: 処理完了待機（最大5分）');
    await helpers.waitForTaskCompletion(taskId, 5 * 60 * 1000);
    
    // 完了トーストの確認
    await helpers.checkToastNotification('議事録が完成しました', 'success');
    
    // Step 10-11: 議事録画面への遷移
    console.log('Step 10-11: 議事録表示確認');
    const viewButton = page.locator(`[data-testid="view-minutes-${taskId}"]`);
    await expect(viewButton).toBeVisible();
    await viewButton.click();
    
    // 議事録画面の表示確認
    await expect(page.locator('[data-testid="minutes-content"]')).toBeVisible();
    await expect(page.locator('.transcription-content')).toBeVisible();
    
    // Step 12: ダウンロード機能の確認
    console.log('Step 12: ダウンロード機能確認');
    const downloadPath = await helpers.checkDownloadedFile('minutes.md');
    console.log(`Downloaded file: ${downloadPath}`);
    
    // WebSocket通信の確認
    expect(wsMessages.length).toBeGreaterThan(0);
    console.log(`WebSocket messages received: ${wsMessages.length}`);
  });

  test('シナリオ8: レスポンシブデザイン @basic @responsive', async ({ page }) => {
    const viewports = [
      { width: 1920, height: 1080 }, // Desktop
      { width: 768, height: 1024 },  // Tablet
      { width: 375, height: 667 }    // Mobile
    ];

    for (const viewport of viewports) {
      console.log(`Testing viewport: ${viewport.width}x${viewport.height}`);
      await helpers.testResponsiveLayout(viewport);
      
      // ファイルアップロード機能が動作することを確認
      await expect(page.locator('button.upload-button-primary')).toBeVisible();
      
      // タスクリストが適切に表示されることを確認
      await expect(page.locator('div.task-list')).toBeVisible();
    }
  });

  test('パフォーマンス測定', async ({ page }) => {
    const metrics = await helpers.measurePerformance();
    
    console.log('Performance Metrics:', metrics);
    
    // パフォーマンス基準値のチェック
    expect(metrics.domContentLoaded).toBeLessThan(3000); // 3秒以内
    expect(metrics.firstContentfulPaint).toBeLessThan(2000); // 2秒以内
  });

  test('WebSocket接続テスト @basic', async ({ page }) => {
    // WebSocket監視開始
    const wsMessages = await helpers.monitorWebSocketConnection();
    
    // ファイルアップロードでWebSocket接続をトリガー
    await helpers.uploadFile('test-video-small.mp4');
    
    // WebSocket接続の確立を確認
    await page.waitForTimeout(5000);
    
    // WebSocketメッセージの受信を確認
    expect(wsMessages.length).toBeGreaterThan(0);
    
    // 進捗更新メッセージの受信を確認
    const progressMessages = wsMessages.filter(msg => msg.type === 'progress_update');
    expect(progressMessages.length).toBeGreaterThan(0);
  });
});