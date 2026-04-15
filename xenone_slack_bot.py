"""
Xenone Slack Bot - Complete Implementation
Team Xenone | Ideathon April 2026

All 6 features ported from Discord version:
1. 📌 Emoji reaction to capture messages
2. /ask command for AI-powered Q&A with confidence scoring
3. /exit_brief command to generate handoff summary
4. 🏷️ Auto-tagging: Automatically categorize messages
5. 📊 Analytics Dashboard: Most-asked questions, knowledge gaps
6. 📄 Export to PDF: Generate actual downloadable PDF file

Setup:
1. pip install slack-bolt slack-sdk
2. Create .env with SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET
3. Run: python xenone_slack_bot.py
"""

import os
import re
import io
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
import chromadb
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from datetime import datetime
from collections import Counter
from fpdf import FPDF

load_dotenv()

SLACK_BOT_TOKEN      = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN      = os.getenv("SLACK_APP_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

app    = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
client = WebClient(token=SLACK_BOT_TOKEN)

# Global AI + DB state
model       = None
tokenizer   = None
chroma_client = None
collection  = None

# =============================================================================
# FEATURE 4: Auto-tagging
# =============================================================================

TAG_RULES = {
    "decision": [
        r"\bwe (decided|agreed|chose|voted|confirmed|finalized)\b",
        r"\bdecision\b", r"\bfinal call\b", r"\bgo with\b", r"\bapproved\b",
        r"\bshipping\b", r"\bwill use\b", r"\bgoing forward\b"
    ],
    "lesson": [
        r"\blearned\b", r"\blessons?\b", r"\bretro\b", r"\bretrospective\b",
        r"\bnext time\b", r"\bimprovement\b", r"\bshouldve\b", r"\bshould have\b",
        r"\bmistake\b", r"\btakeaway\b", r"\binsight\b"
    ],
    "warning": [
        r"\bwarning\b", r"\bcareful\b", r"\bdo(n'?t| not)\b", r"\bavoid\b",
        r"\bdanger\b", r"\bbug\b", r"\bbreaks?\b", r"\brisk\b", r"\bissue\b",
        r"\bproblem\b", r"\bfail\b", r"\bcrash\b", r"\bdeprecated\b"
    ],
    "action": [
        r"\btodo\b", r"\bto-do\b", r"\bassigned to\b", r"\bowner\b",
        r"\bfollow.?up\b", r"\baction item\b", r"\bneed to\b", r"\bmust\b",
        r"\bplease (do|fix|add|remove|update|check)\b"
    ],
    "question": [
        r"\bwhy\b.*\?", r"\bhow\b.*\?", r"\bwhat\b.*\?", r"\bwhen\b.*\?",
        r"\bwhere\b.*\?", r"\bwho\b.*\?", r"\bcan (we|you|someone)\b",
        r"\?\s*$"
    ],
}

TAG_EMOJIS = {
    "decision": "✅",
    "lesson":   "💡",
    "warning":  "⚠️",
    "action":   "🎯",
    "question": "❓",
    "general":  "📌",
}

def auto_tag(text: str) -> list:
    text_lower = text.lower()
    matched = []
    for tag, patterns in TAG_RULES.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                matched.append(tag)
                break
    return matched if matched else ["general"]


# =============================================================================
# FEATURE 5: Analytics tracking
# =============================================================================

analytics_store = {}

def record_question(team_id: str, question: str, answered: bool):
    store = analytics_store.setdefault(team_id, {"questions": [], "unanswered": []})
    store["questions"].append(question.lower().strip())
    if not answered:
        store["unanswered"].append(question.lower().strip())


# =============================================================================
# FEATURE 6: PDF generation
# =============================================================================

def build_pdf(team_name: str, all_results: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, "Xenone Exit Brief", ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Workspace: {team_name}", ln=True, align="C")
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
    pdf.ln(8)

    documents = all_results.get("documents", [])
    metadatas = all_results.get("metadatas", [])
    total     = len(documents)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Total messages captured: {total}", ln=True)

    authors = set(m.get("author", "Unknown") for m in metadatas)
    pdf.cell(0, 7, f"Unique contributors: {len(authors)}", ln=True)

    timestamps = sorted(m.get("timestamp", "")[:10] for m in metadatas if m.get("timestamp"))
    if timestamps:
        pdf.cell(0, 7, f"Date range: {timestamps[0]}  to  {timestamps[-1]}", ln=True)
    pdf.ln(6)

    tag_counter = Counter()
    for m in metadatas:
        for t in m.get("tags", "general").split(","):
            tag_counter[t.strip()] += 1

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Knowledge by Category", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for tag, count in tag_counter.most_common():
        pdf.cell(0, 7, f"  [{tag.upper()}]: {count} messages", ln=True)
    pdf.ln(6)

    grouped = {}
    for doc, meta in zip(documents, metadatas):
        for tag in meta.get("tags", "general").split(","):
            tag = tag.strip()
            grouped.setdefault(tag, []).append((doc, meta))

    for tag, items in grouped.items():
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, f"[{tag.upper()}] ({len(items)} messages)", ln=True)
        pdf.set_font("Helvetica", "", 10)

        for doc, meta in items:
            author  = meta.get("author",    "Unknown")
            channel = meta.get("channel",   "Unknown")
            ts      = meta.get("timestamp", "")[:10]

            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, f"{author}  |  #{channel}  |  {ts}", ln=True)

            body = doc[:400] + ("..." if len(doc) > 400 else "")
            body = body.encode("latin-1", errors="replace").decode("latin-1")
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, body)
            pdf.ln(3)
        pdf.ln(4)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, "Powered by Xenone  |  AI Knowledge Hub for Slack", ln=True, align="C")

    return bytes(pdf.output())


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize_ai():
    global model, tokenizer, chroma_client, collection
    print("🤖 Loading AI model...")
    model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    tokenizer  = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype=torch.float16, device_map="auto"
    )
    print("✓ AI model loaded")
    chroma_client = chromadb.Client()
    collection    = chroma_client.get_or_create_collection(name="xenone_slack")
    print("✓ Knowledge base ready")
    print("🚀 Xenone Slack Bot is online!\n")


def generate_ai_response(question, context):
    prompt = (
        f"You are Xenone, a knowledge assistant.\n\n"
        f"Based on these captured messages:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer briefly using ONLY the information above:"
    )
    inputs  = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs, max_length=300, temperature=0.7,
        do_sample=True, pad_token_id=tokenizer.eos_token_id
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if "Answer briefly" in response:
        answer = response.split("Answer briefly")[-1].strip()
        if answer.startswith(":"):
            answer = answer[1:].strip()
        return answer
    return response


# =============================================================================
# FEATURE 1: 📌 Reaction Capture
# =============================================================================

@app.event("reaction_added")
def handle_reaction(event, say):
    if event.get("reaction") != "pushpin":   # pushpin = 📌 in Slack
        return

    item     = event.get("item", {})
    if item.get("type") != "message":
        return

    channel_id = item.get("channel")
    ts         = item.get("ts")
    user_id    = event.get("user")

    try:
        result  = client.conversations_history(channel=channel_id, latest=ts, limit=1, inclusive=True)
        messages = result.get("messages", [])
        if not messages:
            return

        message      = messages[0]
        message_text = message.get("text", "").strip()
        author_id    = message.get("user", "Unknown")

        if not message_text or author_id == "USLACKBOT":
            return

        # Get author display name
        try:
            user_info   = client.users_info(user=author_id)
            author_name = user_info["user"]["real_name"]
        except Exception:
            author_name = author_id

        # Get channel name
        try:
            ch_info      = client.conversations_info(channel=channel_id)
            channel_name = ch_info["channel"]["name"]
        except Exception:
            channel_name = channel_id

        # Get team name
        try:
            team_info = client.team_info()
            team_id   = team_info["team"]["id"]
            team_name = team_info["team"]["name"]
        except Exception:
            team_id   = "unknown"
            team_name = "Unknown Workspace"

        msg_id   = f"{team_id}_{channel_id}_{ts}"
        tags     = auto_tag(message_text)
        tags_str = ",".join(tags)

        collection.add(
            documents=[message_text],
            metadatas=[{
                "author":    author_name,
                "channel":   channel_name,
                "timestamp": datetime.now().isoformat(),
                "team_id":   team_id,
                "tags":      tags_str,
            }],
            ids=[msg_id]
        )

        tag_badges = "  ".join(f"{TAG_EMOJIS.get(t, '📌')} `{t}`" for t in tags)

        say(
            channel=channel_id,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"✅ *Saved to Knowledge Base!*\n"
                            f"Message captured by <@{user_id}>\n\n"
                            f"*📝 Content:*\n>{message_text[:200]}{'...' if len(message_text) > 200 else ''}\n\n"
                            f"*👤 Author:* <@{author_id}>   *📅 Date:* {datetime.now().strftime('%Y-%m-%d')}\n"
                            f"*🏷️ Auto-Tags:* {tag_badges}\n\n"
                            f"_Use `/ask` to query this knowledge later_"
                        )
                    }
                }
            ]
        )
        print(f"✓ Captured [{tags_str}] from {author_name} in #{channel_name}")

    except Exception as e:
        print(f"Error capturing message: {e}")
        say(channel=channel_id, text="❌ Failed to capture message.")


# =============================================================================
# FEATURE 2: /ask — AI Q&A
# =============================================================================

@app.command("/ask")
def handle_ask(ack, respond, command):
    ack()
    question = command.get("text", "").strip()
    team_id  = command.get("team_id", "unknown")

    if not question:
        respond("❌ Please provide a question. Usage: `/ask why did we choose vendor X?`")
        return

    respond({"text": "🤔 Searching knowledge base...", "response_type": "ephemeral"})

    try:
        results     = collection.query(
            query_texts=[question], n_results=5,
            where={"team_id": team_id}
        )
        num_sources = len(results["documents"][0]) if results["documents"][0] else 0

        if num_sources >= 3:
            confidence = "🟢 HIGH CONFIDENCE"
        elif num_sources >= 1:
            confidence = "🟡 MEDIUM CONFIDENCE"
        else:
            confidence = "🔴 LOW CONFIDENCE"

        record_question(team_id, question, num_sources > 0)

        if num_sources > 0:
            context   = "\n".join(f"- {doc}" for doc in results["documents"][0])
            ai_answer = generate_ai_response(question, context)

            sources_text = ""
            for i, meta in enumerate(results["metadatas"][0][:3], 1):
                author   = meta.get("author",    "Unknown")
                channel  = meta.get("channel",   "Unknown")
                date     = meta.get("timestamp", "")[:10]
                tags     = meta.get("tags",      "general")
                badges   = " ".join(f"{TAG_EMOJIS.get(t.strip(),'📌')} `{t.strip()}`" for t in tags.split(","))
                sources_text += f"{i}. *{author}* in #{channel} on {date}  {badges}\n"

            respond({
                "response_type": "in_channel",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*💬 Q: {question[:100]}*\n\n"
                                f"{ai_answer[:2000]}\n\n"
                                f"*📊 Confidence:* {confidence} ({num_sources} sources)\n\n"
                                f"*📎 Sources:*\n{sources_text}"
                                f"\n_React with 📌 to important messages to improve my knowledge!_"
                            )
                        }
                    }
                ]
            })
        else:
            respond({
                "response_type": "in_channel",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*💬 Q: {question[:100]}*\n\n"
                                f"❌ *No information found in knowledge base.*\n"
                                f"React with 📌 to relevant messages to fill this gap!\n\n"
                                f"*📊 Confidence:* {confidence} (0 sources)"
                            )
                        }
                    }
                ]
            })

    except Exception as e:
        print(f"Error in /ask: {e}")
        respond("❌ An error occurred. Please try again.")


# =============================================================================
# FEATURE 3: /exit_brief
# =============================================================================

@app.command("/exit_brief")
def handle_exit_brief(ack, respond, command):
    ack()
    team_id = command.get("team_id", "unknown")

    try:
        all_results    = collection.get(where={"team_id": team_id})
        total_messages = len(all_results["ids"]) if all_results["ids"] else 0

        if total_messages == 0:
            respond("❌ No knowledge captured yet! React with 📌 to messages first.")
            return

        authors = set(m.get("author", "Unknown") for m in all_results["metadatas"])

        timestamps = [m.get("timestamp", "") for m in all_results["metadatas"] if m.get("timestamp")]
        dates      = sorted([t[:10] for t in timestamps if t])
        date_range = f"{dates[0]} to {dates[-1]}" if dates else "N/A"

        tag_counter = Counter()
        for meta in all_results["metadatas"]:
            for t in meta.get("tags", "general").split(","):
                tag_counter[t.strip()] += 1
        tag_summary = "\n".join(
            f"{TAG_EMOJIS.get(t,'📌')} *{t.capitalize()}*: {c}" for t, c in tag_counter.most_common()
        )

        sample_text = "\n\n".join(
            f"*{i+1}.* {doc[:100]}..." for i, doc in enumerate(all_results["documents"][:5])
        )

        respond({
            "response_type": "in_channel",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*📄 Exit Brief*\n\n"
                            f"*📊 Total Messages:* {total_messages}\n"
                            f"*👥 Contributors:* {len(authors)} members\n"
                            f"*📅 Date Range:* {date_range}\n\n"
                            f"*🏷️ By Category:*\n{tag_summary}\n\n"
                            f"*📌 Sample Knowledge:*\n{sample_text[:1000]}\n\n"
                            f"_Use `/export_pdf` to download the full PDF_"
                        )
                    }
                }
            ]
        })

    except Exception as e:
        print(f"Error in /exit_brief: {e}")
        respond("❌ An error occurred.")


# =============================================================================
# FEATURE 5: /analytics
# =============================================================================

@app.command("/analytics")
def handle_analytics(ack, respond, command):
    ack()
    team_id = command.get("team_id", "unknown")
    store   = analytics_store.get(team_id, {"questions": [], "unanswered": []})
    all_qs  = store["questions"]
    gaps    = store["unanswered"]

    # Top questions
    top_text = "No questions recorded yet."
    if all_qs:
        top      = Counter(all_qs).most_common(5)
        top_text = "\n".join(
            f"*{i+1}.* {q[:80]}{'...' if len(q)>80 else ''}  ×{c}"
            for i, (q, c) in enumerate(top)
        )

    # Knowledge gaps
    gap_text = "✅ No unanswered questions — great coverage!"
    if gaps:
        gap_top  = Counter(gaps).most_common(5)
        gap_text = "\n".join(
            f"*{i+1}.* {q[:80]}{'...' if len(q)>80 else ''}  ×{c}"
            for i, (q, c) in enumerate(gap_top)
        )

    # Tag bar chart
    bar_text = ""
    try:
        all_results = collection.get(where={"team_id": team_id})
        tag_counter = Counter()
        for meta in all_results.get("metadatas", []):
            for t in meta.get("tags", "general").split(","):
                tag_counter[t.strip()] += 1
        if tag_counter:
            total = sum(tag_counter.values())
            for tag, count in tag_counter.most_common():
                pct      = int(count / total * 20)
                bar      = "█" * pct + "░" * (20 - pct)
                emoji    = TAG_EMOJIS.get(tag, "📌")
                bar_text += f"{emoji} `{tag:<10}` {bar}  {count}\n"
    except Exception:
        pass

    respond({
        "response_type": "in_channel",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*📊 Xenone Analytics Dashboard*\n\n"
                        f"*🔥 Most-Asked Questions:*\n{top_text}\n\n"
                        f"*⚠️ Knowledge Gaps:*\n{gap_text}\n\n"
                        f"*🏷️ Knowledge by Tag:*\n{bar_text or 'No data yet.'}\n\n"
                        f"*📈 Totals:* {len(all_qs)} questions asked  |  {len(gaps)} unanswered"
                    )
                }
            }
        ]
    })


# =============================================================================
# FEATURE 6: /export_pdf
# =============================================================================

@app.command("/export_pdf")
def handle_export_pdf(ack, respond, command):
    ack()
    team_id    = command.get("team_id",    "unknown")
    channel_id = command.get("channel_id", "")

    try:
        all_results    = collection.get(where={"team_id": team_id})
        total_messages = len(all_results.get("ids", []))

        if total_messages == 0:
            respond("❌ No knowledge captured yet! React with 📌 first.")
            return

        try:
            team_info = client.team_info()
            team_name = team_info["team"]["name"]
        except Exception:
            team_name = "Your Workspace"

        pdf_bytes = build_pdf(team_name, {
            "documents": all_results.get("documents", []),
            "metadatas": all_results.get("metadatas", []),
        })

        filename = (
            f"xenone_exit_brief_"
            f"{team_name.replace(' ', '_')}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        )

        client.files_upload_v2(
            channel=channel_id,
            content=pdf_bytes,
            filename=filename,
            title=f"Xenone Exit Brief — {team_name}",
            initial_comment=(
                f"📄 *PDF Export Ready*\n"
                f"Exit brief for *{team_name}* — {total_messages} messages captured."
            )
        )
        print(f"✓ PDF exported for {team_name} ({total_messages} messages)")

    except Exception as e:
        print(f"Error exporting PDF: {e}")
        respond("❌ Failed to generate PDF. Please try again.")


# =============================================================================
# /stats and /help
# =============================================================================

@app.command("/xenone_stats")
def handle_stats(ack, respond, command):
    ack()
    team_id = command.get("team_id", "unknown")

    try:
        all_results    = collection.get(where={"team_id": team_id})
        total_messages = len(all_results["ids"]) if all_results["ids"] else 0

        authors  = set(m.get("author",  "Unknown") for m in all_results["metadatas"]) if total_messages > 0 else set()
        channels = set(m.get("channel", "Unknown") for m in all_results["metadatas"]) if total_messages > 0 else set()

        respond({
            "response_type": "in_channel",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*📊 Xenone Knowledge Base Stats*\n\n"
                            f"*📌 Messages Captured:* {total_messages}\n"
                            f"*👥 Contributors:* {len(authors)}\n"
                            f"*💬 Active Channels:* {len(channels)}\n\n"
                            f"*🤖 Commands:*\n"
                            f"• `/ask [question]` — Query knowledge\n"
                            f"• `/exit_brief` — Discord summary\n"
                            f"• `/export_pdf` — Download PDF\n"
                            f"• `/analytics` — Analytics dashboard\n"
                            f"• `/xenone_stats` — Statistics\n"
                            f"• React 📌 to save messages"
                        )
                    }
                }
            ]
        })
    except Exception as e:
        print(f"Error in /xenone_stats: {e}")
        respond("❌ Error retrieving statistics.")


@app.command("/xenone_help")
def handle_help(ack, respond):
    ack()
    respond({
        "response_type": "ephemeral",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*📚 Xenone Bot — How to Use*\n"
                        "_AI-powered knowledge management for your Slack workspace_\n\n"
                        "*1️⃣ Capture Knowledge (📌 Reaction)*\n"
                        "React to any message with :pushpin:\n"
                        "Xenone saves it and auto-tags it:\n"
                        "✅ Decision  •  💡 Lesson  •  ⚠️ Warning  •  🎯 Action  •  ❓ Question\n\n"
                        "*2️⃣ Query Knowledge (/ask)*\n"
                        "`/ask what was our marketing budget?`\n\n"
                        "*3️⃣ Discord Summary (/exit_brief)*\n"
                        "Rich summary with stats and category breakdown.\n\n"
                        "*4️⃣ Download PDF (/export_pdf)*\n"
                        "Generates a real PDF — perfect for handoffs.\n\n"
                        "*5️⃣ Analytics (/analytics)*\n"
                        "Most-asked questions and knowledge gaps.\n\n"
                        "_Built for Ideathon April 2026 | Team Xenone_"
                    )
                }
            }
        ]
    })


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    missing = [v for v in ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "SLACK_SIGNING_SECRET"] if not os.getenv(v)]
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("Please add them to your .env file.")
    else:
        print("🚀 Starting Xenone Slack Bot...")
        initialize_ai()
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
