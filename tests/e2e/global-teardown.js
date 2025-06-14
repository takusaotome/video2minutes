const fs = require('fs-extra');
const path = require('path');

async function globalTeardown() {
  console.log('🧹 Global teardown: Cleaning up test environment...');
  
  // Clean up test downloads
  const downloadsDir = path.join(process.cwd(), 'test-downloads');
  if (await fs.pathExists(downloadsDir)) {
    await fs.remove(downloadsDir);
    console.log('Cleaned up test downloads directory');
  }
  
  // Clean up temporary test files (keep fixtures for reuse)
  const tempFiles = [
    'test-results/temp-uploads',
    'test-results/temp-processing'
  ];
  
  for (const tempPath of tempFiles) {
    const fullPath = path.join(process.cwd(), tempPath);
    if (await fs.pathExists(fullPath)) {
      await fs.remove(fullPath);
      console.log(`Cleaned up: ${tempPath}`);
    }
  }
  
  console.log('✅ Global teardown completed');
}

module.exports = globalTeardown;