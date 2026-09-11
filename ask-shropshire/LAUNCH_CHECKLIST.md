# Ask Shropshire launch checklist

Last reviewed: 11 September 2026

## Current build state

The Shropshire beta is feature-complete enough for public testing. The current web/PWA source lives under `ask-shropshire/app/` on the `ask-shropshire-data` branch.

Built and checked:
- Home / Explore / Family / Saved / More shell
- Family Day Finder with date, desired time, ages, budget, travel radius and accessibility preference
- Weather-aware ranking using Open-Meteo
- Structured opening-hours logic that does not guess unknown hours
- Road distance / drive-time estimates using OSRM where available
- Leaflet/OpenStreetMap interactive map and route drawing
- Saved items in browser storage
- PWA manifest, install icons, service worker and offline app shell
- Deals & Offers page with sponsored labels and automatic expiry workflow
- Submit Event, Claim Business, Update Business, Alerts and Submit Offer forms
- Jotform -> private Airtable intake with Jotform submission-ID deduplication
- Approved-submission moderation workflow
- Business-claim verification gate
- Alert digest / important-change / unsubscribe workflows
- Shareable family plans, WhatsApp sharing, copy-link and calendar `.ics` export
- Follow-up refinements such as closer, cheaper, free, indoors, less walking, no booking, later/earlier and weekend
- Search-gap feedback form and private Search Analytics review workflow
- Privacy and accessibility pages
- No Airtable credentials or private admin tokens embedded in the public client
- QA submissions for Event / Claim / Alert / Offer / Listing Update reached the intended private Airtable queues; QA records were rejected/disabled after proof

## Before public production launch

### 1. Hosting and domain
- [ ] Put the latest `ask-shropshire/app/` build on permanent HTTPS hosting.
- [ ] Connect the final Ask Shropshire domain/subdomain.
- [ ] Confirm `index.html`, manifest and service worker are served with correct MIME types.
- [ ] Confirm service worker scope is the app root.
- [ ] Confirm custom-domain redirects and `www`/non-`www` choice.
- [ ] Add a canonical URL / final social-sharing URL once the domain is known.

### 2. Automatic public-feed proof
- [ ] Observe at least one unattended 08:00 Europe/London Airtable -> GitHub feed sync complete successfully.
- [ ] Confirm `events.json`, `places.json`, `offers.json` and `tips.json` all update together.
- [ ] Confirm the Feed Sync Log contains the run, counts and commit URL.
- [ ] Confirm cancelled/expired/paused/rejected/private records are omitted.
- [ ] Confirm newly added coordinates and structured hours propagate to the public feed.

### 3. Real-user proof for public workflows
- [ ] One genuine event submission arrives in Submissions as `New`, is reviewed, approved and published without duplicate creation.
- [ ] One genuine business claim arrives as `New`, is manually verified and marks only the correct listing as claimed.
- [ ] One verified business-listing correction is approved and changes only explicitly supplied fields.
- [ ] One genuine alert signup with explicit consent is stored, receives a matching alert/digest and can unsubscribe successfully.
- [ ] One genuine offer is submitted as Draft, reviewed, published, appears on Deals, and becomes Expired after its end date.
- [ ] One missing-result report reaches private Search Analytics without copying the optional reply email into analytics.

### 4. Privacy / governance
- [ ] Add the final named data-controller/operator identity and contact details to `privacy.html`.
- [ ] Agree and publish a specific retention schedule for event/business submissions, claims, alerts, analytics and privacy requests.
- [ ] Confirm Jotform, Airtable and email-service use is covered by the production privacy notice.
- [ ] Define the process for access/correction/deletion/privacy requests received through the privacy form.
- [ ] Confirm public forms do not request passwords, payment details or unnecessary sensitive data.

### 5. Data quality
- [ ] Keep exact coordinates populated for published places wherever verified.
- [ ] Add structured `hours_json` only where regular hours are reliable; leave variable/seasonal venues as unknown rather than guessed.
- [ ] Review old events for cancellation/date changes before launch.
- [ ] Check featured listings and sponsored offers are clearly distinguished from factual ranking.
- [ ] Continue discovery across Telford, Ironbridge, Wellington, Newport, Shrewsbury, Bridgnorth, Ludlow, Market Drayton, Oswestry, Church Stretton, Ellesmere and surrounding villages.

### 6. Device / browser launch sweep
- [ ] Android Chrome: install prompt, offline reopen, share sheet, WhatsApp, map and geolocation permission.
- [ ] iPhone Safari: Add to Home Screen, safe-area layout, share sheet, calendar export and no horizontal overflow.
- [ ] Desktop Chrome/Edge/Safari: navigation, keyboard focus, map resize, forms and external links.
- [ ] Deny location permission and confirm manual area selection still works.
- [ ] Simulate failed weather/routing/feed requests and confirm neutral/fallback messaging rather than broken UI.
- [ ] Test a date beyond forecast range.
- [ ] Test a venue with known closed hours and a venue with unknown/variable hours.
- [ ] Test shared plan containing a listing later removed from the live feed.

### 7. Final release checks
- [ ] No `TEST`, `QA`, `DO NOT PUBLISH`, prototype or temporary-host wording visible in public content.
- [ ] No private Airtable table IDs, auth headers, tokens, contact emails or admin notes in the public feed/client.
- [ ] Public source links open correctly.
- [ ] Sponsored offers visibly show `Sponsored`.
- [ ] Accessibility statement and privacy page are reachable from the app.
- [ ] Final production URL added to PWA/share metadata where appropriate.

## Known hosting blocker

ShipStatic has been returning connection/errors during the latest deployment attempt. Do not treat that as an app-code failure. Vercel previously had no usable team/workspace on the connected account. Continue from this checklist when a stable hosting route is available.
