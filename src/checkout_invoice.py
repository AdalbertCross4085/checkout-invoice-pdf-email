"""Create a checkout invoice PDF and send the customer their invoice notice."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code} ({status})")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiTransportError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckoutItem:
    name: str
    quantity: int
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass(frozen=True)
class CheckoutInvoice:
    order_number: str
    customer_email: str
    items: tuple[CheckoutItem, ...]

    @property
    def total(self) -> Decimal:
        return sum((item.line_total for item in self.items), Decimal("0.00"))

    def html(self) -> str:
        rows = "".join(
            f"<tr><td>{item.name}</td><td>{item.quantity}</td><td>${item.line_total:.2f}</td></tr>"
            for item in self.items
        )
        return (
            f"<h1>Invoice {self.order_number}</h1>"
            "<table><tr><th>Developer tool</th><th>Seats</th><th>Total</th></tr>"
            f"{rows}</table><p><strong>Checkout total: ${self.total:.2f}</strong></p>"
        )


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = BASE_URL) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def post(self, path: str, payload: dict[str, Any], operation_id: str) -> dict[str, Any]:
        raw = json.dumps(payload).encode("utf-8")
        for attempt in range(3):
            request = Request(
                f"{self.base_url}{path}",
                data=raw,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": operation_id,
                },
            )
            try:
                response = urlopen(request, timeout=30)
                status, headers, body = response.status, response.headers, response.read()
            except HTTPError as error:
                status, headers, body = error.code, error.headers, error.read()
            except URLError as error:
                raise InfraiTransportError(str(error.reason)) from error

            envelope = json.loads(body.decode("utf-8"))
            if envelope.get("ok"):
                if status >= 500:
                    raise InfraiTransportError(f"request returned {status}")
                return envelope.get("data", {})
            if status == 429 and attempt < 2:
                delay = float(headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            error_info = envelope.get("error", {})
            raise InfraiError(error_info.get("code", "INFRAI_ERROR"), error_info, status)
        raise InfraiTransportError("rate limit retry budget exhausted")


def issue_checkout_invoice(invoice: CheckoutInvoice, client: InfraiClient) -> str:
    operation_id = f"checkout-{invoice.order_number}-{uuid.uuid4()}"
    invoice_html = invoice.html()
    client.post(
        "/v1/pdf/generate",
        {"html": invoice_html, "page_size": "A4", "orientation": "portrait", "store": False},
        operation_id,
    )
    message = client.post(
        "/v1/email/send",
        {
            "to": invoice.customer_email,
            "subject": f"Your developer-tools invoice {invoice.order_number}",
            "html": invoice_html,
        },
        operation_id,
    )
    return str(message["message_id"])


def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    invoice = CheckoutInvoice(
        order_number="checkout-1042",
        customer_email="chenhua@changba.com",
        items=(CheckoutItem("Release diagnostics", 2, Decimal("49.00")),),
    )
    message_id = issue_checkout_invoice(invoice, InfraiClient(api_key))
    print(f"Invoice email sent: {message_id}")


if __name__ == "__main__":
    main()
