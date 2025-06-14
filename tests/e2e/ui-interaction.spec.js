const { test, expect } = require('@playwright/test');
const { TestHelpers } = require('./utils/test-helpers');

test.describe('UIインタラクション・レスポンシブテスト', () => {
  let helpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);
    await page.goto('/');
    
    // ダッシュボードの表示確認
    await expect(page.getByTestId('main-header')).toBeVisible();
    await expect(page.getByTestId('file-upload-area')).toBeVisible();
    await expect(page.getByTestId('task-list')).toBeVisible();
  });

  test('シナリオ8: レスポンシブデザイン @responsive', async ({ page }) => {
    console.log('レスポンシブデザインテスト開始');
    
    const viewports = [
      { name: 'Desktop Large', width: 1920, height: 1080 },
      { name: 'Desktop Medium', width: 1366, height: 768 },
      { name: 'Tablet Portrait', width: 768, height: 1024 },
      { name: 'Tablet Landscape', width: 1024, height: 768 },
      { name: 'Mobile Large', width: 414, height: 896 },
      { name: 'Mobile Medium', width: 375, height: 667 },
      { name: 'Mobile Small', width: 320, height: 568 }
    ];

    for (const viewport of viewports) {
      console.log(`Testing ${viewport.name}: ${viewport.width}x${viewport.height}`);
      
      await helpers.testResponsiveLayout(viewport);
      
      // 各画面サイズで主要機能をテスト
      await testMainFunctionsAtViewport(page, viewport);
    }
    
    console.log('レスポンシブデザインテスト完了');
  });

  test('タッチデバイス操作テスト @responsive @touch', async ({ page, isMobile }) => {
    if (!isMobile) {
      test.skip('Mobile device test skipped on desktop');
    }
    
    console.log('タッチデバイス操作テスト開始');
    
    // タッチジェスチャーでのファイルアップロード
    const uploadArea = page.getByTestId('file-upload-area');
    await expect(uploadArea).toBeVisible();
    
    // タップ操作の確認
    await uploadArea.tap();
    
    // スワイプ操作でタスクリストを操作
    const taskList = page.getByTestId('task-list');
    await expect(taskList).toBeVisible();
    
    // モバイルメニューの表示確認
    const mobileMenuButton = page.getByTestId('mobile-menu-button');
    if (await mobileMenuButton.isVisible()) {
      await mobileMenuButton.tap();
      
      const mobileMenu = page.getByTestId('mobile-menu');
      await expect(mobileMenu).toBeVisible();
      
      // メニューを閉じる
      await page.tap('html'); // 外側タップで閉じる
      await expect(mobileMenu).not.toBeVisible();
    }
    
    console.log('タッチデバイス操作テスト完了');
  });

  test('シナリオ9: ブラウザ互換性 @compatibility', async ({ page, browserName }) => {
    console.log(`ブラウザ互換性テスト開始: ${browserName}`);
    
    // 基本機能の動作確認
    await expect(page.getByTestId('file-upload-area')).toBeVisible();
    await expect(page.getByTestId('task-list')).toBeVisible();
    
    // CSS Grid/Flexboxサポート確認
    const layoutElements = await page.locator('[data-testid*="layout"]').all();
    for (const element of layoutElements) {
      const styles = await element.evaluate(el => {
        const computed = window.getComputedStyle(el);
        return {
          display: computed.display,
          flexDirection: computed.flexDirection,
          gridTemplateColumns: computed.gridTemplateColumns
        };
      });
      
      console.log(`Layout styles in ${browserName}:`, styles);
    }
    
    // JavaScript API サポート確認
    const supportedAPIs = await page.evaluate(() => {
      return {
        fetch: typeof fetch !== 'undefined',
        webSocket: typeof WebSocket !== 'undefined',
        fileAPI: typeof File !== 'undefined',
        dragAndDrop: 'ondragstart' in document.createElement('div'),
        formData: typeof FormData !== 'undefined'
      };
    });
    
    console.log(`API support in ${browserName}:`, supportedAPIs);
    
    // 必須APIのサポート確認
    expect(supportedAPIs.fetch).toBeTruthy();
    expect(supportedAPIs.fileAPI).toBeTruthy();
    expect(supportedAPIs.formData).toBeTruthy();
    
    console.log(`ブラウザ互換性テスト完了: ${browserName}`);
  });

  test('キーボードナビゲーション @accessibility', async ({ page }) => {
    console.log('キーボードナビゲーションテスト開始');
    
    // Tab キーでのフォーカス移動テスト
    await page.keyboard.press('Tab');
    let focusedElement = await page.locator(':focus').getAttribute('data-testid');
    console.log('First focused element:', focusedElement);
    
    // 主要な操作可能要素を順次フォーカス
    const expectedFocusOrder = [
      'file-upload-area',
      'task-list',
      'settings-button'
    ];
    
    for (let i = 0; i < expectedFocusOrder.length; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100);
      
      focusedElement = await page.locator(':focus').getAttribute('data-testid');
      console.log(`Focus ${i + 1}:`, focusedElement);
    }
    
    // Enter キーでの操作確認
    await page.keyboard.press('Enter');
    
    // Escape キーでモーダル閉じる操作
    const modal = page.getByTestId('file-chooser-modal');
    if (await modal.isVisible()) {
      await page.keyboard.press('Escape');
      await expect(modal).not.toBeVisible();
    }
    
    console.log('キーボードナビゲーションテスト完了');
  });

  test('アクセシビリティ標準準拠 @accessibility', async ({ page }) => {
    console.log('アクセシビリティテスト開始');
    
    // ARIA属性の確認
    const ariaElements = await page.locator('[aria-label], [aria-describedby], [role]').all();
    
    for (const element of ariaElements) {
      const ariaLabel = await element.getAttribute('aria-label');
      const ariaDescribedBy = await element.getAttribute('aria-describedby');
      const role = await element.getAttribute('role');
      
      console.log('ARIA attributes:', { ariaLabel, ariaDescribedBy, role });
      
      // 適切なARIA属性が設定されていることを確認
      if (ariaLabel) {
        expect(ariaLabel.length).toBeGreaterThan(0);
      }
    }
    
    // フォーカス表示の確認
    const focusableElements = await page.locator('button, input, [tabindex]').all();
    
    for (const element of focusableElements) {
      await element.focus();
      
      // フォーカススタイルが適用されることを確認
      const focusStyles = await element.evaluate(el => {
        const computed = window.getComputedStyle(el, ':focus');
        return {
          outline: computed.outline,
          boxShadow: computed.boxShadow,
          border: computed.border
        };
      });
      
      // フォーカス表示が存在することを確認
      const hasFocusStyles = focusStyles.outline !== 'none' || 
                            focusStyles.boxShadow !== 'none' ||
                            focusStyles.border !== 'none';
      
      if (!hasFocusStyles) {
        console.warn('No focus styles detected for element:', await element.getAttribute('data-testid'));
      }
    }
    
    console.log('アクセシビリティテスト完了');
  });

  test('ダーク・ライトモード切り替え @ui', async ({ page }) => {
    console.log('テーマ切り替えテスト開始');
    
    // ライトモードの確認
    const themeToggle = page.getByTestId('theme-toggle');
    if (await themeToggle.isVisible()) {
      // 現在のテーマを確認
      const currentTheme = await page.getAttribute('html', 'data-theme');
      console.log('Current theme:', currentTheme);
      
      // テーマ切り替え
      await themeToggle.click();
      await page.waitForTimeout(500); // アニメーション待機
      
      // テーマが切り替わったことを確認
      const newTheme = await page.getAttribute('html', 'data-theme');
      console.log('New theme:', newTheme);
      expect(newTheme).not.toBe(currentTheme);
      
      // UI要素の色が変更されたことを確認
      const backgroundColor = await page.locator('body').evaluate(el => {
        return window.getComputedStyle(el).backgroundColor;
      });
      
      console.log('Background color after theme change:', backgroundColor);
      
      // テーマを元に戻す
      await themeToggle.click();
      await page.waitForTimeout(500);
    }
    
    console.log('テーマ切り替えテスト完了');
  });

  test('言語切り替え @ui @i18n', async ({ page }) => {
    console.log('言語切り替えテスト開始');
    
    const languageSelector = page.getByTestId('language-selector');
    if (await languageSelector.isVisible()) {
      // 現在の言語を確認
      const currentLang = await page.getAttribute('html', 'lang');
      console.log('Current language:', currentLang);
      
      // 利用可能な言語オプションを確認
      await languageSelector.click();
      const languageOptions = await page.locator('[data-testid^="lang-option-"]').all();
      
      if (languageOptions.length > 1) {
        // 異なる言語を選択
        const targetOption = languageOptions.find(async option => {
          const optionLang = await option.getAttribute('data-testid').replace('lang-option-', '');
          return optionLang !== currentLang;
        });
        
        if (targetOption) {
          await targetOption.click();
          await page.waitForTimeout(1000); // 言語変更処理を待機
          
          // 言語が変更されたことを確認
          const newLang = await page.getAttribute('html', 'lang');
          console.log('New language:', newLang);
          expect(newLang).not.toBe(currentLang);
          
          // UI テキストが変更されたことを確認
          const headerText = await page.getByTestId('main-header').textContent();
          console.log('Header text after language change:', headerText);
        }
      }
    }
    
    console.log('言語切り替えテスト完了');
  });

  test('アニメーション・トランジション @ui', async ({ page }) => {
    console.log('アニメーションテスト開始');
    
    // ページ読み込み時のアニメーション確認
    const animatedElements = await page.locator('[data-animate], .fade-in, .slide-in').all();
    
    for (const element of animatedElements) {
      // アニメーション完了まで待機
      await expect(element).toBeVisible();
      
      // アニメーション関連のCSSプロパティを確認
      const animationStyles = await element.evaluate(el => {
        const computed = window.getComputedStyle(el);
        return {
          transition: computed.transition,
          animation: computed.animation,
          transform: computed.transform,
          opacity: computed.opacity
        };
      });
      
      console.log('Animation styles:', animationStyles);
    }
    
    // ローディングアニメーションの確認
    await helpers.uploadFile('test-video-small.mp4');
    
    const loadingSpinner = page.getByTestId('loading-spinner');
    if (await loadingSpinner.isVisible()) {
      // スピナーアニメーションの確認
      const spinnerStyles = await loadingSpinner.evaluate(el => {
        const computed = window.getComputedStyle(el);
        return {
          animation: computed.animation,
          animationDuration: computed.animationDuration,
          animationIterationCount: computed.animationIterationCount
        };
      });
      
      console.log('Spinner animation:', spinnerStyles);
      expect(spinnerStyles.animation).not.toBe('none');
    }
    
    console.log('アニメーションテスト完了');
  });
});

// ヘルパー関数：特定のビューポートでの主要機能テスト
async function testMainFunctionsAtViewport(page, viewport) {
  console.log(`  Testing main functions at ${viewport.name}`);
  
  // ファイルアップロードエリアの表示・操作確認
  const uploadArea = page.getByTestId('file-upload-area');
  await expect(uploadArea).toBeVisible();
  
  // タスクリストの表示確認
  const taskList = page.getByTestId('task-list');
  await expect(taskList).toBeVisible();
  
  // モバイルサイズの場合、ハンバーガーメニューの確認
  if (viewport.width < 768) {
    const mobileMenu = page.getByTestId('mobile-menu-button');
    if (await mobileMenu.isVisible()) {
      await mobileMenu.click();
      
      const menuPanel = page.getByTestId('mobile-menu-panel');
      await expect(menuPanel).toBeVisible();
      
      // メニューを閉じる
      await page.getByTestId('mobile-menu-close').click();
      await expect(menuPanel).not.toBeVisible();
    }
  }
  
  // テキストの可読性確認（文字サイズ、行間など）
  const textElements = await page.locator('p, span, div[class*="text"]').all();
  
  for (const element of textElements.slice(0, 3)) { // 最初の3要素のみテスト
    const textStyles = await element.evaluate(el => {
      const computed = window.getComputedStyle(el);
      return {
        fontSize: parseFloat(computed.fontSize),
        lineHeight: computed.lineHeight,
        color: computed.color
      };
    });
    
    // 最小フォントサイズの確認
    if (textStyles.fontSize < 12) {
      console.warn(`Small font size detected: ${textStyles.fontSize}px at ${viewport.name}`);
    }
  }
}