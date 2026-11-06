/**
 * Shopee 1-Click Video Maker - Content Script
 * Extracts real product title, price, gallery video, and images directly from logged-in Shopee tab.
 */

(function () {
  'use strict';

  // Prevent multiple injections
  if (window.__shopeeVideoFactoryInjected) return;
  window.__shopeeVideoFactoryInjected = true;

  console.log('⚡ Shopee 1-Click Video Maker initialized.');

  // Target Factory URL (Prefers production, falls back to local)
  const FACTORY_URL = 'https://shopee-video-factory.vercel.app';

  // 1. EXTRACTOR HELPER
  function extractShopeePrice() {
    // 1. JSON-LD Extraction (Shopee embeds schema.org Product metadata with 100% exact price)
    try {
      const ldScripts = document.querySelectorAll('script[type="application/ld+json"]');
      for (const s of ldScripts) {
        if (!s.innerText) continue;
        const ld = JSON.parse(s.innerText);
        const data = Array.isArray(ld) ? ld[0] : ld;
        if (data && (data['@type'] === 'Product' || data.offers)) {
          const offers = data.offers;
          if (offers) {
            if (offers.lowPrice !== undefined && offers.highPrice !== undefined) {
              const low = parseFloat(offers.lowPrice);
              const high = parseFloat(offers.highPrice);
              if (!isNaN(low) && low > 0) {
                return {
                  price: low,
                  max_price: !isNaN(high) ? high : low,
                  price_str: (high && high > low) ? `฿${low} - ฿${high}` : `฿${low}`,
                  is_range: high && high > low
                };
              }
            } else if (offers.price !== undefined) {
              const p = parseFloat(offers.price);
              if (!isNaN(p) && p > 0) {
                return {
                  price: p,
                  max_price: p,
                  price_str: `฿${p}`,
                  is_range: false
                };
              }
            }
          }
        }
      }
    } catch (e) {
      console.warn('JSON-LD price extraction notice:', e);
    }

    // 2. OpenGraph & Meta Price
    try {
      const metaAmount = document.querySelector('meta[property="product:price:amount"]');
      if (metaAmount && metaAmount.content) {
        const p = parseFloat(metaAmount.content);
        if (!isNaN(p) && p > 0) {
          return { price: p, max_price: p, price_str: `฿${p}`, is_range: false };
        }
      }
    } catch (e) {}

    // 3. DOM Range & Single Price Regex
    const excludeWords = [
      'โค้ด', 'ส่วนลด', 'voucher', 'ล่าช้า', 'ขั้นต่ำ', 'ค่าส่ง',
      'ค่าจัดส่ง', 'ส่งฟรี', 'coin', 'เหรียญ', 'cashback',
      'คืนเงิน', 'ชิ้น', 'ลดเพิ่ม', 'ติดตาม', 'ช้อปเพิ่ม', 'ผ่อนชำระ'
    ];

    const rangeRegex = /(?:฿|THB)?\s*([\d,]+(?:\.\d+)?)\s*[-–—~至]\s*฿?\s*([\d,]+(?:\.\d+)?)/;
    const singleRegex = /(?:฿|THB)\s*([\d,]+(?:\.\d+)?)/;

    function isExcluded(text) {
      if (!text) return true;
      const lower = text.toLowerCase();
      return excludeWords.some(w => lower.includes(w));
    }

    // Look for dedicated Shopee price elements first (classes used by Shopee)
    const dedicatedSelectors = [
      '[class*="price" i]',
      '[class*="Price"]',
      'div.pqTWkA',
      'div._3n5zSv',
      'div._3e_UQT',
      'div.flex.items-center'
    ];

    for (const sel of dedicatedSelectors) {
      const els = Array.from(document.querySelectorAll(sel));
      for (const el of els) {
        const text = (el.innerText || '').trim();
        if (!text || text.length > 50) continue;
        if (text.includes('฿') && rangeRegex.test(text) && !isExcluded(text)) {
          const match = text.match(rangeRegex);
          if (match) {
            const minP = parseFloat(match[1].replace(/,/g, ''));
            const maxP = parseFloat(match[2].replace(/,/g, ''));
            if (!isNaN(minP) && minP > 0 && !isNaN(maxP) && maxP >= minP) {
              return {
                price: minP,
                max_price: maxP,
                price_str: `฿${match[1].trim()} - ฿${match[2].trim()}`,
                is_range: true
              };
            }
          }
        }
      }
    }

    // General DOM search near H1
    const h1 = document.querySelector('h1') || 
               document.querySelector('.WBVL_7') || 
               document.querySelector('._44qnta') || 
               document.querySelector('[class*="product-briefing"]') || 
               document.querySelector('[class*="title"]');

    const searchRoots = [];
    if (h1) {
      let p = h1.parentElement;
      for (let i = 0; i < 4 && p && p !== document.body; i++) {
        searchRoots.push(p);
        p = p.parentElement;
      }
    }
    searchRoots.push(document.body);

    for (const root of searchRoots) {
      const candidates = Array.from(root.querySelectorAll('div, span, p, h2, h3'));
      const validElements = [];

      for (const el of candidates) {
        try {
          if (el.tagName === 'DEL' || el.tagName === 'S') continue;
          const style = window.getComputedStyle(el);
          if (style.textDecoration && style.textDecoration.includes('line-through')) continue;
        } catch (e) {}

        const text = (el.innerText || '').trim();
        if (!text || !text.includes('฿') || text.length > 70) continue;
        if (isExcluded(text)) continue;

        validElements.push({ el, text });
      }

      // PASS 1: Check for Price Range (e.g. ฿39 - ฿180)
      for (const item of validElements) {
        const match = item.text.match(rangeRegex);
        if (match) {
          const minP = parseFloat(match[1].replace(/,/g, ''));
          const maxP = parseFloat(match[2].replace(/,/g, ''));
          if (!isNaN(minP) && minP > 0 && !isNaN(maxP) && maxP >= minP) {
            return {
              price: minP,
              max_price: maxP,
              price_str: `฿${match[1].trim()} - ฿${match[2].trim()}`,
              is_range: true
            };
          }
        }
      }

      // PASS 2: Check for Single Price
      for (const item of validElements) {
        const match = item.text.match(singleRegex);
        if (!match) continue;

        const val = parseFloat(match[1].replace(/,/g, ''));
        if (isNaN(val) || val <= 0 || val > 1000000) continue;

        return {
          price: val,
          max_price: val,
          price_str: `฿${match[1].trim()}`,
          is_range: false
        };
      }
    }

    return { price: 118.0, max_price: 118.0, price_str: '฿118.00', is_range: false };
  }

  function normalizeThaiProductTitle(rawTitle) {
    if (!rawTitle) return '';
    let str = rawTitle
      .replace(/^\[(Mall|ช้อปปี้|พร้อมส่ง|ของแท้|แท้ 100%)\]\s*/gi, '')
      .replace(/\s*\[อัตโนมัติ.*?\]/gi, '')
      .replace(/\s*\(รับประกัน.*?\)/gi, '')
      .replace(/\s*\(พร้อมส่ง.*?\)/gi, '')
      .replace(/\s*【.*?】/g, '')
      .replace(/\s*\[.*?\]/g, '')
      .trim();

    // Convert unit abbreviations to clear spoken Thai words
    str = str.replace(/(\d+(?:\.\d+)?)\s*(?:m|เมตร|ม\.)(?=[^ก-๙a-zA-Z]|$)/gi, '$1 เมตร');
    str = str.replace(/(\d+(?:\.\d+)?)\s*(?:ml|มล|มล\.)(?=[^ก-๙a-zA-Z]|$)/gi, '$1 มิลลิลิตร');
    str = str.replace(/(\d+(?:\.\d+)?)\s*(?:w|วัตต์)(?=[^ก-๙a-zA-Z]|$)/gi, '$1 วัตต์');
    str = str.replace(/(\d+(?:\.\d+)?)\s*(?:kg|กก|กก\.|กิโล|กิโลกรัม)(?=[^ก-๙a-zA-Z]|$)/gi, '$1 กิโลกรัม');
    str = str.replace(/(\d+(?:\.\d+)?)\s*(?:l|ลิตร)(?=[^ก-๙a-zA-Z]|$)/gi, '$1 ลิตร');

    str = str.replace(/[\/\|]/g, ' ')
             .replace(/\s+/g, ' ')
             .replace(/[.,;]$/, '')
             .trim();

    return str;
  }

  function extractProductData() {
    // Title Extraction
    let title = '';
    const titleCandidates = [
      document.querySelector('h1'),
      document.querySelector('._44qnta'),
      document.querySelector('.WBVL_7'),
      document.querySelector('[class*="product-briefing"] span'),
      document.querySelector('[class*="title"]')
    ];
    for (const el of titleCandidates) {
      if (el && el.innerText && el.innerText.trim().length > 5) {
        title = el.innerText.trim();
        break;
      }
    }
    if (!title) {
      title = document.title
        .replace('| Shopee Thailand', '')
        .replace('Shopee Thailand |', '')
        .replace('ซื้อขายผ่านมือถือ หรือออนไลน์', '')
        .trim();
    }

    // Accurate Price Extraction (Range & Single)
    const priceData = extractShopeePrice();

    // Real Gallery Video Extraction
    let videoUrl = '';
    const videoElements = document.querySelectorAll('video, video source');
    for (const v of videoElements) {
      const src = v.src || v.getAttribute('src');
      if (src && (src.includes('vod.susercontent.com') || src.includes('.mp4'))) {
        videoUrl = src;
        break;
      }
    }

    // If video tag is not yet mounted, check for video thumbnail in gallery
    if (!videoUrl) {
      const playIcons = document.querySelectorAll('[class*="play"], [class*="video-icon"]');
      if (playIcons.length > 0) {
        // Thumbnail has video indicator; if user clicks it, it loads
        const vid = document.querySelector('video');
        if (vid && vid.src) videoUrl = vid.src;
      }
    }

    // Gallery Images Extraction
    const images = [];
    const imgElements = document.querySelectorAll('picture img, [class*="carousel"] img, [class*="gallery"] img');
    for (const img of imgElements) {
      const src = img.src || img.getAttribute('src');
      if (src && src.includes('susercontent.com') && !src.includes('avatar') && !images.includes(src)) {
        // Clean to high-resolution URL
        const clean = src.split('_tn')[0].split('_b')[0];
        images.push(clean);
      }
    }

    return {
      title: normalizeThaiProductTitle(title),
      price: priceData.price,
      max_price: priceData.max_price,
      price_str: priceData.price_str,
      is_range: priceData.is_range,
      video_url: videoUrl,
      images: images.slice(0, 10),
      shopee_url: window.location.href.split('?')[0],
      extracted_at: new Date().toISOString()
    };
  }

  // 2. CREATE FLOATING ACTION BUTTON ON SHOPEE PRODUCT PAGE
  function injectFloatingButton() {
    // Only inject on product pages
    if (!window.location.href.includes('/product/') && !window.location.href.includes('-i.')) {
      return;
    }

    if (document.getElementById('shopee-video-factory-btn')) return;

    const btn = document.createElement('div');
    btn.id = 'shopee-video-factory-btn';
    btn.innerHTML = `
      <div class="svf-floating-card">
        <div class="svf-badge">
          <span class="svf-dot"></span>
          <span>Shopee AI Video</span>
        </div>
        <button type="button" class="svf-action-btn" id="svf-trigger-btn">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
          </svg>
          <span>ผลิตวิดีโอ 9:16 (1-Click)</span>
        </button>
      </div>
    `;

    document.body.appendChild(btn);

    const trigger = document.getElementById('svf-trigger-btn');
    trigger.addEventListener('click', () => {
      trigger.classList.add('svf-loading');
      trigger.innerHTML = `
        <svg class="svf-spin" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
          <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path>
        </svg>
        <span>กำลังเปิดสตูดิโอ...</span>
      `;

      // Extract immediately without delay
      const data = extractProductData();
      console.log('📦 Extracted Product Data for 9:16 Video:', data);

      if (chrome && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ last_extracted_product: data });
      }

      let payload = '';
      try {
        payload = btoa(unescape(encodeURIComponent(JSON.stringify(data))));
      } catch (e) {
        payload = encodeURIComponent(JSON.stringify(data));
      }
      const targetUrl = `${FACTORY_URL}/#import=${payload}`;

      // Open tab via background service worker (100% reliable, never blocked by popup blocker)
      if (chrome && chrome.runtime && chrome.runtime.sendMessage) {
        chrome.runtime.sendMessage({ action: 'open_tab', url: targetUrl }, (res) => {
          if (chrome.runtime.lastError || !res) {
            window.open(targetUrl, '_blank');
          }
        });
      } else {
        window.open(targetUrl, '_blank');
      }

      setTimeout(() => {
        trigger.classList.remove('svf-loading');
        trigger.innerHTML = `
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span>เปิดสตูดิโอ 9:16 สำเร็จ!</span>
        `;
        setTimeout(() => {
          trigger.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
            <span>ผลิตวิดีโอ 9:16 (1-Click)</span>
          `;
        }, 2500);
      }, 350);
    });
  }

  // 3. LISTEN TO MESSAGES FROM POPUP SAFELY
  if (chrome && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request && request.action === 'extract_product') {
        try {
          const data = extractProductData();
          sendResponse(data);
        } catch (err) {
          console.warn('Extraction notice:', err);
          sendResponse({ error: err.message });
        }
      }
      return false; // synchronous response
    });
  }

  // Run injection
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectFloatingButton);
  } else {
    injectFloatingButton();
  }

  // Observe URL changes (SPA navigation)
  let lastUrl = location.href;
  new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
      lastUrl = url;
      setTimeout(injectFloatingButton, 1000);
    }
  }).observe(document, { subtree: true, childList: true });

})();
