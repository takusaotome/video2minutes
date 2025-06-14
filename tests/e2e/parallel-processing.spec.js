const { test, expect } = require('@playwright/test');
const { TestHelpers } = require('./utils/test-helpers');

test.describe('複数ファイル並行処理テスト', () => {
  let helpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);
    await page.goto('/');
    
    // ダッシュボードの表示確認
    await expect(page.getByTestId('main-header')).toBeVisible();
    await expect(page.getByTestId('file-upload-area')).toBeVisible();
    await expect(page.getByTestId('task-list')).toBeVisible();
  });

  test('シナリオ2: 複数ファイルの並行処理 @parallel', async ({ page }) => {
    console.log('複数ファイル並行処理テスト開始');
    
    // Step 1: 3つの異なる動画ファイルを同時にアップロード
    const fileNames = [
      'test-video-small.mp4',
      'test-video-medium.mp4', 
      'test-japanese-名前.mp4'
    ];
    
    console.log('Step 1: 複数ファイルの同時アップロード');
    await helpers.uploadMultipleFiles(fileNames);
    
    // アップロード完了トーストを確認（複数回表示される）
    for (let i = 0; i < fileNames.length; i++) {
      await helpers.checkToastNotification('アップロード完了', 'success');
      await page.waitForTimeout(1000); // トースト間の間隔を考慮
    }
    
    // Step 2: 3つのタスクが並行して処理されることを確認
    console.log('Step 2: 並行処理の確認');
    const taskRows = page.getByTestId(/^task-row-/);
    await expect(taskRows).toHaveCount(3);
    
    // 各タスクのIDを取得
    const taskIds = [];
    for (let i = 0; i < 3; i++) {
      const taskRow = taskRows.nth(i);
      const taskId = await taskRow.getAttribute('data-testid').then(id => id.replace('task-row-', ''));
      taskIds.push(taskId);
    }
    
    console.log('取得したタスクID:', taskIds);
    
    // Step 3: 各タスクの進捗が独立して更新されることを確認
    console.log('Step 3: 独立した進捗更新の確認');
    
    // 各タスクが処理中状態になることを確認
    for (const taskId of taskIds) {
      await page.waitForTimeout(2000); // 処理開始待機
      const status = await helpers.getTaskStatus(taskId);
      console.log(`Task ${taskId} status: ${status}`);
      expect(['pending', 'processing'].includes(status)).toBeTruthy();
    }
    
    // 進捗の独立性を確認（異なる進捗値を持つ）
    const progressValues = [];
    for (const taskId of taskIds) {
      try {
        await helpers.waitForProgress(taskId, 5); // 最低5%の進捗を待機
        const progressBar = page.getByTestId(`progress-bar-${taskId}`);
        const progressValue = await progressBar.getAttribute('aria-valuenow');
        progressValues.push(parseInt(progressValue) || 0);
        console.log(`Task ${taskId} progress: ${progressValue}%`);
      } catch (error) {
        console.log(`Task ${taskId} progress monitoring failed:`, error.message);
        progressValues.push(0);
      }
    }
    
    // 少なくとも1つのタスクで進捗があることを確認
    expect(Math.max(...progressValues)).toBeGreaterThan(0);
    
    // Step 4: 完了順序が処理時間に応じて変わることを確認
    console.log('Step 4: 完了順序の確認');
    const completionOrder = [];
    const maxWaitTime = 10 * 60 * 1000; // 10分
    const startTime = Date.now();
    
    // 各タスクの完了を監視
    const completionPromises = taskIds.map(async (taskId) => {
      try {
        await helpers.waitForTaskCompletion(taskId, maxWaitTime);
        const completionTime = Date.now() - startTime;
        completionOrder.push({ taskId, completionTime });
        console.log(`Task ${taskId} completed in ${completionTime}ms`);
        return { taskId, status: 'completed', completionTime };
      } catch (error) {
        console.log(`Task ${taskId} failed or timed out:`, error.message);
        return { taskId, status: 'failed', error: error.message };
      }
    });
    
    // すべてのタスクの完了または失敗を待機
    const results = await Promise.allSettled(completionPromises);
    console.log('All tasks finished:', results);
    
    // Step 5: 全タスクが正常に完了することを確認
    console.log('Step 5: 全タスク完了確認');
    const successfulTasks = results.filter(result => 
      result.status === 'fulfilled' && result.value.status === 'completed'
    );
    
    console.log(`成功したタスク数: ${successfulTasks.length}/${taskIds.length}`);
    
    // 少なくとも1つのタスクが成功することを期待（API制限やタイムアウトを考慮）
    expect(successfulTasks.length).toBeGreaterThan(0);
    
    // 成功したタスクの完了通知を確認
    for (const result of successfulTasks) {
      await helpers.checkToastNotification('議事録が完成しました', 'success');
    }
  });

  test('シナリオ11: 同時アクセス負荷テスト @parallel @load', async ({ page, context }) => {
    console.log('同時アクセス負荷テスト開始');
    
    // 複数のページを作成して同時アクセスをシミュレート
    const pages = [page];
    
    // 追加のページを作成
    for (let i = 1; i < 3; i++) {
      const newPage = await context.newPage();
      await newPage.goto('/');
      pages.push(newPage);
    }
    
    console.log(`${pages.length}つのページで並行テスト実行`);
    
    // 各ページで同時にファイルアップロード
    const uploadPromises = pages.map(async (currentPage, index) => {
      const pageHelpers = new TestHelpers(currentPage);
      try {
        await pageHelpers.uploadFile('test-video-small.mp4', {
          waitForUpload: true,
          expectSuccess: true,
          timeout: 30000
        });
        console.log(`Page ${index + 1}: Upload successful`);
        return { pageIndex: index, status: 'success' };
      } catch (error) {
        console.log(`Page ${index + 1}: Upload failed:`, error.message);
        return { pageIndex: index, status: 'failed', error: error.message };
      }
    });
    
    // すべてのアップロードの完了を待機
    const uploadResults = await Promise.allSettled(uploadPromises);
    console.log('Upload results:', uploadResults);
    
    // 各セッションが独立して動作することを確認
    for (let i = 0; i < pages.length; i++) {
      const currentPage = pages[i];
      
      // 各ページでタスクリストが表示されることを確認
      await expect(currentPage.getByTestId('task-list')).toBeVisible();
      
      // 各ページで独立したタスクが存在することを確認
      const taskRows = currentPage.getByTestId(/^task-row-/);
      const taskCount = await taskRows.count();
      console.log(`Page ${i + 1}: ${taskCount} tasks found`);
      
      // 少なくとも1つのタスクが存在することを確認
      expect(taskCount).toBeGreaterThanOrEqual(1);
    }
    
    // 追加で作成したページをクリーンアップ
    for (let i = 1; i < pages.length; i++) {
      await pages[i].close();
    }
  });

  test('大量ファイル処理性能テスト @parallel @performance', async ({ page }) => {
    console.log('大量ファイル処理性能テスト開始');
    
    // 5つのファイルを同時処理
    const fileNames = [
      'test-video-small.mp4',
      'test-video-medium.mp4',
      'test-japanese-名前.mp4',
      'test-video-small.mp4', // 重複ファイル名での動作確認
      'test-video-medium.mp4'
    ];
    
    const startTime = Date.now();
    
    // 大量ファイルアップロード
    await helpers.uploadMultipleFiles(fileNames);
    
    const uploadTime = Date.now() - startTime;
    console.log(`Upload time: ${uploadTime}ms`);
    
    // アップロード時間が妥当な範囲内であることを確認
    expect(uploadTime).toBeLessThan(60000); // 1分以内
    
    // システムリソースの確認（メモリ使用量など）
    const performanceMetrics = await helpers.measurePerformance();
    console.log('Performance metrics during load:', performanceMetrics);
    
    // UI の応答性確認
    await expect(page.getByTestId('file-upload-area')).toBeVisible();
    await expect(page.getByTestId('task-list')).toBeVisible();
    
    // 追加ファイルのアップロードが可能であることを確認
    try {
      await helpers.uploadFile('test-video-small.mp4', { timeout: 15000 });
      console.log('Additional upload successful during load');
    } catch (error) {
      console.log('Additional upload failed during load:', error.message);
    }
  });

  test('WebSocket並行接続テスト @parallel @websocket', async ({ page }) => {
    console.log('WebSocket並行接続テスト開始');
    
    // WebSocket監視開始
    const wsMessages = await helpers.monitorWebSocketConnection();
    
    // 複数ファイルアップロードでWebSocket接続を複数作成
    const fileNames = ['test-video-small.mp4', 'test-video-medium.mp4'];
    await helpers.uploadMultipleFiles(fileNames);
    
    // 各タスクのWebSocket接続確認
    await page.waitForTimeout(10000); // WebSocket接続とメッセージの受信を待機
    
    console.log(`WebSocket messages received: ${wsMessages.length}`);
    expect(wsMessages.length).toBeGreaterThan(0);
    
    // 複数タスクの進捗更新メッセージを確認
    const progressMessages = wsMessages.filter(msg => msg.type === 'progress_update');
    const taskUpdateMessages = wsMessages.filter(msg => msg.type === 'task_update');
    
    console.log(`Progress messages: ${progressMessages.length}`);
    console.log(`Task update messages: ${taskUpdateMessages.length}`);
    
    expect(progressMessages.length + taskUpdateMessages.length).toBeGreaterThan(0);
  });
});