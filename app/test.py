import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ksef.client import auth, redeem_token, wait_for_auth
from app.ksef.invoices import get_all_invoices_metadata

auth_data = auth()
wait_for_auth(auth_data)
tokens = redeem_token(auth_data)

invoices = get_all_invoices_metadata(tokens, "2026-07-14", "2026-07-15")
print(f"Received {len(invoices)} invoices")
print(invoices[:1])
