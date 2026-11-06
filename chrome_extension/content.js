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

    // Price Extraction
    let price = 199.0;
    const priceCandidates = [
      document.querySelector('.pqTWkA'),
      document.querySelector('._3n5NQx'),
      document.querySelector('._2v0HG1'),
      document.querySelector('[class*="price"]')
    ];
    for (const el of priceCandidates) {
      if (el && el.innerText) {
        const match = el.innerText.replace(/,/g, '').match(/\d+(\.\d+)?/);
        if (match) {
          price = parseFloat(match[0]);
          break;
        }
      }
    }

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
      title: title,
      price: price,
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
        <span>กำลังดึงข้อมูลจริง...</span>
      `;

      // Trigger video play if on page to ensure video URL loads
      const videoThumb = document.querySelector('[class*="video"], [class*="play"]');
      if (videoThumb) {
        try { videoThumb.click(); } catch(e) {}
      }

      setTimeout(() => {
        const data = extractProductData();
        console.log('📦 Extracted Product Data for 9:16 Video:', data);

        // Store in Chrome storage for popup / factory sync
        if (chrome && chrome.storage && chrome.storage.local) {
          chrome.storage.local.set({ last_extracted_product: data });
        }

        // Open Shopee Video Factory with payload
        const payload = encodeURIComponent(JSON.stringify(data));
        const targetUrl = `${FACTORY_URL}/#import=${payload}`;
        
        window.open(targetUrl, '_blank');

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
        }, 3000);
      }, 500);
    });
  }

  // 3. LISTEN TO MESSAGES FROM POPUP
  if (chrome && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action === 'extract_product') {
        const data = extractProductData();
        sendResponse(data);
      }
      return true;
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
