"""
Xenone Discord Bot - MVP
Team Xenone 

Features:
1. 📌 Emoji reaction to capture messages
2. /ask command for AI-powered Q&A with confidence scoring
3. /exit_brief command to generate handoff summary
4. 🏷️ Auto-tagging: Automatically categorize messages (decisions, lessons, warnings)
5. 📊 Analytics Dashboard: Most-asked questions, knowledge gaps
6. 📄 Export to PDF: Generate actual downloadable PDF file

"""

import os
import re
import io
import discord
from discord.ext import commands
from discord import app_commands
import chromadb
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from datetime import datetime
import asyncio
from collections import Counter
from fpdf import FPDF

# Load environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Global variables for AI model and database
model = None
tokenizer = None
chroma_client = None
collection = None

# =============================================================================
# FEATURE 4: Auto-tagging keyword rules
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
    """Return a list of tags that match the message content."""
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

# In-memory: {guild_id: {"questions": [...], "unanswered": [...]}}
analytics_store = {}


def record_question(guild_id: str, question: str, answered: bool):
    store = analytics_store.setdefault(guild_id, {"questions": [], "unanswered": []})
    store["questions"].append(question.lower().strip())
    if not answered:
        store["unanswered"].append(question.lower().strip())


# =============================================================================
# FEATURE 6: PDF generation helper
# =============================================================================

def build_pdf(guild_name: str, all_results: dict) -> bytes:
    """Build a full PDF from captured knowledge and return raw bytes."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Cover
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, "Xenone Exit Brief", ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Server: {guild_name}", ln=True, align="C")
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
    pdf.ln(8)

    documents = all_results.get("documents", [])
    metadatas = all_results.get("metadatas", [])
    total = len(documents)

    # Summary
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Total messages captured: {total}", ln=True)

    authors = set(m.get("author", "Unknown") for m in metadatas)
    pdf.cell(0, 7, f"Unique contributors: {len(authors)}", ln=True)

    timestamps = sorted(
        m.get("timestamp", "")[:10] for m in metadatas if m.get("timestamp")
    )
    if timestamps:
        pdf.cell(0, 7, f"Date range: {timestamps[0]}  to  {timestamps[-1]}", ln=True)
    pdf.ln(6)

    # Tag breakdown
    tag_counter = Counter()
    for m in metadatas:
        for t in m.get("tags", "general").split(","):
            tag_counter[t.strip()] += 1

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Knowledge by Category", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for tag, count in tag_counter.most_common():
        label = f"  [{tag.upper()}]: {count} messages"
        pdf.cell(0, 7, label, ln=True)
    pdf.ln(6)

    # Messages grouped by tag
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
            header = f"{author}  |  #{channel}  |  {ts}"
            pdf.cell(0, 6, header, ln=True)

            body = doc[:400] + ("..." if len(doc) > 400 else "")
            body = body.encode("latin-1", errors="replace").decode("latin-1")
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, body)
            pdf.ln(3)

        pdf.ln(4)

    # Footer
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, "Powered by Xenone  |  AI Knowledge Hub for Discord", ln=True, align="C")

    return bytes(pdf.output())


# =============================================================================
# INITIALIZATION
# =============================================================================

async def initialize_ai():
    """Load AI model and initialize ChromaDB"""
    global model, tokenizer, chroma_client, collection

    print("🤖 Loading AI model... (this takes 2-3 minutes)")

    model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    tokenizer  = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    print("✓ AI model loaded")

    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection    = chroma_client.get_or_create_collection(name="xenone_discord")
    print("✓ Knowledge base ready")
    print("🚀 Xenone Discord Bot is online!\n")


def generate_ai_response(question, context):
    prompt = (
        f"You are Xenone, a knowledge assistant for Discord servers.\n\n"
        f"Based on these captured messages:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer briefly using ONLY the information above:"
    )
    inputs  = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_length=300,
        temperature=0.7,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if "Answer briefly" in response:
        answer = response.split("Answer briefly")[-1].strip()
        if answer.startswith(":"):
            answer = answer[1:].strip()
        return answer
    return response


# =============================================================================
# BOT EVENTS
# =============================================================================

@bot.event
async def on_ready():
    print(f'✓ Logged in as {bot.user.name} (ID: {bot.user.id})')
    await initialize_ai()
    try:
        synced = await bot.tree.sync()
        print(f'✓ Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for 📌 reactions | /ask for help"
        )
    )


@bot.event
async def on_reaction_add(reaction, user):
    """
    FEATURE 1: Passive Capture
    FEATURE 4: Auto-tagging stored in ChromaDB metadata
    """
    if user.bot:
        return
    if str(reaction.emoji) != "📌":
        return

    message = reaction.message
    if not message.content or message.author.bot:
        return

    try:
        msg_id   = f"{message.guild.id}_{message.id}"
        tags     = auto_tag(message.content)          # FEATURE 4
        tags_str = ",".join(tags)

        collection.add(
            documents=[message.content],
            metadatas=[{
                "author":     str(message.author),
                "channel":    str(message.channel.name),
                "timestamp":  message.created_at.isoformat(),
                "message_id": str(message.id),
                "guild_id":   str(message.guild.id),
                "tags":       tags_str,               # ← FEATURE 4 field
            }],
            ids=[msg_id]
        )

        tag_badges = "  ".join(
            f"{TAG_EMOJIS.get(t, '📌')} `{t}`" for t in tags
        )

        embed = discord.Embed(
            title="✅ Saved to Knowledge Base!",
            description=f"Message captured by {user.mention}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📝 Content",
            value=message.content[:200] + ("..." if len(message.content) > 200 else ""),
            inline=False
        )
        embed.add_field(name="👤 Author",   value=message.author.mention, inline=True)
        embed.add_field(name="📅 Date",     value=message.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="🏷️ Auto-Tags", value=tag_badges, inline=False)  # FEATURE 4
        embed.set_footer(text="Use /ask to query this knowledge later")

        await message.reply(embed=embed, mention_author=False)
        print(f"✓ Captured [{tags_str}] from {message.author} in #{message.channel.name}")

    except Exception as e:
        print(f"Error capturing message: {e}")
        await message.reply("❌ Failed to capture message.", mention_author=False)


# =============================================================================
# SLASH COMMANDS
# =============================================================================

@bot.tree.command(name="ask", description="Ask Xenone a question based on captured knowledge")
@app_commands.describe(question="Your question about the server's history")
async def ask_command(interaction: discord.Interaction, question: str):
    """FEATURE 2 + FEATURE 5 analytics recording"""
    await interaction.response.defer(thinking=True)

    try:
        results     = collection.query(
            query_texts=[question],
            n_results=5,
            where={"guild_id": str(interaction.guild_id)}
        )
        num_sources = len(results['documents'][0]) if results['documents'][0] else 0

        if num_sources >= 3:
            confidence, confidence_color = "🟢 HIGH CONFIDENCE",   discord.Color.green()
        elif num_sources >= 1:
            confidence, confidence_color = "🟡 MEDIUM CONFIDENCE", discord.Color.gold()
        else:
            confidence, confidence_color = "🔴 LOW CONFIDENCE",    discord.Color.red()

        answered = num_sources > 0
        record_question(str(interaction.guild_id), question, answered)  # FEATURE 5

        if answered:
            context   = "\n".join(f"- {doc}" for doc in results['documents'][0])
            ai_answer = generate_ai_response(question, context)

            embed = discord.Embed(
                title=f"💬 Question: {question[:100]}",
                description=ai_answer[:2000],
                color=confidence_color
            )
            embed.add_field(name="📊 Confidence", value=f"{confidence} ({num_sources} sources)", inline=False)

            if results['metadatas'][0]:
                sources_text = ""
                for i, metadata in enumerate(results['metadatas'][0][:3], 1):
                    author  = metadata.get('author',    'Unknown')
                    channel = metadata.get('channel',   'Unknown')
                    date    = metadata.get('timestamp', 'Unknown')[:10]
                    tags    = metadata.get('tags',      'general')
                    badges  = "  ".join(
                        f"{TAG_EMOJIS.get(t.strip(),'📌')} `{t.strip()}`"
                        for t in tags.split(",")
                    )
                    sources_text += f"{i}. **{author}** in #{channel} on {date}  {badges}\n"
                embed.add_field(name="📎 Sources", value=sources_text, inline=False)

            embed.set_footer(text="React with 📌 to important messages to improve my knowledge!")
        else:
            embed = discord.Embed(
                title=f"💬 Question: {question[:100]}",
                description=(
                    "❌ **No information found in knowledge base.**\n\n"
                    "React with 📌 to relevant messages to fill this gap!"
                ),
                color=discord.Color.red()
            )
            embed.add_field(name="📊 Confidence", value=f"{confidence} (0 sources)", inline=False)

        await interaction.followup.send(embed=embed)
        print(f"✓ Answered question from {interaction.user}: {question[:50]}...")

    except Exception as e:
        print(f"Error processing question: {e}")
        await interaction.followup.send("❌ An error occurred. Please try again.", ephemeral=True)


@bot.tree.command(name="exit_brief", description="Generate exit brief summary of all captured knowledge")
async def exit_brief_command(interaction: discord.Interaction):
    """FEATURE 3 enhanced with tag breakdown"""
    await interaction.response.defer(thinking=True)

    try:
        all_results    = collection.get(where={"guild_id": str(interaction.guild_id)})
        total_messages = len(all_results['ids']) if all_results['ids'] else 0

        if total_messages == 0:
            await interaction.followup.send("❌ No knowledge captured yet! React with 📌 first.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📄 Exit Brief Generated",
            description=f"Knowledge base summary for **{interaction.guild.name}**",
            color=discord.Color.blue()
        )
        embed.add_field(name="📊 Total Messages", value=f"**{total_messages}**", inline=True)

        authors = set(meta.get('author', 'Unknown') for meta in all_results['metadatas'])
        embed.add_field(name="👥 Contributors", value=f"**{len(authors)}** members", inline=True)

        timestamps = [m.get('timestamp', '') for m in all_results['metadatas'] if m.get('timestamp')]
        if timestamps:
            dates = sorted([t[:10] for t in timestamps if t])
            embed.add_field(name="📅 Date Range", value=f"{dates[0]} to {dates[-1]}", inline=True)

        tag_counter = Counter()
        for meta in all_results['metadatas']:
            for t in meta.get("tags", "general").split(","):
                tag_counter[t.strip()] += 1
        tag_summary = "\n".join(
            f"{TAG_EMOJIS.get(t,'📌')} **{t.capitalize()}**: {c}" for t, c in tag_counter.most_common()
        )
        embed.add_field(name="🏷️ By Category", value=tag_summary or "—", inline=False)

        if total_messages > 0:
            sample_text = "\n\n".join(
                f"**{i+1}.** {doc[:100]}..." for i, doc in enumerate(all_results['documents'][:5])
            )
            embed.add_field(name="📌 Sample Captured Knowledge", value=sample_text[:1000], inline=False)

        embed.add_field(
            name="💡 How to Use This",
            value=(
                "• `/ask` - Query this knowledge\n"
                "• `/export_pdf` - Download full PDF report\n"
                "• `/analytics` - View analytics dashboard\n"
                "• React 📌 to add more knowledge"
            ),
            inline=False
        )
        embed.set_footer(text=f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | Powered by Xenone")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Error generating exit brief: {e}")
        await interaction.followup.send("❌ An error occurred.", ephemeral=True)


# =============================================================================
# FEATURE 5: /analytics  – Analytics Dashboard
# =============================================================================

@bot.tree.command(name="analytics", description="📊 Show analytics: most-asked questions and knowledge gaps")
async def analytics_command(interaction: discord.Interaction):
    """FEATURE 5: Analytics Dashboard"""
    await interaction.response.defer(thinking=True)

    guild_id = str(interaction.guild_id)
    store    = analytics_store.get(guild_id, {"questions": [], "unanswered": []})
    all_qs   = store["questions"]
    gaps     = store["unanswered"]

    embed = discord.Embed(
        title="📊 Xenone Analytics Dashboard",
        description=f"Insights for **{interaction.guild.name}**",
        color=discord.Color.blurple()
    )

    # Most-asked questions
    if all_qs:
        top = Counter(all_qs).most_common(5)
        top_text = "\n".join(
            f"**{i+1}.** {q[:80]}{'...' if len(q)>80 else ''}  ×{c}"
            for i, (q, c) in enumerate(top)
        )
        embed.add_field(name="🔥 Most-Asked Questions", value=top_text, inline=False)
    else:
        embed.add_field(name="🔥 Most-Asked Questions", value="No questions recorded yet.", inline=False)

    # Knowledge gaps
    if gaps:
        gap_top  = Counter(gaps).most_common(5)
        gap_text = "\n".join(
            f"**{i+1}.** {q[:80]}{'...' if len(q)>80 else ''}  ×{c}"
            for i, (q, c) in enumerate(gap_top)
        )
        embed.add_field(name="⚠️ Knowledge Gaps (Unanswered Questions)", value=gap_text, inline=False)
    else:
        embed.add_field(name="⚠️ Knowledge Gaps", value="✅ No unanswered questions — great coverage!", inline=False)

    # Tag distribution bar chart
    try:
        all_results = collection.get(where={"guild_id": guild_id})
        tag_counter = Counter()
        for meta in all_results.get("metadatas", []):
            for t in meta.get("tags", "general").split(","):
                tag_counter[t.strip()] += 1
        if tag_counter:
            total    = sum(tag_counter.values())
            bar_text = ""
            for tag, count in tag_counter.most_common():
                pct      = int(count / total * 20)
                bar      = "█" * pct + "░" * (20 - pct)
                emoji    = TAG_EMOJIS.get(tag, "📌")
                bar_text += f"{emoji} `{tag:<10}` {bar}  {count}\n"
            embed.add_field(name="🏷️ Knowledge by Tag", value=bar_text, inline=False)
    except Exception:
        pass

    embed.add_field(
        name="📈 Totals",
        value=f"**{len(all_qs)}** questions asked  |  **{len(gaps)}** unanswered",
        inline=False
    )
    embed.set_footer(text="Use /ask to query  |  React 📌 to fill the gaps")
    await interaction.followup.send(embed=embed)


# =============================================================================
# FEATURE 6: /export_pdf  – Export to actual PDF file
# =============================================================================

@bot.tree.command(name="export_pdf", description="📄 Download a full PDF of all captured knowledge")
async def export_pdf_command(interaction: discord.Interaction):
    """FEATURE 6: Export to PDF — generates and uploads a real PDF file"""
    await interaction.response.defer(thinking=True)

    try:
        all_results    = collection.get(where={"guild_id": str(interaction.guild_id)})
        total_messages = len(all_results.get('ids', []))

        if total_messages == 0:
            await interaction.followup.send("❌ No knowledge captured yet! React with 📌 first.", ephemeral=True)
            return

        pdf_bytes = build_pdf(interaction.guild.name, {
            "documents": all_results.get("documents", []),
            "metadatas": all_results.get("metadatas", []),
        })

        filename = (
            f"xenone_exit_brief_"
            f"{interaction.guild.name.replace(' ', '_')}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        )

        pdf_file = discord.File(io.BytesIO(pdf_bytes), filename=filename)

        embed = discord.Embed(
            title="📄 PDF Export Ready",
            description=(
                f"Your Xenone exit brief for **{interaction.guild.name}** is attached.\n\n"
                f"📊 **{total_messages}** messages across all categories."
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | Xenone")

        await interaction.followup.send(embed=embed, file=pdf_file)
        print(f"✓ PDF exported for {interaction.guild.name} ({total_messages} messages)")

    except Exception as e:
        print(f"Error exporting PDF: {e}")
        await interaction.followup.send("❌ Failed to generate PDF. Please try again.", ephemeral=True)


# =============================================================================
# EXISTING COMMANDS (stats, help)
# =============================================================================

@bot.tree.command(name="stats", description="View Xenone knowledge base statistics")
async def stats_command(interaction: discord.Interaction):
    try:
        all_results    = collection.get(where={"guild_id": str(interaction.guild_id)})
        total_messages = len(all_results['ids']) if all_results['ids'] else 0

        embed = discord.Embed(
            title="📊 Xenone Knowledge Base Stats",
            description=f"Statistics for **{interaction.guild.name}**",
            color=discord.Color.purple()
        )
        embed.add_field(name="📌 Messages Captured", value=f"**{total_messages}**", inline=True)

        if total_messages > 0:
            authors  = set(meta.get('author',  'Unknown') for meta in all_results['metadatas'])
            channels = set(meta.get('channel', 'Unknown') for meta in all_results['metadatas'])
            embed.add_field(name="👥 Contributors",   value=f"**{len(authors)}**",  inline=True)
            embed.add_field(name="💬 Active Channels", value=f"**{len(channels)}**", inline=True)

        embed.add_field(
            name="🤖 Available Commands",
            value=(
                "• `/ask [question]` - Query knowledge\n"
                "• `/exit_brief` - Discord summary\n"
                "• `/export_pdf` - Download PDF\n"
                "• `/analytics` - Analytics dashboard\n"
                "• `/stats` - Statistics\n"
                "• React 📌 to save messages"
            ),
            inline=False
        )
        embed.set_footer(text="Xenone - AI Knowledge Hub for Discord")
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        print(f"Error getting stats: {e}")
        await interaction.response.send_message("❌ Error retrieving statistics.", ephemeral=True)


@bot.tree.command(name="help", description="Learn how to use Xenone")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Xenone Bot - How to Use",
        description="AI-powered knowledge management for your Discord server",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="1️⃣ Capture Knowledge (📌 Reaction)",
        value=(
            "React to any message with 📌\n"
            "Xenone saves it and **auto-tags** it:\n"
            "✅ Decision  •  💡 Lesson  •  ⚠️ Warning  •  🎯 Action  •  ❓ Question"
        ),
        inline=False
    )
    embed.add_field(
        name="2️⃣ Query Knowledge (/ask)",
        value=(
            "Use `/ask [question]` to search captured knowledge.\n"
            "**Example:** `/ask what was our marketing budget?`"
        ),
        inline=False
    )
    embed.add_field(
        name="3️⃣ Discord Summary (/exit_brief)",
        value="Rich embed with stats, category breakdown, and sample messages.",
        inline=False
    )
    embed.add_field(
        name="4️⃣ Download PDF (/export_pdf)  🆕",
        value="Generates a real PDF file — perfect for handoffs and reports.",
        inline=False
    )
    embed.add_field(
        name="5️⃣ Analytics (/analytics)  🆕",
        value="See most-asked questions and uncovered knowledge gaps.",
        inline=False
    )
    embed.add_field(
        name="Other Commands",
        value="• `/stats` - Knowledge base statistics\n• `/help` - This message",
        inline=False
    )
    embed.set_footer(text="Built for Ideathon April 2026 | Team Xenone")
    await interaction.response.send_message(embed=embed)


# =============================================================================
# ERROR HANDLER + ENTRY POINT
# =============================================================================

@bot.event
async def on_command_error(ctx, error):
    print(f"Error: {error}")


if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN not found in .env file")
        print("Please create a .env file with: DISCORD_BOT_TOKEN=your_token_here")
    else:
        print("🚀 Starting Xenone Discord Bot...")
        bot.run(DISCORD_BOT_TOKEN)
