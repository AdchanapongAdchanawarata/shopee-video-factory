// Background Service Worker for Shopee 1-Click Video Maker
// Handles tab creation reliably without triggering browser popup blockers

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request && request.action === 'open_tab' && request.url) {
    chrome.tabs.create({ url: request.url }, (tab) => {
      sendResponse({ success: true, tabId: tab ? tab.id : null });
    });
    return true; // Keep message channel open for async response
  }
  return false;
});
