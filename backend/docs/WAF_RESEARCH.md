# WAF & Data Extraction Limitations

During the development of the "Stock Finder" architecture and the integration of Swiggy and BigBasket, we experimented with multiple approaches to bypass anti-bot mechanisms. The goal was to replace dummy API calls with real product data extraction. This document logs the methods used and their outcomes to serve as a reference for future development.

## 1. HTTP/2 and Header Masquerading
- **Method:** Passing traditional `Mozilla Firefox` or `Google Chrome` headers using HTTP 1.1 / HTTP 2 clients (e.g., `httpx`, `curl`).
- **Result:** FAILED. 
- **Reason:** Akamai Bot Manager (BigBasket) and AWS WAF (Swiggy) proactively detect `httpx` and non-browser TLS fingerprints. Without solving invisible JavaScript challenges (e.g., reCAPTCHA v3 or proprietary WAF challenges) natively, direct programmatic API hits result in HTTP 403 Access Denied.

## 2. API "Golden" Endpoints
- **Method:** Exploring legacy, mobile-app-specific, or undocumented API endpoints (e.g., `/product/get-product-details/?pd_id=...` or Next.js `_rsc` endpoints) which sometimes have looser restrictions.
- **Result:** FAILED (mostly).
- **Reason:** For BigBasket, these endpoints have either been retired (redirect loops `302 \skip_explore`) or require strictly authenticated session cookies tied to a known residential region.

## 3. Headless Browser Automation (Playwright)
- **Method:** Implementing a headless Chromium scraper using Microsoft Playwright to implicitly evaluate JavaScript and solve basic bot challenges.
- **Result:** FAILED.
- **Reason:** Akamai Bot Manager detected the headless browser fingerprint (e.g., specific WebDriver signals, canvas rendering differences, and absence of stealth plugins) resulting in a direct Access Denied screen instead of the product view.

## 4. Mobile User-Agent Spoofing
- **Method:** Changing the User-Agent to match native applications, such as `Bigbasket-Android/8.0.5`.
- **Result:** PARTIAL SUCCESS.
- **Reason:** Android User-Agent successfully bypassed Akamai's initial perimeter on the BigBasket web frontend, returning HTTP 200 containing Next.js payload chunks. However, the exact dynamic product JSON data is deferred to asynchronous API requests rather than embedded cleanly in the RSC structure. Retrieving the prices still falls back to API restrictions.

## 5. Search Engine Crawler Spoofing 
- **Method:** Changing the User-Agent to `Googlebot` to exploit SEO-whitelisted paths.
- **Result:** **SUCCESS** for Swiggy Instamart!
- **Reason:** Swiggy's AWS WAF rules explicitly whitelist Googlebot to ensure products remain SEO-indexable. This returns a fully hydrated DOM containing `window.___INITIAL_STATE___` loaded with real-time variation blocks and local inventory levels! We use this method successfully today.

## Conclusion 
Any future attempts to expand BigBasket data functionally (outside of `DEV_MODE`) unequivocally require a high-quality, geographically distributed, rotating residential proxy pool (`PROXY_URL`) configured via the backend to prevent active IP reputation flagging by Akamai.
