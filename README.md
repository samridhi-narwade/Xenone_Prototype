# Xenone - AI Knowledge Hub for Student Clubs

[![AMD Slingshot Hackathon 2025](https://img.shields.io/badge/AMD%20Slingshot-2025-red)](https://amd.com)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **AI-powered knowledge management system that captures, stores, and surfaces institutional knowledge for student organizations with high turnover.**

---

## 🎯 Problem Statement

**70% of team knowledge is tacit** (exists only in people's heads) and **80% is lost during handoffs** between graduating batches. Xenone solves this by:

1. **Passive Capture** - 📌 emoji reaction = instant knowledge capture
2. **AI Q&A** - Confidence-scored answers grounded in team history
3. **Exit Briefs** - One-click handoff documents for graduating members

---

## 🚀 Quick Start

### Run the Prototype (Google Colab)

**Fastest way to see Xenone in action:**

1. Open our Colab notebook: [Xenone Prototype](https://colab.research.google.com/drive/1VquMrOaindH4G0jlQHQcYA6TGuFnjpy2)
2. Click `Runtime` → `Run all`
3. Wait 3-5 minutes for model download
4. See demo queries with confidence scoring

### Run Locally

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/xenone.git
cd xenone

# Install dependencies
pip install -r requirements.txt

# Run the knowledge base demo
python xenone_core.py
```

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Slack/Discord  │ ← User Interface
└────────┬────────┘
         │ 📌 Emoji reactions
         │ /ask commands
         ↓
┌─────────────────┐
│   Slack Bot     │ ← Event Handler
│  (Python SDK)   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  RAG Pipeline   │ ← Core Logic
│  • Embedding    │
│  • Retrieval    │
│  • Generation   │
└────────┬────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌─────────┐ ┌──────────┐
│ChromaDB │ │ TinyLlama│ ← AI Components
│ Vector  │ │   1.1B   │
│   DB    │ │   LLM    │
└─────────┘ └──────────┘
```

---

## ✨ Features

### 1. Passive Knowledge Capture
- React with 📌 emoji to any Slack/Discord message
- Bot automatically captures, embeds, and stores
- Zero documentation burden on team members

### 2. AI Q&A with Confidence Scoring
```
User: /ask why did we switch vendors?

Xenone: 🟢 HIGH CONFIDENCE (3 sources)

We switched to PrintPro because they offer 30% cost 
savings and 3-day turnaround vs 7 days from previous 
vendor. Decision made Dec 14, 2024.

Sources: 
1. Message from Sarah Kumar in #marketing...
2. Message from Priya Sharma in #budget-planning...
3. Message from Team Lead in #decisions...
```

**Confidence Levels:**
- 🟢 **HIGH** (3+ sources): Multiple team discussions found
- 🟡 **MEDIUM** (1-2 sources): Limited documentation
- 🔴 **LOW** (0 sources): No information found - flag to document

### 3. Exit Brief Generator
One-click PDF generation containing:
- ✅ Key Decisions Made
- ✅ Lessons Learned  
- ✅ Warnings & Pitfalls
- ✅ Unfinished Work

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **LLM** | TinyLlama 1.1B | Text generation & reasoning |
| **Framework** | Hugging Face Transformers | Model inference |
| **Vector DB** | ChromaDB | Semantic search |
| **Bot SDK** | Slack Bolt (Python) | Event handling |
| **Deployment** | Google Colab (prototype) | GPU access |
| **Planned** | AMD MI300X + ROCm | Production deployment |

---

## 📊 How Confidence Scoring Works

```python
# Simplified logic
results = vector_db.query(question, n=3)
num_sources = count_relevant_sources(results, threshold=0.7)

if num_sources >= 3:
    confidence = "HIGH"
elif num_sources >= 1:
    confidence = "MEDIUM"
else:
    confidence = "LOW"
```

**Key Innovation:** Unlike ChatGPT/Claude which answer confidently even when guessing, Xenone explicitly flags uncertainty and prompts documentation.

---

## 💡 Why Xenone?

| Problem | Traditional Solution | Xenone Solution |
|---------|---------------------|-----------------|
| Knowledge capture | Manual documentation | 📌 emoji = captured |
| Finding information | Search 6 months of Slack | Semantic AI search |
| Handoffs | "Figure it out yourself" | Auto-generated exit brief |
| Trust | AI hallucinates answers | Confidence scores + sources |
| Cost | $28-38/user/month | ~$50/month for entire club |

---

## 🎓 Built For

- **Student Clubs** - High turnover, informal structure
- **Project Teams** - Short-term with critical knowledge
- **NGOs** - Volunteer organizations with limited budgets
- **Startups** - Early-stage teams documenting as they grow

---

## 📁 Repository Structure

```
xenone/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── xenone_core.py              # Core RAG implementation
├── slack_bot/
│   ├── bot.py                  # Slack integration
│   ├── .env.example            # Environment variables template
│   └── requirements.txt        # Bot-specific dependencies
├── dashboard/
│   ├── app.py                  # Streamlit dashboard (planned)
│   └── templates/              # Exit brief templates
├── notebooks/
│   └── xenone_prototype.ipynb  # Google Colab notebook
├── docs/
│   ├── ARCHITECTURE.md         # Technical deep dive
│   ├── DEPLOYMENT.md           # AMD Cloud migration guide
│   └── API.md                  # API documentation
└── tests/
    ├── test_rag.py             # RAG pipeline tests
    └── test_confidence.py      # Confidence scoring tests
```

---

## 🚀 Deployment

### Prototype (Current)
- **Platform:** Google Colab
- **GPU:** NVIDIA T4 (free tier)
- **Model:** TinyLlama 1.1B
- **Cost:** $0

### Production (Planned)
- **Platform:** AMD Developer Cloud
- **GPU:** MI300X (192GB HBM3)
- **Model:** Llama 3 70B
- **Benefits:**
  - 12x more memory
  - Private deployment
  - No API costs
  - Data sovereignty

**Migration Path:** Code is hardware-agnostic. Change 3 lines:
```python
# Before (Colab)
model = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
device = "cuda"

# After (AMD Cloud)
model = "meta-llama/Llama-3-70b-chat"
device = "rocm"
```

---

## 📈 Roadmap

### Phase 1: Prototype ✅ (Completed)
- [x] RAG pipeline with ChromaDB
- [x] Confidence scoring
- [x] Demo knowledge base
- [x] Colab deployment

### Phase 2: Slack Integration (In Progress)
- [ ] Emoji capture bot
- [ ] /ask slash command
- [ ] Socket mode connection
- [ ] Authentication flow

### Phase 3: Production Features
- [ ] Exit brief PDF generator
- [ ] Discord integration
- [ ] Document upload & analysis
- [ ] Multi-club support

### Phase 4: AMD Migration
- [ ] Deploy to AMD Developer Cloud
- [ ] Benchmark MI300X vs T4
- [ ] Load Llama 3 70B model
- [ ] Scale testing

---

## 🏆 AMD Slingshot Hackathon 2025

**Team:** Xenone  
**Leader:** Samridhi  
**Problem Category:** Team knowledge hubs that capture tacit know-how

**Why AMD?**
- Designed for MI300X's 192GB unified memory
- ROCm open-source ecosystem alignment
- Private on-premise deployment for student data
- Cost-effective for educational institutions

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- AMD Developer Cloud for GPU infrastructure
- Hugging Face for model hosting
- Google Colab for prototyping environment
- Slack API for integration support

---

## 📞 Contact

- **GitHub Issues:** [Report bugs or request features](https://github.com/YOUR_USERNAME/xenone/issues)
- **Documentation:** [Full docs](https://github.com/samridhi-narwade/Xenone_Prototype/wiki)
- **Demo Video:** [Watch on YouTube](YOUR_VIDEO_LINK)

---

## 🌟 Star Us!

If Xenone helps your student club preserve knowledge, give us a ⭐️ on GitHub!

**Built with ❤️ for student communities by Team Xenone**
