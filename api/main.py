from fastapi import FastAPI, HTTPException, Header, Depends, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import os
import threading

from database import (
    init_db, upsert_decisions, get_decision, get_db_status, 
    get_all_decisions, add_subscription, get_pending_subscriptions_with_decisions, get_all_subscriptions,
    mark_subscription_notified
)
from scraper import run_scraper
from notifier import send_notification_email

app = FastAPI(title="Visa Tracker API")

API_TOKEN = os.getenv("API_TOKEN", "supersecrettoken123")
CRON_SECRET = os.getenv("CRON_SECRET", "") 

# Pydantic models for request bodies
class SubscribeRequest(BaseModel):
    irl_number: str
    email: str

def perform_background_sync():
    """Runs a full sync in a background thread."""
    print("Initiating automatic background sync (Empty Database Detected)...")
    try:
        result = run_scraper()
        if result["success"]:
            upsert_decisions(result["data"])
            process_notifications()
            print(f"Background sync complete. Added {len(result['data'])} records.")
        else:
            print(f"Background sync failed: {result.get('error')}")
    except Exception as e:
        print(f"Background sync exception: {e}")

@app.on_event("startup")
def startup_event():
    init_db()

def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")
    x_token = request.headers.get("x-token")
    
    if x_token == API_TOKEN:
        return True
    if CRON_SECRET and auth_header == f"Bearer {CRON_SECRET}":
        return True
        
    raise HTTPException(status_code=401, detail="Unauthorized API Access")

# ---- Notification Processor ----
def process_notifications():
    pending_subs = get_pending_subscriptions_with_decisions()
    notified_count = 0
    
    for sub in pending_subs:
        sent = send_notification_email(
            to_email=sub['email'], 
            irl_number=sub['irl_number'], 
            status=sub['status'], 
            decision_date=sub['decision_date']
        )
        # We mark as notified if email was successfully sent, 
        # or if SMTP is simply not configured (to prevent infinite loops in dev without credentials).
        if sent or not os.getenv("SMTP_USER"): 
            mark_subscription_notified(sub['id'])
            notified_count += 1
            
    return notified_count

# ---- API Endpoints ----

@app.get("/api/status")
def api_status():
    db_stats = get_db_status()
    return {
        "last_sync": db_stats["last_sync"],
        "total_records": db_stats["total_records"],
        "latest_ods_link": "https://www.ireland.ie/en/india/newdelhi/services/visas/processing-times-and-decisions/#visa-decisions"
    }

@app.get("/api/check/{irl_number}")
def api_check(irl_number: str):
    # Vercel Serverless Self-Healing: Check if DB is completely empty before searching
    stats = get_db_status()
    if stats["total_records"] == 0:
        print("Empty database detected during search. Running blocking sync...")
        result = run_scraper()
        if result["success"]:
            upsert_decisions(result["data"])
        else:
            raise HTTPException(status_code=500, detail="Database is empty and automatic sync failed.")
            
    sanitized_irl = irl_number.strip().upper()
    if not sanitized_irl.startswith("IRL"):
        clean_num = ''.join(e for e in sanitized_irl if e.isalnum())
        sanitized_irl = f"IRL{clean_num}"
            
    result = get_decision(sanitized_irl)
    return result

@app.post("/api/subscribe")
def api_subscribe(req: SubscribeRequest):
    sanitized_irl = req.irl_number.strip().upper()
    if not sanitized_irl.startswith("IRL"):
        clean_num = ''.join(e for e in sanitized_irl if e.isalnum())
        sanitized_irl = f"IRL{clean_num}"
        
    # Check if the decision is already published
    decision = get_decision(sanitized_irl)
    
    if decision["found"]:
        # Check if SMTP is configured before trying
        if not os.getenv("SMTP_USER") or not os.getenv("SMTP_PASS"):
            raise HTTPException(status_code=500, detail="Server Error: Email (SMTP) environment variables are missing in Vercel.")
            
        # If already approved/refused, send the email IMMEDIATELY
        sent = send_notification_email(
            to_email=req.email.strip(),
            irl_number=sanitized_irl,
            status=decision["status"],
            decision_date=decision["date"]
        )
        
        if sent:
            return {"message": f"Success! A copy of this decision has been emailed to {req.email.strip()}."}
        else:
            raise HTTPException(status_code=500, detail="Failed to send email. Check Vercel logs for SMTP authentication errors.")
    else:
        # If pending, add to the database queue
        success = add_subscription(sanitized_irl, req.email.strip())
        
        if success:
            return {"message": "Success! You will receive an email as soon as the decision is published."}
        else:
            # Already subscribed
            return {"message": "You are already subscribed for updates on this reference number."}

@app.post("/api/force-sync", dependencies=[Depends(verify_token)])
@app.get("/api/force-sync", dependencies=[Depends(verify_token)])
def api_force_sync():
    result = run_scraper()
    
    if result["success"]:
        # Update DB with latest records
        upsert_decisions(result["data"])
        # Trigger email notification queue
        notified_count = process_notifications()
        
        return {
            "message": "Sync successful", 
            "records_processed": len(result["data"]),
            "notifications_sent": notified_count
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))

@app.get("/api/admin/records", dependencies=[Depends(verify_token)])
def api_admin_records():
    return get_all_decisions(limit=10000)

@app.get("/", response_class=HTMLResponse)
def read_root():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    try:
        with open(template_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<html><body><h1>UI not found.</h1></body></html>"

@app.get("/admin", response_class=HTMLResponse)
def read_admin():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "admin.html")
    try:
        with open(template_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<html><body><h1>Admin UI not found.</h1></body></html>"

if __name__ == "__main__":
    os.makedirs("api/templates", exist_ok=True)
    uvicorn.run("main:app", host="0.0.0.0", port=3000)

@app.get("/api/admin/subscriptions", dependencies=[Depends(verify_token)])
def api_admin_subscriptions():
    return get_all_subscriptions()
