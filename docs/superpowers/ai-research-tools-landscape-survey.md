# AI-Powered Academic Research Assistants & Literature Review Tools: Landscape Survey

**Date**: 2026-03-21

---

## Table of Contents

1. [Dedicated AI Research Tools](#1-dedicated-ai-research-tools)
2. [LLM-Based Research Agents](#2-llm-based-research-agents)
3. ["Deep Research" Features from Major AI Labs](#3-deep-research-features-from-major-ai-labs)
4. [Academic AI Tools: 2025-2026 Launches and Commentary](#4-academic-ai-tools-2025-2026-launches-and-commentary)
5. [Systematic Review Automation Tools](#5-systematic-review-automation-tools)
6. [Agent Frameworks Applied to Research](#6-agent-frameworks-applied-to-research)
7. [Cross-Cutting Analysis](#7-cross-cutting-analysis)

---

## 1. Dedicated AI Research Tools

### 1.1 Elicit

- **What it does**: AI research assistant for evidence synthesis. Searches 138M+ papers and 545K clinical trials. Generates structured reports with sentence-level citations linked to exact source passages.
- **Methodology**: Semantic similarity search (not just keyword matching). Uses Claude Opus 4.5 (as of Dec 2025) for data extraction and report writing. Supports "Strict Screening" for systematic reviews (Dec 2025).
- **Formal protocol support**: Systematic Review workflow available, but a 2025 Cochrane-affiliated study (Lau et al.) found Elicit's sensitivity averaged only 39.5% and precision 41.8%, concluding it "is not equipped to replace standard systematic searching" but is "useful for grant proposals and scoping searches."
- **Pipeline coverage**: Search, screening, data extraction, synthesis, report generation. Reports can include up to 80 papers. "Research Agents" (Dec 2025) handle broad topic exploration.
- **Limitations**: Low recall/sensitivity makes it unsuitable as a sole search tool for formal systematic reviews. API launched March 2026 but ecosystem is still young.
- **Pricing**: Free tier available; paid plans from $9/month.

### 1.2 Consensus

- **What it does**: AI search engine exclusively for peer-reviewed literature. Searches 200M+ papers aggregated from Semantic Scholar, OpenAlex, and its own crawl. Generates synthesis with citations.
- **Methodology**: Hybrid search combining semantic AI embeddings (intent capture) with BM25 keyword search, weighted by citation count, recency, and journal reputation. Uses GPT-5 and OpenAI's Responses API (as of 2025-2026) with a multi-agent architecture: a Planning Agent decomposes queries, specialized agents read/synthesize, and a final agent assembles the report. The "Consensus Meter" classifies studies as supporting/contradicting yes/no research questions.
- **Formal protocol support**: "Deep Search" mode runs up to 20 targeted searches, reviews 1,000+ papers, and produces a report structured like a traditional literature review (introduction, methods, results, discussion). Not PRISMA-aligned per se, but the output structure mirrors it.
- **Pipeline coverage**: Search, synthesis, structured report generation. Does not handle screening workflows or data extraction tables in the way systematic review tools do.
- **Limitations**: Focused on synthesis, not full systematic review management. No team collaboration, no PRISMA flow diagram generation.
- **Pricing**: Free tier; Pro at $9.99/month.

### 1.3 Scite

- **What it does**: AI platform for discovering and evaluating scientific literature through "Smart Citations" that classify whether a citing paper supports, contrasts, or merely mentions the cited work. Indexed 1.6B+ citations from 30+ publisher partnerships. Serves 2M+ users.
- **Methodology**: NLP-based citation context classification (supporting/contrasting/mentioning). Scite Assistant uses LLMs (models include Haiku 4.5 as a lightweight option, Oct 2025) to answer questions grounded in real papers. Every answer is linked to actual citation contexts.
- **Formal protocol support**: None explicit. The tool is a discovery and evaluation layer, not a protocol-driven review pipeline.
- **Pipeline coverage**: Search, citation evaluation, Q&A synthesis. January 2026 added mixed patent+paper search (private beta).
- **Limitations**: Focused on citation analysis rather than full review workflows. No screening management, no data extraction forms.
- **Pricing**: Institutional and individual plans available.

### 1.4 SciSpace

- **What it does**: End-to-end platform for discovering, analyzing, and writing scientific literature. 280M+ papers sourced from Semantic Scholar, OpenAlex, Google Scholar, and other repositories.
- **Methodology**: AI-powered reading comprehension (can explain paper sections in plain language), literature search, and workspace-based organization. Provides 150+ tools within the platform for different research tasks.
- **Pipeline coverage**: Search, reading comprehension, paper comparison, note-taking, writing assistance.
- **Limitations**: Breadth-over-depth approach. Not specifically designed for systematic reviews.

### 1.5 Research Rabbit

- **What it does**: Citation-based discovery tool. Starting from seed papers, it maps citation networks to recommend related work. Interactive visual graphs.
- **Methodology**: Relies on Semantic Scholar and PubMed for search; discovery is driven by citation/reference relationships (not semantic similarity). Users build collections and the tool recommends papers similar to or cited by those collections.
- **Pipeline coverage**: Discovery and visualization only. No synthesis, no extraction.
- **Limitations**: Depends on citation graph completeness. Does not generate summaries or reports. Merged/partnered with Litmaps in October 2025.
- **Pricing**: Free.

### 1.6 Connected Papers

- **What it does**: Visual tool that generates similarity graphs from a seed paper. Papers are arranged by co-citation and bibliographic coupling similarity (not direct citation).
- **Methodology**: Uses Semantic Scholar data. The graph reflects similarity based on shared citations rather than direct citation links, which can surface thematically related work that does not directly cite each other.
- **Pipeline coverage**: Discovery and visualization only.
- **Limitations**: Limited to visual exploration. No AI synthesis, no full-text analysis. The graph can be misleading if the seed paper has thin citation context.
- **Pricing**: Free tier; Pro plans available.

### 1.7 Litmaps

- **What it does**: Literature mapping tool with citation network visualization covering ~270M works from 1400 to present. Color-coded organization, automated alerts for new publications.
- **Methodology**: Citation-based mapping with some AI-powered semantic matching (newer feature). Automated monitoring for new papers entering a user's research landscape.
- **Pipeline coverage**: Discovery, visualization, monitoring.
- **Limitations**: Primarily a mapping tool, not a synthesis engine. Partnered with Research Rabbit (Oct 2025). Closed $1M Series A (May 2025).
- **Pricing**: Free tier; Pro plans available.

### 1.8 Inciteful

- **What it does**: Two modes -- "Paper Discovery" (builds citation network from a seed paper) and "Literature Connector" (finds connections between two papers across disciplines).
- **Methodology**: Citation graph traversal and network analysis.
- **Pipeline coverage**: Discovery only.
- **Limitations**: No AI synthesis. Useful for initial exploration but not for systematic work.
- **Pricing**: Free and open access.

### 1.9 Semantic Scholar

- **What it does**: AI-powered academic search engine from the Allen Institute for AI (AI2). 200M+ papers. Provides TLDR summaries (GPT-3-style single-sentence auto-summaries), Semantic Reader (augmented PDF reading), and Research Feeds (personalized alerts).
- **Methodology**: TLDR uses abstractive summarization models. Semantic Reader overlays "Goal/Method/Result" highlights on PDFs and provides in-line citation cards. Research Feeds learn from user libraries.
- **Pipeline coverage**: Search, paper triage (TLDR), augmented reading. Does not generate synthesis reports.
- **Limitations**: TLDRs are directional, not definitive. No systematic review workflow. Primarily a search and triage tool.
- **Pricing**: Free. Open API available.

### 1.10 Scholarcy

- **What it does**: Summarizes and analyzes uploaded academic documents. Generates structured summaries, notes, and flashcards. "Robo-Highlighter" identifies key phrases and contributions.
- **Methodology**: NLP-based document processing. Does not search the literature -- it processes documents the user uploads.
- **Pipeline coverage**: Reading comprehension and summarization only. No search, no synthesis across multiple papers.
- **Limitations**: Single-document focus. Not a discovery or review tool.
- **Pricing**: Free tier (3 summaries/day); Plus plan for more.

### 1.11 Undermind

- **What it does**: AI research assistant that conducts iterative, adaptive literature searches mimicking expert human researchers. Searches across Semantic Scholar and other databases, analyzing thousands of papers per query.
- **Methodology**: Agent-like search with multiple rounds of query refinement and citation chaining. As of Dec 2024, described as "the only off-the-shelf academic search that has agent-like search" with iterative adaptation.
- **Pipeline coverage**: Discovery and search. Provides ranked, analyzed results.
- **Limitations**: Newer tool with less established track record. Limited collaboration features.
- **Pricing**: Free tier; Pro Academic at $16/month.

---

## 2. LLM-Based Research Agents

### 2.1 OpenScholar (Allen Institute for AI / University of Washington)

- **What it does**: Specialized retrieval-augmented LM that answers scientific queries by retrieving relevant passages from 45M open-access papers and synthesizing citation-backed responses. Published in Nature (Feb 2026).
- **Methodology**: Retrieval-augmented generation (RAG) over a dedicated scientific corpus. OpenScholar-8B outperforms GPT-4o by 5% and PaperQA2 by 7% in correctness. GPT-4o hallucinates citations 78-90% of the time; OpenScholar achieves citation accuracy on par with human experts. Human evaluators preferred OpenScholar-8B responses over expert-written ones 51% of the time.
- **Pipeline coverage**: Q&A, synthesis with citations. Does not manage review workflows.
- **Formal protocol**: None. Research-oriented, not protocol-driven.
- **Open source**: Fully open-sourced (code, models, datastore, data, demo).
- **Limitations**: Focused on Q&A synthesis. Not a full review management platform. Requires computational resources to run locally.

### 2.2 PaperQA2 (FutureHouse)

- **What it does**: High-accuracy RAG agent for scientific documents. First agent to beat PhD/postdoc-level biology researchers on literature research tasks.
- **Methodology**: Multi-step agentic RAG with document metadata-aware embeddings, LLM-based re-ranking, and contextual summarization. Iteratively refines queries. Uses OpenAI embeddings by default.
- **Pipeline coverage**: Q&A over uploaded papers, summarization, contradiction detection.
- **Formal protocol**: None.
- **Open source**: Yes (Future-House/paper-qa on GitHub).
- **Limitations**: Requires the user to supply PDFs. Not a discovery/search tool by itself.

### 2.3 Robin / Kosmos (FutureHouse / Edison Scientific)

- **What it does**: Robin is a multi-agent system that autonomously generates hypotheses, designs experiments, analyzes data, and iterates on findings. Integrates specialized sub-agents: Crow, Falcon, and Owl (literature search/synthesis), Phoenix (chemical synthesis), Finch (data analysis).
- **Methodology**: End-to-end autonomous scientific discovery. In its landmark demonstration, Robin identified ripasudil as a novel therapeutic candidate for dry AMD in 2.5 months. Kosmos (Nov 2025, spun out as Edison Scientific, $70M seed round) processes 1,500 papers and 42,000 lines of analysis code in a single run.
- **Pipeline coverage**: Full scientific pipeline -- literature review through experimental validation.
- **Formal protocol**: None formally declared, but the workflow is structured around hypothesis generation, experimental design, execution, and analysis.
- **Limitations**: Domain-focused (biomedical). Requires wet-lab infrastructure for experimental validation. Not publicly available as a general tool.

### 2.4 LitLLM

- **What it does**: AI toolkit for writing literature reviews. Published at TMLR 2025.
- **Methodology**: Two-step retrieval (LLM keyword extraction + embedding search against external knowledge base) followed by two-step generation (plan outline, then execute plan). Combining keyword and embedding search improves precision and recall by 10% and 30% respectively. Planning-based generation reduces hallucinated references by 18-26%.
- **Pipeline coverage**: Retrieval of related work + generation of literature review sections.
- **Open source**: Yes (GitHub: LitLLM/LitLLM).
- **Limitations**: Focused on "related work" section generation. Does not handle systematic review protocols.

### 2.5 Agent Laboratory / AgentRxiv

- **What it does**: Agent Laboratory is an end-to-end autonomous research workflow with three phases: Literature Review, Experimentation, Report Writing. Published at EMNLP 2025 Findings. AgentRxiv extends this with a shared preprint server for agent-to-agent collaboration.
- **Methodology**: Specialized LLM agents (PhD agent, Postdoc agent) handle different phases. Uses o1-preview as the backbone (best results). Human feedback at each stage improves quality significantly. AgentRxiv demonstrated 13.7% improvement over baseline on MATH-500 through agent collaboration.
- **Pipeline coverage**: Full research pipeline from idea to paper. 84% cost reduction vs. previous autonomous methods.
- **Open source**: Yes (GitHub: SamuelSchmidgall/AgentLaboratory).
- **Limitations**: Quality does not yet match careful human-authored research. Requires human-in-the-loop for best results.

### 2.6 GPT-Researcher

- **What it does**: Open-source autonomous agent for deep web and local research. Generates detailed reports with citations. Outperformed Perplexity, OpenAI, OpenDeepSearch, and HuggingFace on CMU's DeepResearchGym benchmark (May 2025).
- **Methodology**: Planner-executor architecture. Breaks queries into sub-questions, searches the web in parallel, synthesizes findings. Now supports MCP integration, LangSmith tracing, multi-agent workflows via LangGraph and AG2.
- **Pipeline coverage**: Research planning, multi-source search, report generation with citations.
- **Open source**: Yes (GitHub: assafelovic/gpt-researcher).
- **Limitations**: Web-focused, not specifically designed for academic literature. No integration with academic databases by default (though MCP can bridge this).

### 2.7 AutoResearchClaw

- **What it does**: Fully autonomous research pipeline from idea to paper. Features "OpenCode Beast Mode" with automatic complexity scoring.
- **Methodology**: Multi-LLM support, automatic research workflow.
- **Open source**: Yes (GitHub: aiming-lab/AutoResearchClaw, v0.3.1 as of March 2026).
- **Limitations**: Early-stage. Limited community validation.

### 2.8 STORM (Stanford)

- **What it does**: Writing system for generating Wikipedia-like articles from scratch. Published at NAACL 2024, with Co-STORM at EMNLP 2024.
- **Methodology**: Multi-perspective question asking. (1) Discovers diverse perspectives on a topic, (2) simulates conversations where writers with different perspectives question a topic expert grounded in internet sources, (3) curates collected information into an outline, (4) generates full article with citations. 25% improvement in organization and 10% in coverage breadth vs. baseline.
- **Pipeline coverage**: Pre-writing research, outline generation, article writing.
- **Open source**: Yes (GitHub: stanford-oval/storm).
- **Limitations**: Generates magazine/encyclopedia-style articles, not formal systematic reviews. Quality below carefully human-edited articles.

### 2.9 Karpathy's autoresearch

- **What it does**: 630-line Python script that lets an AI agent autonomously run ML experiments on a single GPU overnight. Released March 6, 2026; hit 30,307 GitHub stars in one week.
- **Methodology**: Autonomous experiment loop: modify code, train for 5 min, check if result improved, keep or discard, repeat. ~12 experiments/hour, ~100 experiments overnight. Found ~20 additive improvements in 700 runs, achieving 11% efficiency gain on the "Time to GPT-2" leaderboard.
- **Pipeline coverage**: Experimental research only (no literature review component). Focused on ML training optimization.
- **Limitations**: Narrow domain (LLM training). Not a literature review tool. Demonstrates the concept of autonomous research loops rather than literature synthesis.

### 2.10 DeepResearchAgent (SkyworkAI)

- **What it does**: Hierarchical multi-agent system for deep research and general-purpose task solving.
- **Methodology**: Top-level planning agent coordinates specialized lower-level agents (Deep Analyzer, Deep Researcher, Browser Use Agent, MCP Manager). Supports multiple LLM providers and local models.
- **Pipeline coverage**: Research planning, web/browser research, analysis, report generation.
- **Open source**: Yes (GitHub: SkyworkAI/DeepResearchAgent).
- **Limitations**: General-purpose rather than academic-specific. No formal protocol support.

---

## 3. "Deep Research" Features from Major AI Labs

### 3.1 OpenAI Deep Research (ChatGPT)

- **What it does**: Autonomous research agent within ChatGPT that spends up to 30 minutes conducting comprehensive web investigations. Produces 20-40 page reports with 75+ citations.
- **Methodology**: Multimodal analysis (text, images, PDFs). Adjusts research path in real-time based on findings. Uses agentic browsing -- the model decides what to search, read, and synthesize.
- **How it compares to systematic review**: The output resembles "graduate-level research" with detailed analysis and citations. However, it does not follow any formal protocol (PRISMA, Kitchenham), does not produce PRISMA flow diagrams, does not support reproducible search strategies, and the search process is opaque.
- **Limitations**: 10 deep research queries per week on Plus ($20/month). No reproducibility -- cannot re-run the same search. Citation accuracy is unverified. Not designed for evidence synthesis per formal standards.

### 3.2 Google Deep Research (Gemini)

- **What it does**: Generates structured research reports from web sources. Users can review and modify the research plan before execution. Switched to Gemini 2.5 Pro Experimental in 2025, significantly improving quality.
- **Methodology**: Follows a structured research plan (user-reviewable). Text-based only (no image/PDF analysis unlike OpenAI). Typically produces shorter reports (~6 minutes, ~29 sources) compared to OpenAI.
- **How it compares to systematic review**: Produces "well-organized undergraduate synthesis" level output. More transparent than OpenAI (shows the plan), but still not protocol-driven.
- **Limitations**: Text-only analysis. Shorter, more surface-level reports than OpenAI. Free with Gemini; higher limits with Gemini Advanced ($20/month).

### 3.3 Perplexity Deep Research

- **What it does**: Multi-pass querying and cross-verification. Searches peer-reviewed journals, .gov/.edu domains. Produces structured synthesis with source links.
- **Methodology**: Automated source aggregation, claim cross-verification, uncertainty annotation. Partnerships with Wiley and other publishers (May 2025) for enhanced peer-reviewed access. Can retrieve 100+ cited studies in under 4 minutes.
- **How it compares to systematic review**: More search-focused than OpenAI/Google. Better academic source access. Still not protocol-driven.
- **Limitations**: Pro subscription ($20/month) required. No reproducibility guarantees. Citation accuracy varies.

### 3.4 Claude Research (Anthropic)

- **What it does**: Agentic research mode that conducts multiple searches building on each other, explores different angles automatically, and produces cited answers.
- **Methodology**: Multi-step agentic search with citation-backed responses. Available on Claude Pro.
- **How it compares to systematic review**: Can be configured for structured reviews (one GitHub project reports a "13-agent research team with Socratic guided mode + systematic review / PRISMA" configuration). Post-publication audits found a 31% error rate in references that passed 3 rounds of integrity checks.
- **Limitations**: Paid-only. Citation accuracy concerns. Not natively protocol-aware.

### 3.5 Google NotebookLM

- **What it does**: AI research tool that works over user-uploaded sources (up to 50). Generates Q&A, audio overviews, mind maps, flashcards. Added Deep Research in Nov 2025. 17M monthly active users by late 2025.
- **Methodology**: Grounded in user-provided sources only (unlike ChatGPT, does not search the web unless Deep Research is used). This means responses are more reliable for the given corpus but limited to what the user uploads.
- **How it compares to systematic review**: Not a review tool per se. Useful for synthesis over a curated paper collection. Deep Research adds web search capability.
- **Limitations**: Bounded by uploaded sources. No systematic search capability in base mode.

### 3.6 Summary Comparison of "Deep Research" Features

| Feature | OpenAI | Google Gemini | Perplexity | Claude | NotebookLM |
|---|---|---|---|---|---|
| Report length | 20-40 pages | 5-15 pages | 5-15 pages | Variable | Variable |
| Sources per report | 75+ | ~29 | 100+ | Variable | Up to 50 (uploaded) |
| Multimodal | Yes (text, image, PDF) | Text only | Text | Text | Text, audio, video |
| User control over plan | No | Yes (review/modify) | No | No | N/A |
| Academic source focus | General web | General web | Academic + web | General web | User-provided |
| Formal protocol support | None | None | None | None | None |
| Free tier | No ($20/month) | Yes | No ($20/month) | No | Yes |

**Key finding**: None of these "Deep Research" features follow formal systematic review protocols (PRISMA, Kitchenham). They produce impressively long reports, but they lack reproducibility, transparent search strategies, and formal quality assessment -- all of which are requirements for publishable systematic reviews.

---

## 4. Academic AI Tools: 2025-2026 Launches and Commentary

### 4.1 Notable Launches and Updates

- **Elicit API** (March 2026): Programmatic access to 138M+ papers and report generation.
- **Elicit Research Agents** (Dec 2025): Autonomous agents for broad topic exploration, competitive landscapes. Integrated Claude Opus 4.5.
- **Consensus Deep Search** (2025): Multi-agent system using GPT-5 for full literature review reports.
- **Scite Patent Search** (Jan 2026): Mixed patent+paper search in private beta.
- **Litmaps + Research Rabbit partnership** (Oct 2025): Consolidation in the citation mapping space.
- **OpenScholar** (published Nature, Feb 2026): Open-source scientific Q&A that beats GPT-4o on citation accuracy.
- **Kosmos / Edison Scientific** (Nov 2025): $70M seed for autonomous scientific discovery. Successor to Robin.
- **ASReview LAB v.2** (2025): Multi-agent, multi-oracle collaborative screening.
- **Karpathy's autoresearch** (March 2026): 630-line autonomous ML experiment loop. 30K+ stars in one week.

### 4.2 Commentary from Academic Influencers

**Sebastian Raschka** (Ahead of AI, Dec 2025): In his "State of LLMs 2025" review, Raschka noted that MCP (Model Context Protocol) has become the standard for tool and data access in agent-style LLM systems, which directly enables research agents to connect to academic databases. He covered the broader shift toward agentic systems but did not publish a dedicated review of research assistant tools.

**Andrej Karpathy** (March 2026): Released autoresearch, demonstrating autonomous ML experimentation. Called it "the final boss battle" and predicted "all LLM frontier labs will do this." Previously coined "vibe coding" (Feb 2025) and expressed concern about the rapid pace of change: "I've never felt this much behind as a programmer."

**Lilian Weng** (OpenAI, Lil'Log): Her foundational 2023 post "LLM Powered Autonomous Agents" (Agent = LLM + memory + planning + tool use) remains the canonical reference. Her May 2025 post "Why We Think" covers test-time compute and reasoning, which underlies the "deep thinking" capabilities in research agents. No dedicated post on research assistant tools found.

**Elvis Saravia** (DAIR.AI): Maintains the widely-used Prompt Engineering Guide and curates "Top ML Papers of the Week." Teaches courses on LLM applications covering tools like LangChain, LlamaIndex, and agent frameworks. No dedicated 2025-2026 survey of research assistant tools found, but his curation work tracks the space closely.

### 4.3 Key Academic Papers (2024-2026)

| Paper | Year | Key Contribution |
|---|---|---|
| "LLMs as a tool in literature reviews: an LLM automated systematic review" (JAMIA) | 2024 | 172 studies surveyed; 73.2% use GPT-based LLMs. ChatGPT dominant. |
| "From Automation to Autonomy" (EMNLP 2025) | 2025 | Three-level taxonomy (Tool/Analyst/Scientist) across 90 research works. |
| "Can Agents Judge SLRs Like Humans?" (arXiv 2509.17240) | 2025 | 27-agent system achieving 84% agreement with expert PRISMA scores. |
| "LiRA: Multi-Agent Framework for Literature Review Generation" (arXiv 2510.05138) | 2025 | Agentic workflow integrating SLR-writing guidelines for readable reviews. |
| OpenScholar (Nature, Feb 2026) | 2026 | Open-source RAG over 45M papers. Beats GPT-4o on citation accuracy. |
| PRISMA-trAIce (JMIR AI, 2025) | 2025 | Discipline-agnostic checklist for transparent reporting of AI use in SLRs. |
| Agent Laboratory (EMNLP 2025 Findings) | 2025 | End-to-end research workflow; 84% cost reduction; human feedback critical. |
| PaperQA2 (FutureHouse, 2024) | 2024 | First agent to beat PhD-level researchers on literature research tasks. |
| STORM (NAACL 2024) / Co-STORM (EMNLP 2024) | 2024 | Multi-perspective pre-writing for Wikipedia-like article generation. |
| Otto-SR (medRxiv, 2025) | 2025 | End-to-end SR agent: 96.7% sensitivity, 93.1% extraction accuracy (vs. human 81.7%/79.7%). |

### 4.4 Hallucination Crisis in AI-Assisted Research

A critical concern across all tools:
- **NeurIPS 2025**: GPTZero found 100+ hallucinated citations across 51 accepted papers that passed peer review.
- **ICLR 2026**: 50+ hallucinated citations found under review, each missed by 3-5 peer reviewers.
- **General LLM citation accuracy**: ChatGPT-3.5 hallucinates 39.6-55% of citations; GPT-4 hallucinates 18-28.6%. Even RAG-based legal tools (LexisNexis, Thomson Reuters) hallucinate 17-33% of the time.
- **Mitigation**: OpenScholar and Consensus represent the strongest approaches -- OpenScholar achieves human-level citation accuracy by grounding in a curated corpus; Consensus searches before synthesizing and never lets the LLM "fill in" beyond retrieved sources.

---

## 5. Systematic Review Automation Tools

### 5.1 ASReview

- **What it does**: Open-source active learning tool for screening. Prioritizes records most likely to be relevant based on previous screening decisions.
- **Methodology**: Active learning loop -- human labels records, ML model re-ranks remaining records by predicted relevance. ASReview LAB v.2 (2025) supports multiple experts ("crowd of oracles") and multiple AI agents (general-purpose, domain-specific, semantic, multilingual transformer models). 24.1% reduction in loss vs. v.1.
- **Pipeline coverage**: Screening prioritization only.
- **Formal protocol support**: Designed for use within PRISMA-compliant reviews. Does not enforce the protocol but supports the screening phase.
- **Limitations**: Only handles screening. No search, no extraction, no synthesis. Requires the user to import records from external databases.
- **Pricing**: Free, open source.

### 5.2 Rayyan

- **What it does**: AI-powered systematic review management platform. 350K+ researchers, 15K organizations, 180 countries.
- **Methodology**: AI learns from inclusion/exclusion decisions and predicts relevance for remaining articles. Supports team collaboration with conflict resolution.
- **Pipeline coverage**: Import, deduplication, screening (with AI), some data extraction.
- **Formal protocol support**: Designed for systematic reviews. Supports PRISMA-style workflow but does not generate PRISMA flow diagrams automatically.
- **Limitations**: AI is screening-focused. No automated search strategy execution, no synthesis, no report generation.
- **Pricing**: Free tier; paid plans for teams.

### 5.3 Covidence

- **What it does**: Most widely used systematic review management platform. Endorsed by Cochrane.
- **Methodology**: RCT Classifier (99.5% sensitivity, trained on 280K+ records) for identifying randomized controlled trials. Relevance Sorting uses active learning to prioritize screening. Attempted LLM-based auto-exclusion but pulled it from production after beta testing showed recall dropping to 66% in some reviews.
- **Pipeline coverage**: Import, deduplication, screening, data extraction, quality assessment, PRISMA flow diagram generation.
- **Formal protocol support**: Explicitly designed for PRISMA-compliant reviews. Aligned with 2025 Cochrane Position Statement on AI and RAISE guidelines.
- **Limitations**: Conservative on AI adoption (deliberately pulled LLM features that didn't meet quality standards). Screening AI is supplementary, not autonomous. RCT classifier evaluated primarily on English biomedical literature.
- **Pricing**: Institutional subscriptions (unlimited reviews/users); individual plans available.

### 5.4 DistillerSR

- **What it does**: Enterprise-grade systematic review platform. Supports 26/30 assessed features in a comprehensive evaluation.
- **Methodology**: AI-driven study selection, data extraction, quality assessment. Can automatically pull references from PubMed at regular intervals.
- **Pipeline coverage**: Search (PubMed auto-pull), screening, data extraction, quality assessment.
- **Formal protocol support**: Designed for formal systematic reviews.
- **Limitations**: Paid subscription required. Less widely adopted than Covidence.

### 5.5 EPPI-Reviewer

- **What it does**: Comprehensive systematic review platform supporting all 6 appraisal features and strong data extraction.
- **Pipeline coverage**: Full systematic review workflow including coding, meta-analysis.
- **Limitations**: Paid subscription. Complex interface.

### 5.6 RobotReviewer

- **What it does**: ML system that auto-extracts risk of bias information from RCT articles.
- **Methodology**: Machine learning and NLP for semi-automated data extraction of RoB 1 elements.
- **Pipeline coverage**: Risk of bias assessment only.
- **Limitations**: Narrow focus. Single-user only. Free but limited.

### 5.7 Laser AI

- **What it does**: Evidence synthesis platform covering screening through extraction.
- **Methodology**: AI-powered ranking by inclusion criteria probability, duplicate detection, automated table detection and data extraction (reduces extraction time by up to 50%).
- **Pipeline coverage**: Screening, data extraction. Database-centric design (not spreadsheet-based).
- **Limitations**: Newer entrant. Less community validation than Covidence/Rayyan.

### 5.8 Otto-SR

- **What it does**: End-to-end agentic systematic review workflow using LLMs. Published 2025.
- **Methodology**: LLM-powered agents handle screening and data extraction. Outperformed dual human workflows: 96.7% sensitivity (vs. 81.7% human), 97.9% specificity (vs. 98.1% human), 93.1% extraction accuracy (vs. 79.7% human).
- **Pipeline coverage**: Search through analysis.
- **Limitations**: Research prototype (medRxiv preprint). Not yet a production tool.

### 5.9 Comparison: Traditional SR Tools vs. Fully Autonomous Approaches

| Dimension | Traditional SR Tools (Covidence, Rayyan, ASReview) | Fully Autonomous (Otto-SR, Agent Laboratory, Elicit SR) |
|---|---|---|
| Human involvement | Human-in-the-loop at every stage | Minimal to none |
| Formal protocol | PRISMA/Cochrane aligned | Usually none |
| Reproducibility | High (documented search strategies) | Low (opaque agent decisions) |
| Screening sensitivity | High (human final decision) | Variable (66-96.7%) |
| Speed | Weeks to months | Minutes to hours |
| Accepted by journals | Yes | Not yet (lacking transparency) |
| Best for | Publishable systematic reviews | Rapid scoping, exploration |

**Key finding**: No fully autonomous system is currently accepted for publishable systematic reviews. The PRISMA-trAIce checklist (2025) attempts to bridge this gap by establishing transparency requirements for AI use in SLRs. The consensus in the field remains that "AI may have a role in assisting humans with evidence synthesis" but "current evidence does not support generative AI use in evidence synthesis without human involvement."

---

## 6. Agent Frameworks Applied to Research

### 6.1 LangGraph / Open Deep Research (LangChain)

- **What it does**: Open Deep Research is an open-source, configurable deep research agent built on LangGraph. Ranked #6 on Deep Research Bench Leaderboard.
- **Architecture**: Multi-agent with research supervisor. Supervisor splits queries into subtopics, spawns sub-agents in parallel, sub-agents search and read, supervisor synthesizes. Three-step process: scoping (user clarification + brief generation), research, writing.
- **Research application**: General-purpose research reports. Supports any LLM provider. MIT license.
- **Limitations**: Not academic-specific. No built-in academic database integration (relies on web search or user-provided MCP connections).
- **GitHub**: langchain-ai/open_deep_research

### 6.2 CrewAI for Literature Review

- **What it does**: Role-based multi-agent orchestration. 280% adoption increase in 2025.
- **Research applications**: Multiple tutorials and implementations for literature review exist (e.g., "Build your Multi-Agent Research Literature Review AI App with CrewAI" on Medium). Users define agents with roles like "Researcher," "Analyst," and "Writer."
- **Academic evaluation**: A systematic comparison of agentic frameworks for scholarly literature processing (SSRN, 2025) found CrewAI provides "predictable" operation via role-based orchestration, while LangGraph offers better state control at higher implementation cost.
- **Paper**: "Exploration of LLM Multi-Agent Application Implementation Based on LangGraph+CrewAI" (arXiv 2411.18241) investigates combining both frameworks.
- **Limitations**: Requires significant setup and prompt engineering. No built-in academic search tools. Quality depends entirely on configuration.

### 6.3 AutoGPT

- **Status**: Pioneered autonomous agents but is "largely obsolete for production use in 2026." The original concept of fully autonomous goal-seeking agents has been superseded by more structured approaches (LangGraph, CrewAI).
- **Research application**: Various early experiments in 2023-2024 used AutoGPT for literature searches, but no significant research-specific projects have survived.

### 6.4 Microsoft AutoGen

- **What it does**: Multi-agent conversation framework. "Task-based conversational systems that manage tasks in a malleable manner."
- **Research applications**: Used in some academic paper analysis projects. Flexible but requires more implementation effort than CrewAI.

### 6.5 Comparative Analysis for Research Use

| Framework | Best For | Research Suitability | Academic Tool Integration | Production Readiness |
|---|---|---|---|---|
| LangGraph | Complex workflows with conditional logic | High (Open Deep Research exists) | Via MCP/tools | High |
| CrewAI | Role-based team simulation | Medium (tutorials exist) | Via custom tools | Medium |
| AutoGPT | Historical interest | Low (obsolete) | None | Low |
| AutoGen | Flexible conversations | Medium | Via custom tools | Medium-High |

---

## 7. Cross-Cutting Analysis

### 7.1 The Pipeline Gap

No single tool covers the entire systematic review pipeline with both formal protocol compliance and AI automation:

```
Search -> Screening -> Extraction -> Quality Assessment -> Synthesis -> Report
  |          |            |              |                    |          |
Elicit    ASReview     Covidence      RobotReviewer       Consensus   STORM
Consensus  Rayyan     DistillerSR                         OpenScholar  LitLLM
Undermind Covidence   Laser AI                            Elicit
```

The closest to "full pipeline" are:
1. **Elicit** (search through report, but low recall for formal SR)
2. **Covidence** (screening through PRISMA diagram, but no AI synthesis)
3. **Otto-SR** (end-to-end but research prototype only)
4. **Consensus Deep Search** (search through structured report, but no screening management)

### 7.2 Taxonomy of Approaches

**Category 1: Citation-Graph Tools** (Research Rabbit, Connected Papers, Litmaps, Inciteful)
- Strength: Reliable discovery based on actual citation relationships
- Weakness: No AI synthesis, no full-text analysis

**Category 2: Semantic Search + Synthesis** (Elicit, Consensus, SciSpace, Undermind)
- Strength: Natural language queries, AI-generated summaries
- Weakness: Variable recall, hallucination risk

**Category 3: Screening Optimizers** (ASReview, Rayyan, Covidence)
- Strength: Formal protocol support, human-in-the-loop
- Weakness: Only cover screening phase, require manual search

**Category 4: Deep Research Agents** (OpenAI, Gemini, Perplexity, GPT-Researcher)
- Strength: Comprehensive reports, fast
- Weakness: Not reproducible, not protocol-compliant, variable citation accuracy

**Category 5: Autonomous Research Systems** (Robin/Kosmos, Agent Laboratory, autoresearch)
- Strength: End-to-end automation
- Weakness: Quality concerns, domain-specific, not accepted for publication

### 7.3 The Reproducibility Problem

The fundamental tension in this space: traditional systematic reviews require reproducible, documented search strategies. AI agents make opaque, non-deterministic decisions. The PRISMA-trAIce checklist (2025) is the first formal attempt to reconcile these, requiring researchers to document:
- Which AI tools were used at which stages
- How AI outputs were verified
- What human oversight was applied

### 7.4 Where the Field Is Heading

1. **Convergence**: Tools are expanding their scope. Elicit is adding agents; Covidence is cautiously adding AI; Consensus is adding deep search. Expect more overlap.
2. **MCP as connective tissue**: Model Context Protocol is becoming the standard for connecting LLM agents to academic databases, enabling research agents to tap into Semantic Scholar, PubMed, arXiv, etc.
3. **Human-AI collaboration, not replacement**: The most successful systems (Agent Laboratory, Covidence, ASReview v.2) keep humans in the loop. Fully autonomous systems produce impressive demos but fail reliability thresholds for formal research.
4. **Open source closing the gap**: OpenScholar, PaperQA2, STORM, GPT-Researcher, and LangChain's Open Deep Research provide open-source alternatives that are increasingly competitive with commercial offerings.
5. **Citation accuracy as the critical bottleneck**: Hallucinated citations remain the single biggest obstacle. Systems that ground in a curated corpus (OpenScholar, Consensus, Scite) perform better than those that synthesize from general knowledge.

---

## Sources

### Dedicated Research Tools
- [Elicit](https://elicit.com/)
- [Elicit AI Research Tool Review and New Features (Dec 2025)](https://scrollwell.com/guide/tools/elicit-ai-research-tool-review-new-features-2025/)
- [Comparison of Elicit AI and Traditional Literature Searching -- Cochrane Evidence Synthesis and Methods](https://onlinelibrary.wiley.com/doi/full/10.1002/cesm.70050)
- [Consensus: AI for Research](https://consensus.app/)
- [Consensus uses GPT-5 and the Responses API -- OpenAI](https://openai.com/index/consensus/)
- [Consensus Deep Search](https://consensus.app/home/blog/deep-search/)
- [Scite AI](https://scite.ai/)
- [Scite AI Review 2026](https://effortlessacademic.com/scite-ai-review-2026-literature-review-tool-for-researchers/)
- [SciSpace](https://scispace.com/)
- [Research Rabbit](https://www.researchrabbit.ai/)
- [Connected Papers](https://www.connectedpapers.com/)
- [Litmaps](https://www.litmaps.com/)
- [Inciteful](https://inciteful.xyz/)
- [Semantic Scholar](https://www.semanticscholar.org/)
- [Semantic Scholar Review 2025](https://skywork.ai/blog/semantic-scholar-review-2025/)
- [Undermind](https://www.undermind.ai/)
- [Scholarcy](https://www.scholarcy.com/)

### LLM-Based Research Agents
- [OpenScholar -- University of Washington / AI2](https://openscholar.ai/)
- [OpenScholar paper (arXiv 2411.14199)](https://arxiv.org/abs/2411.14199)
- [PaperQA2 (GitHub: Future-House/paper-qa)](https://github.com/Future-House/paper-qa)
- [FutureHouse / Robin](https://www.futurehouse.org/research-announcements/demonstrating-end-to-end-scientific-discovery-with-robin-a-multi-agent-system)
- [LitLLM (GitHub)](https://github.com/LitLLM/LitLLM)
- [LitLLMs paper (arXiv 2412.15249)](https://arxiv.org/html/2412.15249)
- [Agent Laboratory (arXiv 2501.04227)](https://arxiv.org/abs/2501.04227)
- [AgentRxiv (arXiv 2503.18102)](https://arxiv.org/abs/2503.18102)
- [GPT-Researcher (GitHub)](https://github.com/assafelovic/gpt-researcher)
- [STORM (Stanford)](https://storm-project.stanford.edu/research/storm/)
- [Karpathy autoresearch (GitHub)](https://github.com/karpathy/autoresearch)
- [Karpathy autoresearch -- VentureBeat](https://venturebeat.com/technology/andrej-karpathys-new-open-source-autoresearch-lets-you-run-hundreds-of-ai)
- [DeepResearchAgent (SkyworkAI, GitHub)](https://github.com/SkyworkAI/DeepResearchAgent)
- [AutoResearchClaw (GitHub)](https://github.com/aiming-lab/AutoResearchClaw)

### Deep Research Features
- [OpenAI vs Google Deep Research comparison](https://www.sectionai.com/blog/chatgpt-vs-gemini-deep-research)
- [AI Deep Research Tools Compared (AI IXX)](https://aiixx.ai/blog/ai-deep-research-tools-compared-gemini-openai-and-perplexity)
- [Perplexity Deep Research Review 2026](https://www.secondtalent.com/resources/perplexity-deep-research-review/)
- [Claude Research](https://claude.com/blog/research)
- [NotebookLM Deep Research (Google Blog)](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-deep-research-file-types/)
- [Gemini 2.5 Pro Deep Research -- Hacker News](https://news.ycombinator.com/item?id=43662468)
- [OpenAI Deep Research comparison (Helicone)](https://www.helicone.ai/blog/openai-deep-research)

### Systematic Review Automation
- [ASReview](https://asreview.nl/)
- [ASReview LAB v.2 (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12416088/)
- [Rayyan](https://www.rayyan.ai/)
- [Covidence](https://www.covidence.org/)
- [Covidence AI Screening Approach](https://www.covidence.org/blog/ai-screening-automation-systematic-reviews/)
- [Laser AI](https://www.laser.ai/)
- [Otto-SR (medRxiv)](https://www.medrxiv.org/content/10.1101/2025.06.13.25329541v1.full)
- [AI Tools for Systematic Reviews 2026 (Atlas)](https://www.atlasworkspace.ai/blog/ai-systematic-review-tools)

### Agent Frameworks
- [LangChain Open Deep Research](https://blog.langchain.com/open-deep-research/)
- [Open Deep Research (GitHub)](https://github.com/langchain-ai/open_deep_research)
- [CrewAI Literature Review (Medium)](https://medium.com/@nimritakoul01/build-your-multi-agent-research-literature-review-ai-app-with-crewai-68a25754d889)
- [LangGraph+CrewAI paper (arXiv 2411.18241)](https://arxiv.org/abs/2411.18241)
- [Systematic Comparison of Agentic AI Frameworks for Scholarly Literature Processing (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5484727)

### Academic Surveys and Protocols
- [From Automation to Autonomy survey (EMNLP 2025, arXiv 2505.13259)](https://arxiv.org/abs/2505.13259)
- [PRISMA-trAIce checklist (JMIR AI, 2025)](https://ai.jmir.org/2025/1/e80247)
- [LLMs as tools in literature reviews (JAMIA, 2024)](https://academic.oup.com/jamia/article/32/6/1071/8126534)
- [Can Agents Judge SLRs Like Humans (arXiv 2509.17240)](https://arxiv.org/abs/2509.17240)
- [LiRA (arXiv 2510.05138)](https://arxiv.org/html/2510.05138v1)
- [NeurIPS hallucinated citations (GPTZero)](https://gptzero.me/news/neurips/)
- [ICLR 2026 hallucinations (GPTZero)](https://gptzero.me/news/iclr-2026/)

### Influencer Commentary
- [Sebastian Raschka -- State of LLMs 2025](https://magazine.sebastianraschka.com/p/state-of-llms-2025)
- [Lilian Weng -- LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)
- [Lilian Weng -- Why We Think (May 2025)](https://lilianweng.github.io/posts/2025-05-01-thinking/)
- [Elvis Saravia / DAIR.AI Prompt Engineering Guide](https://github.com/dair-ai/Prompt-Engineering-Guide)
- [Karpathy autoresearch -- Fortune](https://fortune.com/2026/03/17/andrej-karpathy-loop-autonomous-ai-agents-future/)
