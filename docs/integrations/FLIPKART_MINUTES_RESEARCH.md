# Flipkart Minutes Research

## 1. Current Flipkart Architecture
Flipkart Minutes is integrated directly into the broader Flipkart ecosystem, primarily operating as a mobile-first quick commerce experience. It leverages hyper-local dark stores to fulfill orders in 10-30 minutes. The service does not maintain a separate, public-facing web product URL structure for individual items (like a traditional e-commerce SEO page). Instead, inventory, pricing, and availability are fetched dynamically through internal APIs tied heavily to the user's active session, geolocation (pincode), and app tokens.

## 2. URL Types Tested
- Standard web URLs (e.g., `https://www.flipkart.com/maggi-2-minute-masala-noodles-vegetarian/p/itm0a2ed56502396`)
- Short URLs (e.g., `dl.flipkart.com/...`)

## 3. URL Classification Logic
Standard web URLs use the `flipkart.com/.../p/[ProductID]` format. However, Flipkart Minutes items do not typically have a unique web-facing URL structure; they are dynamically badged and served within the Flipkart app's "Minutes" UI layer.

## 4. Normal Flipkart vs Minutes Identification
Because there is no distinct web URL structure, identifying a product as a "Minutes" product requires intercepting the API response payload which contains the fulfillment SLA (e.g., `hyperlocal`, `10_MINUTES`, etc.) or checking the UI badges via browser automation.

## 5. Product Identifiers Discovered
Flipkart uses an alphanumeric Product ID (e.g., `itm0a2ed56502396`). 

## 6. Pincode/Location Requirements
Minutes delivery is strictly geo-fenced. The APIs require a valid pincode and often a geolocation header/cookie to map the user to the nearest active dark store.

## 7. Requests & Responses Observed
Direct HTTP GET requests to standard Flipkart product URLs (using `httpx` or `curl`) are immediately intercepted by Flipkart's Web Application Firewall (WAF) and reCAPTCHA Enterprise.

Example response:
```html
<!DOCTYPE html><html lang=en>...<title>Flipkart reCAPTCHA</title>...<h1 class=header>Are you a human?</h1>...
```

## 8. Required Headers/Cookies/Session State
Bypassing the reCAPTCHA wall requires legitimate browser fingerprinting, established session cookies (often generated via the mobile app), and potentially solving the reCAPTCHA challenge.

## 9. Availability, ETA, and Store Detection
Because the initial web request is blocked by anti-bot protections, it is not possible to reliably extract availability, ETA, or store fulfillment information without deploying aggressive bot-evasion techniques.

## 10. Failure Cases & Reliability Concerns
- **reCAPTCHA Blocking:** Every automated HTTP request without a valid session is blocked by a reCAPTCHA challenge.
- **Mobile-First API:** The Flipkart Minutes data is exposed primarily through private mobile APIs, which require reverse-engineering authentication mechanisms.
- **High Fragility:** Any workaround (like Playwright stealth plugins or API spoofing) would be extremely fragile and violate the project's strict anti-bot bypassing rules.

## 11. Recommended Implementation Strategy
**Outcome:** RELIABLE IMPLEMENTATION NOT POSSIBLE

Due to Flipkart's aggressive use of reCAPTCHA Enterprise on standard web requests and the mobile-centric nature of the Minutes platform, a reliable, robust integration is not possible without violating the project's strict rules against bypassing anti-bot protections and CAPTCHAs. 

Attempting to force an integration via Playwright would lead to frequent CAPTCHA blocks, high memory consumption, and a degraded user experience. Attempting to reverse-engineer the private mobile APIs would require inventing/guessing undocumented headers and authentication flows.

## 12. Future Approach
If Flipkart releases a public API or a dedicated, accessible web frontend for Minutes (similar to Blinkit or Zepto), the integration can be revisited. Alternatively, if the CartRadar platform introduces a legitimate partnership or official API access with Flipkart, the integration can be built safely. Until then, the existing scaffold (`flipkart.py`) will remain disabled.
