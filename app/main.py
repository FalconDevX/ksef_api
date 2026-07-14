from datetime import datetime, timedelta, timezone

from fastapi import FastAPI

from app.ksef.client import auth,redeem_token, get_all_invoices_metadata, wait_for_auth


app = FastAPI()

@app.post("/invoices/sync")
def sync_invoices():
    date_to = datetime.now(timezone.utc)
    date_from = date_to - timedelta(days=1)

    auth_data = auth()
    wait_for_auth(auth_data)

    tokens = redeem_token(auth_data)

    invoices = get_all_invoices_metadata(
        tokens=tokens,
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
    )

    return {
        "downloaded": len(invoices),
        "invoices": invoices,
    }