from fastapi import FastAPI

from app.routers.invoices import router as invoices_router

app = FastAPI(title="KSeF")
app.include_router(invoices_router)

