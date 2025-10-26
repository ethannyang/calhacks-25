/**
 * Simple keyboard test script to verify uiohook is detecting the ` key
 * Run with: node test_keyboard.js
 */

const { uIOhook, UiohookKey } = require('./node_modules/uiohook-napi');

console.log('========================================');
console.log('⌨️  Keyboard Monitoring Test');
console.log('========================================');
console.log('');
console.log('Testing if the ` (grave) key is detected...');
console.log('Press the ` key (above Tab, left of 1)');
console.log('Press Ctrl+C to exit');
console.log('');

let isGravePressed = false;

// Monitor keydown
uIOhook.on('keydown', (e) => {
  console.log(`🔽 Key pressed: ${e.keycode} (looking for Grave=${UiohookKey.Grave})`);

  // Check multiple possible key codes for the grave/tilde key
  if (e.keycode === UiohookKey.Grave || e.keycode === 41 || e.keycode === 50) {
    if (!isGravePressed) {
      isGravePressed = true;
      console.log('✅ ` KEY DETECTED - Voice input should activate!');
    }
  }
});

// Monitor keyup
uIOhook.on('keyup', (e) => {
  console.log(`🔼 Key released: ${e.keycode} (looking for Grave=${UiohookKey.Grave})`);

  // Check multiple possible key codes for the grave/tilde key
  if (e.keycode === UiohookKey.Grave || e.keycode === 41 || e.keycode === 50) {
    if (isGravePressed) {
      isGravePressed = false;
      console.log('✅ ` KEY RELEASED - Voice input should deactivate!');
    }
  }
});

// Start monitoring
try {
  uIOhook.start();
  console.log('✅ Keyboard monitoring started successfully!');
  console.log(`   Grave key code: ${UiohookKey.Grave}`);
  console.log('');
} catch (error) {
  console.error('❌ Failed to start keyboard monitoring:', error);
  console.error('');
  console.error('This might be a permissions issue.');
  console.error('On macOS, you need to grant accessibility permissions:');
  console.error('1. System Settings → Privacy & Security → Accessibility');
  console.error('2. Add Terminal (or your terminal app)');
  console.error('3. Restart this script');
  process.exit(1);
}

// Cleanup on exit
process.on('SIGINT', () => {
  console.log('');
  console.log('Stopping keyboard monitoring...');
  uIOhook.stop();
  process.exit(0);
});
