<div align="center">

# 🤖 Xenone
### AI-Powered Knowledge Hub for Discord

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![discord.py](https://img.shields.io/badge/discord.py-2.3%2B-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discordpy.readthedocs.io)
[![TinyLlama](https://img.shields.io/badge/AI-TinyLlama%201.1B-ff6b35?style=flat-square&logo=huggingface&logoColor=white)](https://huggingface.co/TinyLlama)
[![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-orange?style=flat-square)](https://trychroma.com)
[![Railway](https://img.shields.io/badge/Hosted%20on-Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white)](https://railway.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

*Built for Ideathon April 2026 — Team Xenone*

</div>

---

## 💡 What is Xenone?

Xenone turns your Discord server into a **living knowledge base**. Instead of important messages getting buried in chat, Xenone lets your team capture, tag, search, and export knowledge — all powered by a local AI model running right inside the bot.

React with 📌 to save a message. Use `/ask` to get answers. Export everything to PDF with `/export_pdf`. No external knowledge base tool needed.

---

## ✨ Features

| # | Feature | How to use |
|---|---|---|
| 1 | **📌 Reaction Capture** | React to any message with 📌 to save it to the knowledge base |
| 2 | **🤖 AI-Powered Q&A** | `/ask [question]` — queries captured messages via TinyLlama with confidence scoring |
| 3 | **📄 Exit Brief** | `/exit_brief` — rich Discord embed with a full summary of captured knowledge |
| 4 | **🏷️ Auto-Tagging** | Messages are automatically categorized: `decision` ✅ `lesson` 💡 `warning` ⚠️ `action` 🎯 `question` ❓ |
| 5 | **📊 Analytics Dashboard** | `/analytics` — most-asked questions, knowledge gaps, and tag distribution |
| 6 | **📄 PDF Export** | `/export_pdf` — generates a real, downloadable PDF report of all captured knowledge |

---

## 🛠️ Slash Commands

| Command | Description |
|---|---|
| `/ask [question]` | Ask the AI a question based on captured server messages |
| `/exit_brief` | Generate a Discord embed summary of all knowledge |
| `/export_pdf` | Download a full PDF report of the knowledge base |
| `/analytics` | View most-asked questions and knowledge gaps |
| `/stats` | View knowledge base statistics |
| `/help` | Show all commands and usage guide |

---

## 📋 Requirements

- Python **3.10+**
- A [Discord Developer Application](https://discord.com/developers/applications) with a Bot token
- **Message Content Intent** enabled in the Discord Developer Portal
- ~3–4 GB RAM (for TinyLlama model loading)
- `pip` for installing dependencies

---

## 🚀 Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/xenone.git
cd xenone
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Activate:
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ `torch` and `transformers` are large packages. The first install may take several minutes.

### 4. Configure environment variables

Create a `.env` file in the root directory:

```env
DISCORD_BOT_TOKEN=your_bot_token_here
```

> ⚠️ **Never** commit your `.env` file. Add it to `.gitignore`.

### 5. Enable Discord Intents

In the [Discord Developer Portal](https://discord.com/developers/applications):
1. Go to your app → **Bot** tab
2. Enable **Message Content Intent**
3. Enable **Server Members Intent**

### 6. Run the bot

```bash
python xenone_discord_bot.py
```

> 🕐 On first run, TinyLlama (~2GB) will be downloaded. This takes 2–3 minutes. Subsequent starts are faster.

---

## 📁 Project Structure

```
xenone/
├── xenone_discord_bot.py    # Main bot — all features in one file
├── requirements.txt         # Python dependencies
├── .env                     # Your secrets (DO NOT COMMIT)
├── .env.example             # Template for environment variables
├── .gitignore
└── Procfile                 # For Railway / cloud deployment
```

---

## 🏷️ Auto-Tagging System

When a message is captured with 📌, Xenone automatically analyzes the content and assigns one or more tags using keyword pattern matching:

| Tag | Emoji | Triggered by keywords like… |
|---|---|---|
| `decision` | ✅ | *"we decided"*, *"approved"*, *"finalized"*, *"go with"* |
| `lesson` | 💡 | *"learned"*, *"retrospective"*, *"next time"*, *"takeaway"* |
| `warning` | ⚠️ | *"bug"*, *"avoid"*, *"risk"*, *"don't"*, *"deprecated"* |
| `action` | 🎯 | *"todo"*, *"assigned to"*, *"need to"*, *"action item"* |
| `question` | ❓ | Messages ending with `?` or starting with *why / how / what* |
| `general` | 📌 | Fallback when no other tag matches |

---

## 🤖 How the AI Works

Xenone uses **TinyLlama 1.1B Chat** (a lightweight open-source LLM) to answer questions. When you run `/ask`:

1. ChromaDB finds the top 5 most relevant captured messages via semantic search
2. Those messages become the context for TinyLlama
3. TinyLlama generates an answer grounded in your server's own captured knowledge
4. A **confidence score** is shown based on how many relevant sources were found

| Sources found | Confidence |
|---|---|
| 3 or more | 🟢 HIGH |
| 1–2 | 🟡 MEDIUM |
| 0 | 🔴 LOW |

---

## 📄 PDF Export

`/export_pdf` generates a structured PDF containing:
- Cover page with server name and generation date
- Summary: total messages, unique contributors, date range
- Knowledge breakdown by category (tag)
- All captured messages grouped by tag, with author, channel, and timestamp

---

## ⚙️ Dependencies

| Package | Purpose |
|---|---|
| `discord.py >= 2.3.2` | Discord bot framework |
| `transformers >= 4.36.0` | TinyLlama AI model |
| `torch >= 2.1.0` | AI inference engine |
| `accelerate >= 0.25.0` | Optimized model loading |
| `chromadb >= 0.4.22` | In-memory vector database |
| `fpdf2 >= 2.7.6` | PDF generation |
| `python-dotenv >= 1.0.0` | `.env` file loading |

---

## ⚠️ Known Limitations

- **ChromaDB is in-memory** — the knowledge base resets when the bot restarts. For persistence across restarts, replace `chromadb.Client()` with `chromadb.PersistentClient(path="./chroma_db")` and mount a Railway volume.
- **TinyLlama requires ~3–4 GB RAM** — ensure your hosting plan has enough memory.
- **First startup is slow** — model download and loading takes 2–5 minutes.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

1. Fork the repo
2. Create your branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📜 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

---

<div align="center">

Built with ❤️ by **Team Xenone** · Ideathon April 2026

</div>
