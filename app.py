from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
from collections import defaultdict, deque

app = Flask(__name__)

# === Use Google Sheets CSV Export Link ===
url = "https://docs.google.com/spreadsheets/d/1b1snHVRh6-PDPDJz_P3ba5ChvY6wvY34/gviz/tq?tqx=out:csv"

# Store last 5 queries per user (user_id → deque of queries)
user_logs = defaultdict(lambda: deque(maxlen=5))


def load_stock():
    """Load latest stock data from Google Sheets CSV link"""
    try:
        df = pd.read_csv(url)
        # Normalize column names (in case of spaces or casing)
        df.columns = [c.strip() for c in df.columns]
        print(f"✅ Stock loaded: {df.shape[0]} rows")
        return df
    except Exception as e:
        print("❌ Error loading Excel:", e)
        return None


@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    """Respond to WhatsApp messages with stock info"""
    incoming_msg = request.values.get("Body", "").strip()
    user_id = request.values.get("From", "unknown")  # phone number acts as user ID
    print(f"📩 Incoming from {user_id}: {incoming_msg}")

    resp = MessagingResponse()
    msg = resp.message()

    if not incoming_msg:
        msg.body("⚠️ Please send a part number or description to check stock.")
        return str(resp)

    df = load_stock()
    if df is None:
        msg.body("❌ Could not load stock data (file link or permission issue).")
        return str(resp)

    # Search by Material or Description (case-insensitive)
    results = df[
        df["Material"].astype(str).str.contains(incoming_msg, case=False, na=False)
        | df["Material Description"].astype(str).str.contains(incoming_msg, case=False, na=False)
    ]

    if results.empty:
        reply_text = f"❌ No stock found for: {incoming_msg}"
    else:
        reply_lines = []
        for _, row in results.iterrows():
            reply_lines.append(
                f"📦 {row['Material']} | {row['Material Description']}\n"
                f"🏭 {row['Storage Location']} → {row['Unrestricted']} units"
            )
        reply_text = "\n\n".join(reply_lines[:5])  # Limit to 5 matches

    # Save this interaction in user log
    user_logs[user_id].append(f"🔎 {incoming_msg} → {reply_text[:80]}...")

    # Add history footer
    history = "\n".join(list(user_logs[user_id]))
    full_reply = f"{reply_text}\n\n🕑 Your last {len(user_logs[user_id])} queries:\n{history}"

    msg.body(full_reply)
    print("📤 Reply sent")
    return str(resp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
