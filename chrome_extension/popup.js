function normalizeThaiProductTitle(rawTitle) {
  if (!rawTitle) return '';
  let str = String(rawTitle)
    .replace(/^\[(Mall|ช้อปปี้|พร้อมส่ง|ของแท้|แท้ 100%)\]\s*/gi, '')
    .replace(/\s*\[(Mall|ช้อปปี้|พร้อมส่ง|ของแท้|แท้ 100%|อัตโนมัติ.*?)\]/gi, '')
    .replace(/\s*\(รับประกัน.*?\)/gi, '')
    .replace(/\s*\(พร้อมส่ง.*?\)/gi, '')
    .replace(/\s*\(ของแท้.*?\)/gi, '')
    .replace(/\s*【.*?】/g, '')
    .replace(/\s*\[.*?\]/g, '')
    .trim();

  // Convert unit abbreviations to clear spoken Thai words without breaking decimals
  str = str.replace(/(\d+(?:\.\d+)?)\s*(?:m|เมตร|ม\.)(?=[^ก-๙a-zA-Z]|$)/gi, '$1 เมตร');
  str = str.replace(/(\d+(?:\.\d+)?)\s*(?:ml|มล|มล\.)(?=[^ก-๙a-zA-Z]|$)/gi, '$1 มิลลิลิตร');
  str = str.replace(/(\d+(?:\.\d+)?)\s*(?:w|วัตต์)(?=[^ก-๙a-zA-Z]|$)/gi, '$1 วัตต์');
  str = str.replace(/(\d+(?:\.\d+)?)\s*(?:kg|กก|กก\.|กิโล|กิโลกรัม)(?=[^ก-๙a-zA-Z]|$)/gi, '$1 กิโลกรัม');
  str = str.replace(/(\d+(?:\.\d+)?)\s*(?:l|ลิตร)(?=[^ก-๙a-zA-Z]|$)/gi, '$1 ลิตร');
  str = str.replace(/(\d+)\s*(?:mah|มิลลิแอมป์|แอมป์)(?=[^ก-๙a-zA-Z]|$)/gi, '$1 มิลลิแอมป์');

  str = str.replace(/[\/\|]/g, ' ')
           .replace(/\s+/g, ' ')
           .replace(/[.,;]$/, '')
           .trim();

  return str;
}

document.addEventListener('DOMContentLoaded', async () => {
  const nameEl = document.getElementById('product-name');
  const priceEl = document.getElementById('product-price');
  const statusEl = document.getElementById('page-status');
  const exportBtn = document.getElementById('btn-export');
  const envSelect = document.getElementById('select-env');
  const mediaLabel = document.getElementById('label-media');

  let currentData = null;

  // Restore env preference and cached product safely
  if (chrome && chrome.storage && chrome.storage.local) {
    try {
      chrome.storage.local.get(['factory_env', 'last_extracted_product'], (res) => {
        if (chrome.runtime && chrome.runtime.lastError) {
          console.warn('Storage get notice:', chrome.runtime.lastError.message);
          return;
        }
        if (res && res.factory_env && envSelect) envSelect.value = res.factory_env;
        if (res && res.last_extracted_product) {
          currentData = res.last_extracted_product;
          displayData(currentData);
        }
      });
    } catch (e) {
      console.warn('Storage access warning:', e);
    }
  }

  if (envSelect) {
    envSelect.addEventListener('change', () => {
      if (chrome && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ factory_env: envSelect.value }, () => {
          if (chrome.runtime && chrome.runtime.lastError) {
            console.warn(chrome.runtime.lastError.message);
          }
        });
      }
    });
  }

  // Query active tab safely
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const tab = tabs && tabs[0];
    if (tab && tab.url && (tab.url.includes('shopee.co.th') || tab.url.includes('shope.ee'))) {
      if (statusEl) statusEl.innerText = 'อยู่ใน Shopee';
      
      chrome.tabs.sendMessage(tab.id, { action: 'extract_product' }, (response) => {
        const err = chrome.runtime && chrome.runtime.lastError;
        if (err || !response) {
          // If script not injected yet, inject programmatically using chrome.scripting
          if (chrome.scripting && chrome.scripting.executeScript) {
            chrome.scripting.executeScript({
              target: { tabId: tab.id },
              files: ['content.js']
            }, () => {
              const injectErr = chrome.runtime && chrome.runtime.lastError;
              if (injectErr) {
                console.warn('Content script injection notice:', injectErr.message);
                return;
              }
              chrome.tabs.sendMessage(tab.id, { action: 'extract_product' }, (res2) => {
                const msgErr = chrome.runtime && chrome.runtime.lastError;
                if (!msgErr && res2) {
                  currentData = res2;
                  displayData(currentData);
                }
              });
            });
          }
        } else {
          currentData = response;
          displayData(currentData);
        }
      });
    } else {
      if (statusEl) {
        statusEl.innerText = 'เปิดแท็บ Shopee';
        statusEl.style.color = '#f59e0b';
        statusEl.style.borderColor = 'rgba(245, 158, 11, 0.4)';
      }
      if (nameEl) nameEl.innerText = 'กรุณาเปิดแท็บสินค้า Shopee เพื่อดึงข้อมูลอัตโนมัติ';
    }
  } catch (e) {
    console.warn('Tab query notice:', e);
  }

  function displayData(data) {
    if (!data) return;
    if (data.title) data.title = normalizeThaiProductTitle(data.title);
    if (nameEl) nameEl.innerText = data.title || 'ตรวจพบสินค้า';
    
    // Accurate Price & Price Range Display (e.g. ฿39 - ฿180 or ฿96.00)
    const displayPrice = data.price_str || ('฿' + Number(data.price || 0).toFixed(2));
    if (priceEl) {
      if (priceEl.tagName === 'INPUT') {
        priceEl.value = displayPrice;
      } else {
        priceEl.innerText = displayPrice;
      }
    }

    if (mediaLabel) {
      const vCount = (data.video_urls && data.video_urls.length) || (data.video_url ? 1 : 0);
      if (vCount > 1) {
        mediaLabel.innerText = `🎬 พบคลิปวิดีโอ ${vCount} คลิป (หลัก + รีวิวคอมเมนต์)`;
        mediaLabel.style.color = '#34d399';
      } else if (vCount === 1) {
        mediaLabel.innerText = '🎬 พบคลิปวิดีโอแท้ (ผสานรีวิว/ภาพต่อหากไม่ครบ 20 วิ)';
        mediaLabel.style.color = '#34d399';
      } else if (data.images && data.images.length > 0) {
        mediaLabel.innerText = `📸 พบภาพสินค้า ${data.images.length} รูป (ใช้ภาพโฆษณาแปลงโมชัน 9:16 แทนอัตโนมัติ)`;
        mediaLabel.style.color = '#f59e0b';
      }
    }
  }

  // Allow manual edit if user wants to tweak price or title directly in popup
  if (priceEl && priceEl.tagName === 'INPUT') {
    priceEl.addEventListener('input', () => {
      if (!currentData) currentData = {};
      currentData.price_str = priceEl.value;
      const numMatch = priceEl.value.replace(/,/g, '').match(/\d+(\.\d+)?/);
      if (numMatch) {
        currentData.price = parseFloat(numMatch[0]);
      }
    });
  }

  if (nameEl) {
    nameEl.setAttribute('contenteditable', 'true');
    nameEl.setAttribute('title', 'คลิกเพื่อแก้ไขชื่อสินค้าได้');
    nameEl.addEventListener('input', () => {
      if (!currentData) currentData = {};
      currentData.title = nameEl.innerText.trim();
    });
  }

  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      if (!currentData) {
        alert('ยังไม่พบข้อมูลสินค้า กรุณาเปิดหน้าสินค้า Shopee แล้วลองใหม่อีกครั้ง');
        return;
      }

      // Ensure edited values in popup inputs are included in export payload
      if (priceEl && priceEl.tagName === 'INPUT') {
        currentData.price_str = priceEl.value;
        const numMatch = priceEl.value.replace(/,/g, '').match(/\d+(\.\d+)?/);
        if (numMatch) currentData.price = parseFloat(numMatch[0]);
      }
      if (nameEl && nameEl.innerText.trim()) {
        currentData.title = nameEl.innerText.trim();
      }

      const baseUrl = (envSelect && envSelect.value) ? envSelect.value : 'https://shopee-video-factory.vercel.app';
      let payload = '';
      try {
        payload = btoa(unescape(encodeURIComponent(JSON.stringify(currentData))));
      } catch (e) {
        payload = encodeURIComponent(JSON.stringify(currentData));
      }
      const targetUrl = `${baseUrl}/#import=${payload}`;
      
      if (chrome && chrome.tabs && chrome.tabs.create) {
        chrome.tabs.create({ url: targetUrl });
      } else {
        window.open(targetUrl, '_blank');
      }
    });
  }
});
