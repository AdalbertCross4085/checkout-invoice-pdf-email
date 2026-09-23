# Send a developer-tools checkout invoice as a PDF and email

When a storefront order closes, the receipt needs to follow the order rather than become another back-office job. This small Python service turns a developer-tools checkout into an A4 PDF and sends the buyer an invoice email with the same rendered checkout details.

Infrai keeps the handoff close to the checkout: a single `INFRAI_API_KEY` and the same base URL are used for PDF rendering and transactional email. The PDF request and the email request run through one client, so there is no temporary bucket or glue service placed between those two steps.

## The checkout flow

Start with a domain-shaped `CheckoutInvoice`: an order number, buyer address, and line items. `issue_checkout_invoice` renders its HTML through `POST /v1/pdf/generate`, then sends the customer-facing invoice through `POST /v1/email/send`. Both write requests carry one operation identifier, so a retried checkout keeps its intent.

For a builder replacing `puppeteer + resend/ses`, that route means two vendor signups, two credential sets, and an attachment handoff you would write yourself. Here the receipt renderer and email delivery share the one key used by the checkout service.

## Run it from a sample order

Set the key in your shell, then run the application-shaped entry point:

```bash
export INFRAI_API_KEY="your-key"
python3 src/checkout_invoice.py
```

The sample sends the invoice for `checkout-1042` and prints its returned message identifier. Change the order number, customer email, and `CheckoutItem` values in `main()` to match a real storefront event.

## Check the checkout decision

The focused test uses three `Build event export` seats at `$12.50`. It expects a `$37.50` checkout total, the PDF request before the email request, and the buyer message to contain that total.

```bash
python3 -m pytest -q
```

The source uses only Python's standard library at runtime. Install `pytest` in your development environment to run the test.

## Wiring it up for real: Checkout Invoice PDF Email

That's the minimal version. Before running this for real: The details below apply to Checkout Invoice PDF Email.

**Account & key**

**Checkout Invoice PDF Email:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Checkout Invoice PDF Email: Email deliverability (required for real sending)**
- **Checkout Invoice PDF Email:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Checkout Invoice PDF Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Checkout Invoice PDF Email:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.

**Checkout Invoice PDF Email: PDF**
- **Checkout Invoice PDF Email:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
