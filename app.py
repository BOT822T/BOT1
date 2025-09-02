from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd

app = Flask(__name__)

# === Put your OneDrive direct download link here ===
url = "https://docs.google.com/spreadsheets/d/1b1snHVRh6-PDPDJz_P3ba5ChvY6wvY34/export?format=xlsx"


def load_stock():
    """Load latest stock data from OneDrive Excel file"""
    try:
        df = pd.read_excel(url)
        # Normalize column names (in case of spaces or casing)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        print("Error loading Excel:", e)
        return None


@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    """Respond to WhatsApp messages with stock info"""
    incoming_msg = request.values.get("Body", "").strip()
    resp = MessagingResponse()
    msg = resp.message()

    if not incoming_msg:
        msg.body("⚠️ Please send a part number or description to check stock.")
        return str(resp)

    df = load_stock()
    if df is None:
        msg.body("❌ Could not load stock data. Please try again later.")
        return str(resp)

    # Search by Material or Description (case-insensitive)
    results = df[
        df["Material"].astype(str).str.contains(incoming_msg, case=False, na=False)
        | df["Material Description"].str.contains(incoming_msg, case=False, na=False)
    ]

    if results.empty:
        msg.body(f"❌ No stock found for: {incoming_msg}")
    else:
        reply_lines = []
        for _, row in results.iterrows():
            reply_lines.append(
                f"📦 {row['Material']} | {row['Material Description']}\n"
                f"🏭 {row['Storage Location']} → {row['Unrestricted']} units"
            )
        msg.body("\n\n".join(reply_lines[:5]))  # Limit to 5 matches

    return str(resp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

