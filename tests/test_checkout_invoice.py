from decimal import Decimal

from src.checkout_invoice import CheckoutInvoice, CheckoutItem, issue_checkout_invoice


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def post(self, path: str, payload: dict[str, object], operation_id: str) -> dict[str, str]:
        self.calls.append((path, payload))
        return {"message_id": "msg_1042"}


def test_checkout_total_and_customer_message_follow_the_paid_line_items() -> None:
    invoice = CheckoutInvoice(
        order_number="checkout-1042",
        customer_email="buyer@example.com",
        items=(CheckoutItem("Build event export", 3, Decimal("12.50")),),
    )
    client = RecordingClient()

    message_id = issue_checkout_invoice(invoice, client)  # type: ignore[arg-type]

    assert invoice.total == Decimal("37.50")
    assert message_id == "msg_1042"
    assert [path for path, _ in client.calls] == ["/v1/pdf/generate", "/v1/email/send"]
    assert "Checkout total: $37.50" in str(client.calls[1][1]["html"])
