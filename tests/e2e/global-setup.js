const fs = require('fs-extra');
const path = require('path');

async function globalSetup() {
  console.log('🚀 Global setup: Preparing test environment...');
  
  // Create test fixtures directory
  const fixturesDir = path.join(__dirname, 'fixtures');
  await fs.ensureDir(fixturesDir);
  
  // Create mock video files for testing
  await createMockVideoFiles(fixturesDir);
  
  // Ensure test output directories exist
  const testDirs = ['test-results', 'test-downloads'];
  for (const dir of testDirs) {
    await fs.ensureDir(path.join(process.cwd(), dir));
  }
  
  console.log('✅ Global setup completed');
}

async function createMockVideoFiles(fixturesDir) {
  // Create different sized mock video files for testing
  const mockFiles = [
    {
      name: 'test-video-small.mp4',
      size: 1024 * 1024, // 1MB
      content: Buffer.alloc(1024 * 1024, 'mock video data')
    },
    {
      name: 'test-video-medium.mp4', 
      size: 10 * 1024 * 1024, // 10MB
      content: Buffer.alloc(10 * 1024 * 1024, 'mock video data')
    },
    {
      name: 'test-invalid-file.txt',
      size: 1024,
      content: Buffer.from('This is not a video file')
    },
    {
      name: 'test-japanese-名前.mp4',
      size: 2 * 1024 * 1024, // 2MB
      content: Buffer.alloc(2 * 1024 * 1024, 'mock video with japanese name')
    }
  ];
  
  for (const file of mockFiles) {
    const filePath = path.join(fixturesDir, file.name);
    if (!await fs.pathExists(filePath)) {
      await fs.writeFile(filePath, file.content);
      console.log(`Created mock file: ${file.name} (${file.size} bytes)`);
    }
  }
}

module.exports = globalSetup;