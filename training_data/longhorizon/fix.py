from pathlib import Path

path = Path(r"C:\Data\training_data\longhorizon\batch_0001.txt")
s = path.read_text(encoding="utf-8")
edits = [
    # C4
    ("Measure that rather than assuming it is free.", "Measure it."),
    ("The sweep only touches historical rows, since the app dual-writes. Run it off-peak; if it is too large, repeat with `LIMIT` until zero nulls.",
     "The sweep only touches historical rows. Run it off-peak; if too large, repeat with `LIMIT` until zero nulls."),
    # C6 A3
    ("If the first transaction rolls back, the second proceeds and processes the event. That is exactly the behavior you want. Keep the handler transaction short; do not call Stripe or SES inside it, or the lock is held for the network round trip.",
     "If the first transaction rolls back, the second proceeds. Keep the handler transaction short; do not call Stripe or SES inside it."),
    ("Write an admin script that inserts a new outbox row with an explicit `reason = 'manual_replay'` and an audit record. Reusing the original event id must remain a no-op forever.",
     "Write an admin script that inserts a new outbox row and an audit record. Reusing the original event id must remain a no-op forever."),
    # C6 A5
    ("For a refund that arrives first, record it, leave the order pending, and when the checkout event arrives at `paid`, immediately apply the stored refund. Simpler and more robust: on any event that conflicts with local state, call `stripe.checkout.sessions.retrieve` or `stripe.paymentIntents.retrieve` and reconcile to Stripe's current object, because Stripe is the source of truth. Use the event only as a trigger, not as the final state.",
     "For a refund that arrives first, record it and leave the order pending. On any event that conflicts with local state, call `stripe.checkout.sessions.retrieve` or `stripe.paymentIntents.retrieve` and reconcile to Stripe's current object. Use the event as a trigger, not as the final state."),
    ("Loyalty points must be keyed by order and reason, as in the schema above; a second `payment_intent.succeeded` cannot insert a second ledger row for the same purchase.",
     "Loyalty points are keyed by order and reason, so a second `payment_intent.succeeded` cannot insert a second ledger row."),
]
for a, b in edits:
    if a not in s:
        raise SystemExit("missing: " + a[:90])
    s = s.replace(a, b, 1)
path.write_text(s, encoding="utf-8", newline="\n")
print("ok", len(s))
