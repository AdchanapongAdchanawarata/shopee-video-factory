document.addEventListener('DOMContentLoaded', async () => {
  const nameEl = document.getElementById('product-name');
  const priceEl = document.getElementById('product-price');
  const statusEl = document.getElementById('page-status');
  const exportBtn = document.getElementById('btn-export');
  const envSelect = document.getElementById('select-env');
  const mediaLabel = document.getElementById('label-media');

  let currentData = null;

  // Restore env preference
  if (chrome && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(['factory_env', 'last_extracted_product'], (res) => {
      if (res.factory_env) envSelect.value = res.factory_env;
      if (res.last_extracted_product) {
        currentData = res.last_extracted_product;
        displayData(currentData);
      }
    });
  }

  envSelect.addEventListener('change', () => {
    chrome.storage.local.set({ factory_env: envSelect.value });
  });

  // Query active tab
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url && (tab.url.includes('shopee.co.th') || tab.url.includes('shope.ee'))) {
      statusEl.innerText = 'อยู่ใน Shopee';
      chrome.tabs.sendMessage(tab.id, { action: 'extract_product' }, (response) => {
        if (chrome.runtime.lastError || !response) {
          // If script not injected yet, inject programmatically
          chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ['content.js']
          }, () => {
            chrome.tabs.sendMessage(tab.id, { action: 'extract_product' }, (res2) => {
              if (res2) {
                currentData = res2;
                displayData(currentData);
              }
            });
          });
        } else {
          currentData = response;
          displayData(currentData);
        }
      });
    } else {
      statusEl.innerText = 'เปิดแท็บ Shopee';
      statusEl.style.color = '#f59e0b';
      statusEl.style.borderColor = 'rgba(245, 158, 11, 0.4)';
      nameEl.innerText = 'กรุณาเปิดแท็บสินค้า Shopee เพื่อดึงข้อมูลอัตโนมัติ';
    }
  } catch (e) {
    console.error(e);
  }

  function displayData(data) {
    if (!data) return;
    nameEl.innerText = data.title || 'ตรวจพบสินค้า';
    priceEl.innerText = '฿' + Number(data.price || 0).toFixed(2);
    if (data.video_url) {
      mediaLabel.innerText = '🎬 พบคลิปวิดีโอแท้ 100%';
      mediaLabel.style.color = '#34d399';
    } else if (data.images && data.images.length > 0) {
      mediaLabel.innerText = `📸 พบภาพแกลเลอรี ${data.images.length} รูป`;
      mediaLabel.style.color = '#f59e0b';
    }
  }

  exportBtn.addEventListener('click', () => {
    if (!currentData) {
      alert('ยังไม่พบข้อมูลสินค้า กรุณาเปิดหน้าสินค้า Shopee แล้วลองใหม่อีกครั้ง');
      return;
    }
    const baseUrl = envSelect.value || 'https://shopee-video-factory.vercel.app';
    const payload = encodeURIComponent(JSON.stringify(currentData));
    const targetUrl = `${baseUrl}/#import=${payload}`;
    chrome.tabs.create({ url: targetUrl });
  });
});
