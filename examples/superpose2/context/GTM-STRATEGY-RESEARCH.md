# Superpose GTM Strategy — Single Source of Truth

**Last Updated:** 2026-02-13 (Alternative verticals explored beyond insurance. 9 verticals evaluated across 33+ sub-agent searches + 15+ direct searches. Accounting/Tax ranked #1, Healthcare Prior Auth #2. Insurance deprioritized per founder preference.)
**Status:** Vertical exploration expanded beyond insurance. Accounting/Tax emerges as top alternative: Accrual ($75M, just launched Feb 2026), Accordance ($13M seed), Fieldguide ($75M Series C, $700M val) prove market timing. Healthcare prior auth/denial management is #2. Legal too crowded (Harvey $11B). Financial services sales cycles too long. Gov/defense inaccessible at pre-seed.
**Classification:** CONFIDENTIAL — Internal Only

> **Reference appendices (not merged, kept separately):**
> - `research/GTM-STRATEGY-DETAILS.md` — Detailed analysis (market sizing, competitive landscape, product spec, pricing, Plan B evaluation, insurance AI deep dive)
> - `research/QUBO-OPPORTUNITY-MAP.md` — Full QUBO opportunity rankings across 13 areas
> - `research/TRAINING-PIPELINE-DEEP-DIVE.md` — Training pipeline stages, where DatologyAI operates, SFT vs CPT analysis
> - `research/raw/` — All raw search outputs indexed in `research/INDEX.md`

---

## 1. Executive Summary

**The one-page story for Siinn:**

Superpose leverages **quantum computing to accelerate AI workloads** — faster, better, or cheaper than classical methods. We're paradigm-agnostic: both **quantum annealing** (D-Wave, combinatorial optimization) and **gate-based QC** (IBM, Quantinuum, IonQ — molecular simulation, variational algorithms) are in scope. We're searching for the right product/market.

**Core thesis:** Many ML pipeline steps are secretly combinatorial optimization problems — selecting training data, pruning neural networks, choosing features, optimizing model architecture. These map naturally to QUBO (Quadratic Unconstrained Binary Optimization), which is what D-Wave quantum annealers are built to solve. Where classical methods use greedy heuristics, QUBO can jointly optimize.

**What we know so far:**
- **Academic validation is real and growing.** SIGIR 2024: QUBO-based instance selection for transformer fine-tuning (28% data reduction, competitive accuracy). QuantumCLEF 2025: live competition using D-Wave for Llama 3.1 fine-tuning. Multiple papers on QUBO for feature selection, clustering, NN compression.
- **New validations (Feb 2026 breadth campaign).** Nature Scientific Reports Oct 2025 (Otsuka et al.): D-Wave QA for mislabeled data detection — peer-reviewed, real hardware. arxiv 2511.02785: QUBO formulation for federated learning client selection, 33% reduction in privacy attacks, tested on D-Wave. QR-LLM (Kipu Quantum): LLM reasoning as HUBO/QUBO, run on D-Wave. ICML 2025 "Less is More": DPO preference selection explicitly called "intractable combinatorial optimization."
- **Industry adoption is early but real.** VW (traffic routing with D-Wave, Lisbon pilot), DENSO (factory logistics, 30% vehicle reduction), D-Wave's own Crafto (feature selection outperforms 2 classical methods).
- **Product surface area is wider than expected but shallower than hoped.** Breadth exploration identified **6 new product directions** beyond the original 5, bringing total to 11 (see §1a). However, **5 out of 5 deep dives resulted in downgrades.** Directions killed: B (compression), G (GPU scheduling). Directions downgraded: A (7→4), F (8→6), H (7→4). The pattern: at ML pipeline problem scales, classical methods are good enough. QUBO advantage is marginal or nonexistent.

**Honest odds:** ~5–8% probability of becoming $100M+ company *as a quantum company*. **Every deep dive (9/9) has resulted in a downgrade.** No ML direction above 6/10. The core finding: at ML pipeline problem scales, classical solvers are good enough. **However, as a classical company (Plan B), odds improve to ~15-25%.** The product spec, market, and pricing work without quantum — quantum was a differentiator that didn't differentiate. See §15.

**Where QA DOES work (new finding, Feb 11):** Non-ML combinatorial optimization — manufacturing scheduling (Ford Otosan: 30min→5min), telecom (NTT DOCOMO: 15% congestion reduction), defense (Anduril/Davidson: 10x faster, 9-12% better threat mitigation in 500-missile sim), finance (CaixaBank: 90% faster portfolio hedging). Sweet spot: binary decisions × 100-5K variables × speed matters more than optimality. ML problems fail this sweet spot on 3 dimensions (too small/too large, continuous, eval-dominated).

**Plan B (increasingly likely, now validated by insurance AI deep dive — see §15 and §16):** Drop quantum, keep privacy-first fine-tuning with classical optimization. Two viable paths: (B1) Privacy-first FTaaS platform with classical curation, or (B5) Vertical insurance AI company ("Harvey AI for Insurance"). Recommended: combine both — B5 as GTM, B1 as technical platform. **Plan C:** Pivot to non-ML QUBO applications (defense, logistics, scheduling) — requires domain expertise Superpose doesn't have.

**Key Plan B insight:** The product spec in §6 is *already correct* — just replace D-Wave with Gurobi/submodular optimization. The privacy-first, deploy-in-your-cloud architecture is the real product. Quantum was a differentiator that didn't differentiate.

**Insurance AI landscape validation (Feb 11–12):** The "Harvey AI for Insurance" positioning is confirmed viable. AI in insurance market: $10.3B (2025) → $35.8B (2029). 90% of insurance C-suite evaluating GenAI. ~24 states adopted NAIC AI bulletin. Fine-tuned LLMs beat generic by 30% (EXL proof point). **No company occupies the "fine-tuning platform for insurance" niche — every competitor (Roots, FurtherAI, Sixfold) builds workflow automation powered by AI, not a platform for carriers to fine-tune their own models.** However: Roots ($43.9M, $9.5M rev, 35 customers) has massive data moat (250M+ docs). FurtherAI ($35.6M, a16z) is aggressively targeting MGAs. Anthropic signing direct carrier deals. See competitive map below and `raw/2026-02-12-roots-automation-insurance-gtm-*.md`.

**MVP technical feasibility validated (Feb 12):** EXL proved fine-tuned Llama 3.1-8B beats GPT-4/Claude 3.5/Gemini 1.5 with only 13,500 training records (LoRA rank 32, Q/K/V, 2x H100). Roots open-sourced GutenOCR (Qwen2.5-VL fine-tuned OCR, Apache-2.0) — their OCR moat is gone. **Critical opportunity: no English insurance NLP benchmark exists** (InsQABench is Chinese-only, INS-MMBench is multimodal/vision). Superpose can create "InsurBench" — first mover defines the standard. Public training data sources identified: SERFF rate filings (richest insurance text), SEC EDGAR insurance 10-Ks (6B+ token corpus), FEMA NFIP claims (2.7M records). Bessemer's vertical AI playbook warns: "data extraction becomes table stakes" — defensibility requires workflow embedding + compliance architecture, not just fine-tuning. See §17 (new) and `raw/2026-02-12-insurance-mvp-technical-*.md`.

**Architecture validation from energy sector (Feb 12, v3):** Studying Chevron/ADNOC/EnergyLLM/EnergyGPT fine-tuning architectures confirms: (1) 8B-class models + LoRA SFT is the converging enterprise recipe, (2) synthetic data generation from domain corpus is validated (EnergyLLM uses Mistral-Nemo for QA pair generation), (3) SME-in-the-loop evaluation is mandatory, (4) MIT study shows vendor-built AI succeeds 67% vs 22% for internal builds — strong platform validation. ADNOC's $340M ENERGYai contract proves $100M+ AI budgets exist in regulated industries.

**Gate-based QC exploration (Feb 12):** Expanded scope beyond quantum annealing to gate-based quantum computing (IBM, Google, IonQ, Quantinuum). Explored whether Chevron/energy could be a customer for quantum molecular simulation (catalysis, carbon capture, reservoir modeling) rather than NLP/fine-tuning. **Result: Gate-based QC does NOT create a viable unicorn path for Superpose at pre-seed stage.** Key findings: (1) All quantum chemistry simulation is pre-revenue globally — zero enterprises paying for this as a service. (2) Competitors are impossibly well-funded: Quantinuum ($10B valuation, $115M revenue, 561 employees), SandboxAQ ($5.75B, $950M raised, Alphabet spinout). (3) Chevron invested in OQC ($100M Series B, Mar 2024) for catalysis/materials — but as INVESTOR, not buyer. Same pattern as FTaaS rejection. (4) Timeline: BCG says broad quantum advantage 2030-2040. Chemical-precision simulation requires millions of qubits. (5) Would require a completely different company: PhD quantum chemists, $50M+ funding, 5+ years R&D. Superpose has none of this. (6) Zapata AI (quantum ML startup, $67M raised, Harvard spinout) went bankrupt Oct 2024 — cautionary tale. **Gate-based QC is a viable Series B/C strategy (post-$15M raise), not a pre-seed strategy.** See §1b for full analysis.

**Dead ideas revisited (Feb 12):** Systematically re-evaluated ALL killed/downgraded directions with a "what can we engineer?" mindset. Studied unicorn patterns (Harvey: $0→$100M ARR in 3 years, $11B valuation; Cursor: $1B ARR in 24 months with 12 people; EvenUp: $2B valuation via narrow wedge + data curation; Lovable: $100M ARR in 8 months). Key frameworks: BVP's 10 Principles for Vertical AI, Scale VP's AI Verticals framework. **Result: Insurance AI (Plan B5) REINFORCED as correct strategy.** None of the killed quantum/ML directions become viable by "combining" them — but ALL become features of the insurance AI platform. The platform should emerge from the vertical (EvenUp model), not the other way around. New competitive intelligence: Predibase acquired by Rubrik (~$100M, Jun 2025) creating gap in privacy-first fine-tuning; Snorkel AI at $148M revenue ($1.3B valuation); Multiverse Computing proved quantum-INSPIRED can reach €100M ARR on classical hardware but requires $250M+ and world-class tensor network researcher (unreplicable at $3M). Mathematical optimization market only $1.85B with 93% held by Gurobi/FICO/IBM — OaaS path rejected. Defense quantum software fully captured by SandboxAQ ($950M). One new idea: use "quantum-informed optimization" as investor NARRATIVE (not product) for data curation — quantum math differentiation without hardware dependency.

**This week:** Experiment still running (Qwen2.5-3B → gpt-oss-20b). If QUBO wins by >10% over GRAPE, quantum stays in the stack. If not, execute Plan B immediately.

---

## 1a. Product Directions Under Evaluation
<!-- Last updated: 2026-02-11 — Expanded after breadth exploration campaign (6 new directions added) -->

We are evaluating 11 product directions. Each is scored on QUBO fit, market size, competitive landscape, and feasibility. Directions A–E are original; F–K were discovered in the Feb 2026 breadth campaign. Old Direction E has been upgraded to Direction F with new evidence.

### Direction A: SFT Data Curation — 4/10 ⬇️ (downgraded from 7 after deep dive)
<!-- Last updated: 2026-02-11 — Deep dive validation -->
**What:** Select optimal training data subsets for fine-tuning LLMs. Deploy on customer's cloud for privacy.
**QUBO fit:** ⭐⭐⭐⭐⭐ — Natural QUBO. **But the problem isn't hard enough at SFT scale for quantum to matter.**
**Market:** Privacy-first fine-tuning TAM $4–8B (2025) → $16–25B (2030). But data *selection* as standalone is $50–200M. Pricing pressure from open-source.
**Kill factors:** (1) Classical baselines excellent (GRAPE: O(n log n), SOTA). (2) Problem not hard enough — Gurobi handles 50K vars. (3) DatologyAI one product decision away ($57.6M). (4) Feature, not product. (5) Quantum is a liability at this scale.
**Status:** Experiment running. **Downgraded.** Detail in `GTM-STRATEGY-DETAILS.md` §2–§10.

### Direction B: Model Compression/Pruning — 2/10 ❌
**What:** QUBO for NN pruning/quantization for edge deployment.
**Market:** Edge AI $25B (2025) → $57–143B. Massive but consolidating (Neural Magic→IBM, Deci→NVIDIA).
**Honest assessment:** Math works but D-Wave can't handle even small CNNs. Block decomposition makes subproblems classically trivial. Market consolidating into chip vendors bundling compression free.
**Status:** **KILLED.** Detail in `GTM-STRATEGY-DETAILS.md`.

### Direction C: Feature Selection — 3/10
**What:** QUBO-based feature selection. D-Wave already has this (Crafto, scikit-learn plugin).
**Honest assessment:** 3/10 standalone. D-Wave gives this away free. Market too small for a startup. Useful as feature within other products.

### Direction D: Multi-Task Mixture Optimization — 3/10 ⬇️ ❌
**What:** QUBO for optimal data mixture across tasks.
**QUBO fit:** ⭐ — **WRONG FORMALISM.** Continuous optimization, not binary. Field moving to model merging instead.
**Status:** **KILLED.**

### Direction F: DPO/RLHF Preference Data Selection — 6/10 (downgraded from 8)
**What:** Select optimal preference pairs for alignment. ICML 2025 calls it "intractable combinatorial optimization."
**Reality:** Current heuristics (score → sort → top-k, O(n log n)) already work well. Marginal QUBO improvement 1-2%.
**Status:** Valid but quantum advantage uncertain. Keep as Direction A extension, not primary bet.

### Direction G: GPU/Inference Scheduling — 3/10 ❌ (was 7)
**What:** Assign AI workloads to GPU resources. Textbook QUBO.
**Market:** $106-134B inference market. Enormous.
**Fatal:** (1) Practical scheduling needs millions of vars (D-Wave: 4400 qubits). (2) Needs <10ms latency (D-Wave: 5s min). (3) GPU scheduling is online streaming, not batch — RL is the natural fit. (4) NVIDIA vertically integrating.
**Status:** **KILLED.** Market huge but QUBO is wrong tool.

### Direction H: Mislabeled Data Detection — 4/10 (was 7)
**What:** QUBO to identify mislabeled training samples.
**Reality:** Nature paper tested on 128 binary samples with logistic regression. Cleanlab (free, open-source) already works at ImageNet scale.
**Status:** Downgraded. Good PR, not a product path.

### Direction I: Model Merging Optimization — 4/10 ⬇️ (was 5)
**What:** QUBO for optimal merge recipes across fine-tuned models.
**QUBO fit:** ⭐⭐⭐⭐ — Best mathematical QUBO fit of all directions.
**Fatal:** Practical problem sizes are 100-160 vars (trivial for classical). Eval cost dominates — quantum speedup on the millisecond search step is irrelevant.
**Status:** Downgraded. Best math, wrong scale.

### Direction J: Federated Learning Client Selection — 3/10 ❌ (was 5)
**What:** QUBO for optimal FL client selection.
**Fatal:** Cross-silo FL <100 clients (trivial). Cross-device FL millions (too large). Sweet spot doesn't exist. FL market tiny ($140-190M). DivFL (submodular greedy) already works.
**Status:** **KILLED.** 8/8 deep dives = downgrades.

### Direction K: Synthetic Data Curation — 3/10 ❌
**What:** QUBO for selecting from synthetic data pools.
**Fatal:** Mathematically identical to Direction A (killed). Zero QUBO papers. Market value is in generation (NVIDIA/Gretel $320M+), not selection.
**Status:** **KILLED.** 9/9 deep dives = downgrades.

### What's NOT a Direction
- **Pre-training data curation** — DatologyAI's lane, petabyte scale, wrong for D-Wave
- **HPO via quantum** — No evidence of beating Bayesian optimization
- **Quantum RL** — Too early, doesn't scale
- **NAS** — Natural QUBO fit but no D-Wave results, market unclear
- **EDA/Chip Placement** — 2/10. Millions of vars needed. Synopsys/Cadence duopoly.
- **Green AI** — 2/10. D-Wave 12.5kW for problems a laptop solves. Google/Microsoft already solve carbon-aware scheduling with heuristics.
- **Defense** — Davidson Technologies has on-prem Advantage2 for DoD. Anduril collaboration is real (10x speed, 9-12% better). But requires clearances + domain expertise Superpose lacks.

### Non-ML QUBO Applications: Where QA Actually Works (Feb 11)

**After 9/9 ML direction downgrades: QA delivers commercial value in logistics, scheduling, defense, and finance — NOT ML.**

| Customer | Domain | Result | Status |
|----------|--------|--------|--------|
| Ford Otosan | Manufacturing scheduling | 30min → <5min | ✅ Production |
| NTT DOCOMO | Telecom paging | 15% congestion reduction | ✅ Production |
| Pattison Food Group | Employee scheduling | 80% less manual effort | ✅ Production |
| Anduril/Davidson | Missile defense | 10x faster, 9-12% better | PoC (Jan 2026) |
| CaixaBank | Portfolio optimization | 90% faster | PoC → Expanded |
| BASF | Manufacturing | "Significantly better than classical-only" | PoC (Nov 2025) |

**QA Sweet Spot:** Binary decisions × 100-5K vars × Hard constraints × Speed > Optimality × Repeated batches

**Why ML fails:** (1) Wrong scale. (2) Problems are continuous. (3) Eval cost dominates search cost.

**D-Wave reality:** $8.8M total revenue FY2024. Kerrisdale Capital short thesis: "commercial dead end."

**Implication:** Domains where QA works require domain expertise we don't have. We'd compete with D-Wave's own services.

### Vertical Exploration: Oil & Gas (Chevron) — REJECTED WITH MAXIMUM CONFIDENCE (Feb 12)
<!-- Last updated: 2026-02-12 — After v3 final validation (110+ total searches across 4 engines, 30+ page reads). All angles exhausted. -->

**Question:** Is Chevron / oil & gas a viable second vertical after insurance for Superpose's privacy-first fine-tuning platform?

**Answer: NO. Do not pursue. EXHAUSTIVELY VALIDATED.** Four rounds of research (v1, v2, architecture lessons, v3 final validation) across 110+ searches confirm: oil & gas is structurally wrong for FTaaS at every tier — supermajors, OFS companies, mid-market E&P, and subsidiaries. No wedge found. No 2026 developments change the verdict.

**Why Chevron/O&G fails as a customer target:**

| Factor | Finding | Implication |
|--------|---------|-------------|
| **Build vs Buy** | Chevron has in-house Enterprise AI team (led by Justin Lo), built ApEX (gen AI exploration platform, 1M+ docs, multi-agent), APOLO (drilling optimization). "AI scientists constantly fine-tuning models." $1B Bengaluru ENGINE hub (1,000+ AI/ML professionals). | They build, not buy. No external FTaaS procurement pattern exists at any supermajor. |
| **CPChem builds internally too** | CPChem (separate entity) has 400-person digital/AI team under Allison Martinez (SVP Digital & AI) and Brent Railey (CDAO, 19yr tenure). Databricks + Azure + Capgemini. Cross-functional Gen AI Task Force. "Mature stage in traditional ML workflows." | Even subsidiaries with separate leadership build in-house. |
| **OFS companies build platforms** | SLB: Lumi platform + Mistral AI (primary LLM) + NVIDIA NeMo. Baker Hughes: Cordant + C3.ai + Microsoft Azure AI Foundry. Halliburton: DS365.ai + FPT (150+ devs). All fine-tune in-house. | OFS companies are becoming AI PLATFORMS for the industry, not buyers of external fine-tuning. SLB Lumi is the emerging O&G AI standard. |
| **CNE ≠ AI consumer** | Chevron New Energies (Jeff Gustavson, President) focused on POWERING AI data centers (GE Vernova partnership, 4 GW target, $1.5B lower-carbon capex). Not using fine-tuned AI for energy transition. | Energy transition is an AI power supply play, not an AI consumption play. |
| **Cloud lock-in** | Azure is primary cloud (7-year deal). Microsoft Copilot, Form Recognizer, IoT Ops already deployed. Google AutoML Vision for doc classification. | Azure/AWS already offer native fine-tuning. Privacy-first pitch redundant when customer has Azure sovereign cloud. |
| **CTV pathway** | CTV: $90M Core Fund (Series A-C), $100K-$300K Catalyst, $500K Chevron Studio. 140+ investments. Every portfolio company has deep domain expertise: Thoughttrace (O&G contracts, acq. by Thomson Reuters 2022), NobleAI ($17M+ Series A, chemistry/materials), Kiana Analytics (industrial IoT/safety). | Generic FTaaS platform without O&G workflows won't pass CTV's evaluation. Jim Gable (CTV President) requires "laser-focused value proposition" and domain differentiation. |
| **Chevron buys specialized, not generic** | Chevron procures external AI: Thoughttrace ($10M CTV invest, 15M files for contract analytics), Honeywell (refinery alarm AI, Oct 2024), Publicis Sapient (supply chain Azure, 400+ users), NobleAI (chemistry AI). Pattern: domain-expert vendor solving specific operational problem. ZERO evidence of buying generic platforms. | External AI procurement exists but only for deep-domain tools. |
| **Fine-tuning isn't the problem** | O&G AI spend ($4.0B, 2025) goes to: predictive maintenance, drilling optimization, reservoir simulation, production forecasting. Traditional ML + physics-based models dominate. LLMs used for doc processing + knowledge management only. | Fine-tuning is a small, emerging slice — not the core pain. |
| **Domain models exist** | EnergyLLM (Aramco/SPE/i2k Connect): Llama 3.3 fine-tuned on OnePetro, 1B-70B params, v1.0 Jan 2025. ADNOC ENERGYai: 70B-param LLM. TotalEnergies+Mistral AI joint lab (Jun 2025). SPE plans to license ELLM to operators (ELLM+). | Supermajors fine-tuning own models. SPE becoming distribution channel. |
| **The i2k Connect precedent** | Only confirmed case of a supermajor hiring external LLM fine-tuning: Aramco → i2k Connect (Houston, founded 2013, $1M rev, 10+ yrs energy NLP expertise). MOU Oct 2023 → v1.0 Jan 2025 (2+ years). SPE now distributes the model. | Proves it CAN happen but requires 10+ years domain expertise and still generates only ~$1M revenue. Not venture-scale. |
| **NLP pain points already served** | Lease extraction: Thomson Reuters/Thoughttrace (500+ contract elements), Grooper (30yr O&G, 99% accuracy), nuEra/EAG (90% extraction, 10-sec/doc). Safety: SparkCognition NLP Studio. Well logs: Chevron ApEX (1M+ files, 4TB). | No unserved gap where a pre-seed startup adds value. |
| **Competitor landscape** | SLB ($2.4B digital), Baker Hughes/C3.ai (renewed through 2028, Shell/Eni/QatarEnergy/ExxonMobil/Petronas customers), SparkCognition, Palantir (BP 5yr deal), H2O.ai. ISG 2025: O&G AI leaders are Accenture, IBM, TCS, Wipro — massive SIs, not startups. | Overwhelming. AI services market 66.4% share. |
| **Sales cycle** | 12-24+ months. CTO office → cybersecurity review → IT platform approval → Enterprise AI team assessment → CTV diligence. | Superpose has 15-18mo runway. No time to close. |

**Supermajor comparison — who buys external fine-tuning?**

| Company | External AI Partners | Fine-Tuning Approach | Buys External FTaaS? |
|---------|---------------------|---------------------|---------------------|
| Chevron | Thoughttrace, Honeywell, NobleAI, Microsoft, Google | In-house (ApEX, APOLO, Enterprise AI team) | NO |
| Shell | Shell.ai hackathon, own platform | In-house | NO |
| BP | Palantir (5yr, AIP), Microsoft, Salesforce, RELEX | In-house + Palantir | NO |
| TotalEnergies | Mistral AI (joint lab, Jun 2025, on-prem) | Co-development with Mistral | NO (partnership) |
| ExxonMobil | Snowflake, Honeywell, CoLab ($5.6M) | In-house + hyperscaler tools | NO |
| Aramco | i2k Connect (financed ELLM) | External fine-tuning (1 deal) | YES (one deal, ~$1M company) |

**Result: 1 out of 6 supermajors has ever hired external LLM fine-tuning. That one deal (Aramco/i2k Connect) generated ~$1M revenue from a 10-year domain veteran.**

**Oilfield Services companies — also build in-house (v3, Feb 12):**

| Company | AI Platform | LLM Approach | Buys External FTaaS? |
|---------|------------|--------------|---------------------|
| SLB | Lumi (Sep 2024) | Mistral AI (primary LLM) + NVIDIA NeMo. Seismic foundation model (ViTs) trained from scratch. Coding co-pilot fine-tuned on proprietary data. | NO — building industry platform |
| Baker Hughes | Cordant + Leucipa | C3.ai + Microsoft Azure AI Foundry + AWS/EPAM. JenAii digital assistant. | NO |
| Halliburton | DS365.ai | FPT Software (150+ devs). AI-driven horizontal well automation (2023). | NO |

**Mid-market E&P — no validated evidence of external fine-tuning procurement (v3, Feb 12):** Despite Gemini claiming mid-market firms "actively procure" external fine-tuning, all citations were generic service provider blogs — zero named E&P companies buying FTaaS. Tensorblue (cited by Gemini as O&G FTaaS provider) is a generic AI dev agency with no O&G case studies.

**Key people identified (for reference if ever revisited):**
- Les Copeland (CIO, since Apr 2024, ex-GM)
- Ryder Booth (VP Technology, eff. Jul 2025)
- Justin Lo (Technical Manager, AI Engineering — most relevant for AI vendor evaluation)
- Ellen Nielsen (Chief Data Officer — first CDO, data strategy)
- Jim Gable (President, CTV — startup investment decisions)
- Troy Engstrom (Sr Manager, Digital Carbon Management — supply chain AI)
- Allison Martinez (SVP Digital & AI Officer, Chevron Phillips Chemical)
- Brent Railey (CDAO, CPChem — leads data/AI including GenAI/LLM strategy)
- Jeff Gustavson (President, Chevron New Energies — AI data center power)
- Clay Neff (President, Upstream, eff. Jul 2025)
- Andy Walz (President, Downstream, Midstream & Chemicals)

**What WOULD need to be true for O&G to work (future, post-Series A) — v3 makes this HARDER:**
1. Hire oil & gas domain expert (former subsurface/drilling engineer)
2. Find privacy-first need that Azure sovereign cloud doesn't cover (e.g., on-prem at wellsite, specific national data localization)
3. Demonstrate 30%+ improvement over generic LLMs on specific O&G task (EnergyGPT's 2% is insufficient)
4. Start with mid-market E&P (not supermajor) — but v3 found ZERO evidence mid-market buys external fine-tuning either
5. Compete with SLB Lumi (emerging industry standard platform with Mistral AI + NVIDIA NeMo) — this is a NEW blocker discovered in v3
6. AI in O&G market growing to $14.9B by 2035 (ISG/FMI)

**QA relevance:** None. Chevron's AI problems (NLP, time-series, physics-informed models, RL) are not combinatorial optimization at QUBO scale. Consistent with 9/9 ML direction downgrades.

**Architecture lessons for Superpose's insurance platform (Feb 12, v3):**

While Chevron is NOT a customer target, studying how supermajors structure enterprise fine-tuning yields 6 product-architecture validations:

| Lesson | Source | Implication for Superpose |
|--------|--------|--------------------------|
| **Multi-agent + RAG + fine-tuning** is the enterprise pattern, not fine-tuning alone | Chevron ApEX (multi-agent RAG over 1M+ files, 4TB), ADNOC ENERGYai (agentic AI + LLM + OSDU) | Superpose must deliver fine-tuning AS PART OF a pipeline (OCR → curate → fine-tune → deploy → evaluate), not as standalone |
| **8B models with LoRA** are the industry sweet spot | EXL (Llama 3.1-8B, LoRA rank 32), EnergyLLM (8B runs on laptop), EnergyGPT (LLaMA 3.1-8B, full-param SFT on 4x A100) | Converging evidence: 8B-class models, LoRA SFT, domain corpus >10K records is the proven recipe |
| **SME-in-the-loop evaluation** is mandatory, not optional | Chevron ("AI scientists constantly fine-tuning to prevent creative deviations"), EXL (3 blinded SMEs, 1-5 scale), EnergyLLM (SME head-to-head vs base model), EnergyGPT (Claude Sonnet as LLM-judge calibrated against human experts) | InsurBench MUST include SME evaluation protocol, not just automated metrics. Build this into platform. |
| **Synthetic data generation** is a validated scaling approach | EnergyLLM uses Mistral-Nemo to generate QA pairs from OnePetro corpus at scale | Superpose should use LLM-generated QA pairs from SERFF filings + SEC EDGAR to scale insurance training data beyond the ~13K EXL threshold |
| **Cross-functional governance** (legal + cybersecurity + domain) is a prerequisite | Chevron Enterprise AI team includes legal, HR, cybersecurity reps. All AI gets risk assessment. Collaborates with Responsible AI Institute on "AI Inventories." | Superpose platform should have built-in audit trails, AI inventory exports, and compliance dashboards — not afterthoughts |
| **Vendor-built beats internal 2x** (MIT NANDA, Aug 2025) | MIT study: 95% enterprise GenAI pilots fail. Purchasing from specialized vendors succeeds 67% vs ~22% for internal builds. "Core barrier is learning, not infrastructure." | Strong validation of Superpose's platform approach. Carriers who try to build internally will mostly fail. Position Superpose as the vendor that prevents the 95% failure rate. |

**New technical data points from EnergyGPT paper (arxiv 2509.07177):**
- Full-param SFT on LLaMA 3.1-8B, 4x A100-80GB, ~6 days training, 2.14B tokens
- Data pipeline: DeBERTa quality classifier → hash dedup → MinHash fuzzy dedup → semantic filtering (cosine >0.8 against domain queries)
- Only 88% MC accuracy vs 86% base model = **2% improvement** on domain QA. Validates that fine-tuning improvement is MARGINAL for factual QA — the value is in instruction-following and domain-appropriate outputs, not raw accuracy.
- Deployment: NVIDIA NIM (on-prem) + Azure ML endpoint (cloud), both with API key management + per-project quotas

**ADNOC ENERGYai scale validation:** $340M 3-year contract (Mar 2025) with AIQ/G42/Microsoft. Uses agentic AI + OpenAI models + OSDU framework on Azure. 10x seismic speed, 70% precision improvement on 15% of data. SLB joined as implementation partner (Aug 2025). **This is a $113M/yr AI deal — proves enterprise AI budgets exist at scale in regulated industries.**

**Detail:** `raw/2026-02-12-chevron-finetuning-gemini.md`, `raw/2026-02-12-chevron-finetuning-claude.md`, `raw/2026-02-12-chevron-finetuning-v2-gemini.md`, `raw/2026-02-12-chevron-finetuning-v2-claude.md`, `raw/2026-02-12-chevron-finetuning-lessons-gemini.md`, `raw/2026-02-12-chevron-finetuning-v3-gemini.md`, `raw/2026-02-12-chevron-finetuning-v3-claude.md`

### §1b. Gate-Based Quantum Computing Expansion — EXHAUSTIVELY ASSESSED, NOT VIABLE AT PRE-SEED (Feb 12)
<!-- Last updated: 2026-02-12 — After COMPREHENSIVE exploration: dual-engine Chevron/energy (70+ searches) + ALL gate-based QC applications (34 searches, 10 page reads) covering QML, QAOA, quantum finance, PQC, drug discovery, sensing, QEC, middleware, compilers, QRNG, defense, quantum-inspired classical. Total: 120+ searches across all gate-based QC research. -->

**Question:** Can Superpose pivot from quantum annealing to gate-based quantum computing (IBM, Google, IonQ, Quantinuum) and build a unicorn via ANY application area — molecular simulation, QML, QAOA optimization, quantum finance, drug discovery, PQC/cybersecurity, sensing, QEC-as-a-service, middleware, compilers, QRNG, defense, or quantum-inspired classical algorithms?

**Answer: NOT VIABLE AT CURRENT STAGE. DEFINITIVELY CONFIRMED ACROSS ALL 12+ APPLICATION AREAS.** Every gate-based QC pathway falls into one of three failure modes: (1) no revenue exists yet (QML, QAOA, quantum finance, QEC), (2) revenue exists but requires massive capital (hardware, sensing, drug discovery — Q-CTRL needed $50M+, Quantinuum $800M+), or (3) revenue exists on classical hardware and is well-funded (Multiverse Computing $100M ARR with $250M+, SandboxAQ $950M, PQShield $65M). The only commercially successful "quantum" model is quantum-INSPIRED methods on classical hardware (Multiverse CompactifAI, SandboxAQ LQMs). These generate real revenue but don't use quantum computers. Key new finding: **Multiverse Computing reached $100M ARR (Jan 2026) with tensor network LLM compression on classical hardware — 100+ customers (Allianz, Moody's, Bosch), seeking EUR 500M at EUR 1.5B valuation.** This is the one model that works but requires $250M+ and 7-year head start to replicate. Full analysis: `raw/2026-02-12-gate-qc-unicorn-pathways-claude.md`.

**Quantum Computing Industry Landscape (Feb 2026):**

| Company | Valuation | Revenue | Employees | Focus | Funding |
|---------|-----------|---------|-----------|-------|---------|
| Quantinuum | $10B | $115M (2025) | 561 | Trapped-ion hardware + InQuanto chemistry | $800M round (Nov 2025) |
| SandboxAQ | $5.75B | Undisclosed | ~500 | LQMs (physics AI + quantum), AQCat catalysis | $950M total (Alphabet spinout) |
| PsiQuantum | $7B | Undisclosed | ~400 | Photonic quantum computing | $2.3B total |
| IonQ | $24.5B (mkt cap) | $43M (2024), $82-100M (2025 est.) | ~450 | Trapped-ion, cloud QC | Public (NYSE: IONQ) |
| IQM | $1B+ | Undisclosed | ~300 | Superconducting, Europe | $320M (Series B, Sep 2025) |
| Classiq | ~$500M+ | Undisclosed | ~100 | Quantum software platform | $200M+ total |
| D-Wave | $1.5B (mkt cap) | $22M (9mo 2025) | ~200 | Annealing + gate-model (acquired Quantum Circuits Jan 2026) | Public (NYSE: QBTS) |

**Total quantum industry revenue: $1.45B globally (2024).** VC funding: $1.9B in 62 rounds (2024), $3.77B in Q1-Q3 2025.

**Gate-Based QC for Energy — What's Real vs. Speculative:**

| Application | Status | Timeline | Evidence |
|-------------|--------|----------|----------|
| **Molecular simulation (small molecules)** | PROVEN — H2O, BeH2, LiH at chemical precision with QEC | Now | Quantinuum Helios (98 qubits, 99.92% 2-qubit fidelity) |
| **Catalyst design (fuel cells)** | DEMONSTRATED — platinum oxygen reduction (BMW/Airbus/Quantinuum) | Pilot | Single collaboration, not production |
| **Carbon capture (MOF simulation)** | RESEARCH — TotalEnergies/InQuanto for MOFs, CERN Open Quantum Institute | Academic | No commercial deployment |
| **Reservoir simulation** | RESEARCH — QLSTMA model (19-20% improvement in permeability prediction) | Academic | Lab results only, not production |
| **Refinery scheduling/optimization** | RESEARCH — QAOA for scheduling, 15% efficiency claims | Theoretical | No named customer in production |
| **Seismic interpretation (QML)** | RESEARCH — QLSTM for fault detection, quantum kernels for classification | Academic | Not production-ready |
| **Industrial chemistry (chemical accuracy)** | NOT POSSIBLE YET — requires millions of qubits | 2033-2040 | BCG/experts consensus |

**Energy Companies' Quantum Activities:**

| Company | Quantum Partner | Activity | Status |
|---------|----------------|----------|--------|
| Chevron | OQC (CTV invested in $100M round, Mar 2024) | Catalyst optimization, materials discovery | INVESTOR only |
| Aramco | SandboxAQ (AI agreement, Jan 2025), Pasqal (200-qubit install, H2 2025) | CFD solver, battery optimization | Agreement signed, no results |
| Shell | IBM Q Network | Reservoir simulation, molecular modeling | Research only |
| BP | IBM Q Network, ORCA Computing | Molecular energy estimation (hybrid) | Research only |
| ExxonMobil | IBM Q Network | LNG maritime routing | Research only |
| TotalEnergies | Quantinuum InQuanto | MOF carbon capture modeling | Most advanced — still research |
| BASF | D-Wave | Manufacturing optimization | PoC |
| E.ON | IBM | Energy contract pricing | Experimental |

**Result: 0 out of 8 energy companies are PAYING for quantum molecular simulation as a service. All are research/investment activities.**

**Quantum Chemistry Startups (Closer Analogs):**

| Company | Funding | Key People | Product | Customers |
|---------|---------|------------|---------|-----------|
| QSimulate | $11M | Toru Shiozaki, Garnet Chan (Caltech) | Quelo + QIDO (with Mitsui/Quantinuum) | Google, JT Pharma, 5 of top 20 pharma, JSR, Panasonic |
| Phasecraft | $34M | Ashley/Toby Sherring (UCL/Bristol) | Quantum algorithms for chemistry/materials | Google, IBM, Quantinuum partnerships |
| Algorithmiq | $38.8M | Sabrina Maniscalco | Aurora platform for drug discovery | IBM + Microsoft partnerships |
| HQS Quantum Simulations | ~$15M | Michael Marthaler | NMR simulation, materials science | Karlsruhe, Germany |

**Zapata AI Cautionary Tale:** Harvard spinout, $67M raised, founded 2017. Pivoted from quantum to AI. SPAC listed Apr 2024 → stock dropped 60% on debut → $4.8M debt crisis → ceased operations Oct 2024. Lesson: quantum ML startups need massive runway and cannot depend on market timing. Had Zapata survived 2 more months, the quantum stock rally would have saved them.

**Why Gate-Based QC is NOT a Unicorn Path for Superpose NOW:**

| Factor | Reality |
|--------|---------|
| **Market exists?** | NO — quantum chemistry simulation is pre-revenue globally |
| **Competition** | $10B Quantinuum, $5.75B SandboxAQ, IBM/Google giving away tools |
| **Team fit** | ZERO — requires PhD quantum chemists, VQE/QPE specialists, computational chemistry |
| **Funding needed** | $50M+ to survive 3-5 year R&D period |
| **First customer** | UNKNOWN — no enterprise pays for quantum chemistry as a service |
| **Chevron as buyer?** | NO — INVESTOR via CTV, not buyer. Same pattern as FTaaS rejection |
| **Timeline to revenue** | 3-5+ years (BCG: broad advantage 2030-2040) |
| **Runway** | 15-18 months vs 3-5 year requirement |

**The SandboxAQ model is instructive but not replicable.** SandboxAQ ($5.75B) uses "Large Quantitative Models" — physics-based AI trained on quantum chemistry data, delivered on classical hardware. They don't need quantum computers today. But they spun out of Alphabet with $500M, have Eric Schmidt as chairman, and 500+ employees. Their AQCat25 catalysis model (11M data points, 500K GPU-hours on H100s) is available on HuggingFace — demonstrating the value is in the physics/ML, not the quantum hardware.

**Comparison: Gate-Based QC vs. Insurance AI (Plan B5):**

| Dimension | Gate-Based QC for Energy | Insurance AI (Plan B5) |
|-----------|-------------------------|----------------------|
| Revenue timeline | 3-5+ years | 3-6 months |
| Competition | $10B Quantinuum, $5.75B SandboxAQ | No "Harvey AI for Insurance" exists |
| Team fit | Zero quantum chemistry expertise | ML/NLP applies directly |
| Required funding | $50M+ for R&D survival | $3M runway sufficient for MVP |
| First customer | Unknown (no one pays for this yet) | MGAs identified (Accelerant, Coalition, Skyward) |
| P($100M revenue) | <1% | 12-18% |

**What WOULD need to be true (future, post-Series A with $15M+):**
1. Hire quantum chemistry PhD (from Quantinuum, Phasecraft, or national lab)
2. Focus on one vertical: quantum simulation for carbon capture materials
3. Use SandboxAQ model: physics-based AI + quantum as accelerator
4. Target 2028-2030 window when quantum chemistry becomes commercially useful
5. Raise $30-50M specifically for quantum R&D
6. Partner with hardware vendors (Quantinuum, IBM) rather than build hardware
7. First customer: materials company (BASF, Johnson Matthey, Covestro), NOT energy company
8. This is a viable Series B/C strategy, not a pre-seed strategy

**Market sizing for future reference:**
- QCaaS market: $4.35B (2025) → $74.36B (2033), 42.6% CAGR
- Quantum in energy/utility: $15.4B (2024) → $23.7B (2034), 4.3% CAGR
- Quantum chemistry simulation: $100-500M/yr during NISQ era (BCG est.)
- BCG quantum value creation: $450-850B by 2040 ($90-170B for providers)
- $2.6T impact across O&G by 2035 (Global Quantum Intelligence, speculative)

**Detail:** `raw/2026-02-12-gate-qc-chevron-energy-gemini.md`, `raw/2026-02-12-gate-qc-chevron-energy-claude.md`

### §1c. Dead Ideas Revisited — What to Salvage (Feb 12)
<!-- Last updated: 2026-02-12 — After comprehensive revisit of all killed/downgraded directions with engineering mindset. 30+ searches Claude sub-agent + 15+ direct searches. -->

**Question:** We aggressively killed ideas that didn't show quantum advantage. Was this too pessimistic? What if we asked "What can I engineer to make this happen?"

**Answer: The KILLS were correct — but the FRAMING was wrong.** The problem wasn't that individual directions were too small. It's that QUBO/quantum doesn't provide advantage at ML pipeline scales. Combining 5 things that don't work doesn't create something that works. BUT: every killed direction contains IP/knowledge that becomes a FEATURE of the insurance AI platform.

**The EvenUp Blueprint (proven vertical AI unicorn model):**
- **EvenUp** (personal injury legal AI): $2B valuation in 5 years. Started with ONE task (demand letters). Built proprietary data pipeline (1M pages/week of medical docs). Expanded to case management, settlement analysis, discovery. The data curation pipeline IS the moat, not the model.
- **Harvey AI:** $0 → $100M ARR in 3 years. Now $11B valuation (Feb 2026). Wedge: legal research for BigLaw. First customer: Allen & Overy (3,500 attorneys). Strategy: target unprofitable/loss-making workflows, co-build with customers, multi-model approach. 1,000+ customers by end 2025.
- **Mapping to Superpose:** InsurBench (benchmark) → fine-tuning (one task) → data curation → Guidewire integration → full insurance AI platform. Platform emerges from the vertical, not the other way around.

**Speed benchmarks for context (how fast AI companies grow):**

| Company | Speed | Team Size | Revenue | Valuation |
|---------|-------|-----------|---------|-----------|
| Cursor | $0 → $1B ARR in 24 months | 12 people | $1B ARR | $29.3B |
| Lovable | $0 → $100M ARR in 8 months | 45 people | $100M ARR | $2.5B+ |
| Cognition (Devin) | $1M → $73M ARR in 9 months | ~200 | $73M ARR | $10.2B |
| Harvey AI | $0 → $100M ARR in 36 months | ~623 | $195M ARR | $11B |
| Snorkel AI | N/A | 776 | $148M rev | $1.3B |
| EvenUp | 5 years to unicorn | ~500 | Undisclosed | $2B |

**What each dead direction becomes in the insurance platform:**

| Dead Direction | Score | What Died | What to Salvage | Feature in Insurance Platform |
|---------------|-------|-----------|-----------------|------------------------------|
| A: SFT Data Curation | 4/10 | QUBO for data selection at SFT scale | Data quality scoring, diversity metrics, subset selection algorithms | InsurBench benchmark; data readiness audits for carriers; training data quality layer |
| B: Model Compression | 2/10 | D-Wave for NN pruning | Knowledge of efficient model deployment, quantization | Compressed insurance models for edge/mobile (adjuster tablets, offline claims) |
| D: Multi-Task Mixture | 3/10 | Wrong formalism (continuous) | Understanding of multi-task optimization | Multi-task insurance model training (claims + underwriting + compliance in one model) |
| F: DPO/RLHF Selection | 6/10 | Marginal QUBO improvement | Alignment optimization knowledge | Align insurance models with carrier-specific policies and tone |
| G: GPU Scheduling | 3/10 | Wrong scale/latency for QUBO | Inference optimization knowledge | Efficient multi-model serving for insurance deployments |
| H: Mislabeled Data | 4/10 | Cleanlab already exists | Quality detection algorithms | Insurance training data quality layer (flag mislabeled claims/policies) |
| I: Model Merging | 4/10 | Right math, wrong scale | Merge recipe optimization | Merge specialist insurance models (claims + underwriting + compliance) |
| J: FL Client Selection | 3/10 | FL market tiny | Federated learning architecture | Privacy-preserving cross-carrier model improvement (with consent) |
| K: Synthetic Data | 3/10 | Same as A | Synthetic data generation | Generate synthetic insurance training data from SERFF/EDGAR (EnergyLLM validated this approach) |

**None of these are standalone products. ALL become features of the insurance AI platform.**

**Alternative directions evaluated and rejected:**

| Direction | Score | Why Rejected |
|-----------|-------|-------------|
| Quantum-Inspired Optimization (Multiverse-Lite) | 4/10 | Requires $250M+ and world-class tensor network researcher. Interesting as R&D project, not product. |
| ML Lifecycle Platform for Regulated Industries | 5/10 | Too broad for pre-seed. This is the Series A/B expansion, not the starting point. |
| Picks-and-Shovels for Quantum Ecosystem | 2/10 | Q-CTRL proves it works ($50M+) but requires deep physics expertise. Wrong team. |
| Optimization-as-a-Service | 3/10 | Math optimization market only $1.85B. Gurobi/FICO/IBM own 93%. Strangeworks trying, no revenue. |
| Defense Quantum Software | 1/10 | SandboxAQ ($950M) has fully captured this. |

**One new strategic idea: "Quantum-informed" as investor narrative.**
Multiverse's lesson: "quantum" is a MARKETING advantage, not necessarily a product advantage. They sell inference cost reduction; quantum math enables it. Superpose could position as using "quantum-informed optimization" for insurance data curation — submodular optimization with quantum-inspired improvements. This gives investors a quantum story without hardware dependency. BUT: only if the benchmark experiment shows ANY optimization advantage over random/greedy. If QUBO ties GRAPE, the optimization narrative dies regardless of framing.

**Key market data from revisit:**

| Market | Size | Growth |
|--------|------|--------|
| Enterprise LLM market | $5.91B (2026) | $48.25B by 2034, 30% CAGR |
| MLOps market | $3.4B (2026) | $25.4B by 2034, 29% CAGR |
| AI governance market | $227M (2024) | $4.83B by 2034, 36% CAGR |
| Privacy-preserving AI | Growing | $60.4B by 2034, 30% CAGR |
| Math optimization software | $1.85B (2024) | $4.72B by 2033, 11% CAGR |
| Vertical AI (BVP portfolio) | ~400% YoY growth | ~56-65% gross margins |

**Zapata AI cautionary tale (updated):** The lesson isn't "don't do quantum." The lesson is: (1) Never go public via SPAC with no revenue. (2) Build classical revenue first, keep quantum as R&D. (3) Never depend on quantum hardware timelines for revenue. (4) The Multiverse model (quantum math, classical hardware) is the only proven commercial model. Zapata would have survived 2 more months if they'd avoided the Sandia forward purchase agreement — the quantum stock surge in Dec 2024 would have saved them.

**Detail:** `raw/2026-02-12-revisit-dead-ideas-unicorn-claude.md`

---

*Detailed analysis for everything below is in `research/GTM-STRATEGY-DETAILS.md`:*
*§2–§10 (Direction A deep dive), §11 (regulatory tailwinds), Direction B details, QA evidence base, §15 (Plan B full evaluation), §16 (insurance AI landscape deep dive — 60+ searches, competitive map, funding, regulatory)*
*§17 (NEW — MVP technical feasibility, benchmarks, training data, defensibility architecture) is in THIS file above.*

---

## Insurance AI Competitive Map (NEW — Feb 12)
<!-- Last updated: 2026-02-12 — After Roots Automation deep dive + landscape expansion (60+ searches across 3 engines) -->

**Primary competitor (direct threat):**

| Company | Funding | Revenue | Focus | Deployment | Superpose Angle |
|---------|---------|---------|-------|------------|----------------|
| **Roots** | $43.9M (Series B) | $9.5M (100% YoY) | Document AI agents (InsurGPT = Mistral 7B + GutenOCR) | Cloud SaaS only | They sell agents, we sell the platform to build your own |

**Secondary competitors (adjacent):**

| Company | Funding | Revenue | Focus | Threat Level |
|---------|---------|---------|-------|-------------|
| FurtherAI | $35.6M (a16z Series A) | Unknown | Workflow automation for MGAs/carriers | HIGH — competing for same MGA beachhead |
| Gradient AI | $125.7M (Series C) | $12.8M | Traditional ML underwriting + claims | MEDIUM — different approach (predictive ML, not GenAI) |
| Sixfold AI | $45M+ (Series B) | Unknown | AI underwriting agent | MEDIUM — Guidewire-backed, underwriting only |
| EXL Insurance LLM | Public co ($1.8B+ rev) | N/A | Fine-tuned LLM on NVIDIA/AWS | MEDIUM — services company, not product |
| Pibit.AI | $7.5M (Series A, YC) | Unknown | Vertical AI for underwriting | LOW — early stage, narrow focus |
| Panta | YC W2026, 4 ppl | Pre-rev | AI brokerage (autonomous agents) | LOW — brokerage, not carrier tools |
| Amera | YC F2025 | Early | Health claims automation | LOW — health only |

**Key insight:** Every competitor is building **workflow automation powered by AI**. Nobody is building a **fine-tuning platform for insurance carriers to own their own models**. This remains the open niche. But the window is narrowing — FurtherAI (a16z) and Roots (100% YoY growth) are accelerating.

**Roots SWOT Summary:**
- **Strengths:** Insurance-native leadership (CEO 14yrs AIG), 250M+ doc data moat, 35 enterprise customers, SOC2/ISO27001/HIPAA, Liberty Mutual as strategic investor
- **Weaknesses:** Cloud-only (no on-prem), no published benchmarks, single base model (Mistral 7B), throughput degradation at 8K+ tokens, $9.5M on $43.9M raised (~5x capital efficiency), **open-sourced their OCR moat (GutenOCR, Apache 2.0)**
- **Superpose opportunities:** Privacy-first on-prem, publish rigorous benchmarks (create InsurBench — first English insurance NLP benchmark), Guidewire marketplace (no fine-tuning partner exists), multi-model flexibility, compliance-first positioning, **use Roots' own GutenOCR as OCR layer**
- **Threats:** Roots' 250M doc moat, FurtherAI ($35.6M) targeting same MGA beachhead, Anthropic direct deals (Travelers, Allianz), SOC 2 is 6-month blocker

---

## Insurance GTM 90-Day Playbook (UPDATED — Feb 12)
<!-- Last updated: 2026-02-12 — Updated with concrete MVP technical spec -->

**Days 1-30: Foundation**
1. Hire insurance domain advisor ($2-5K/mo + 0.5% equity). Sources: InsurTech Talent Partners, Cowen Partners, ITC network, recently retired VP from mid-market carrier
2. Start SOC 2 Type 2 prep immediately (Vanta/Drata, ~$10-20K/yr). 3-6 month process — every day of delay = day pushed on first enterprise deal
3. Build MVP (see §17 for detailed technical spec):
   - **Base model:** Llama 3.1-8B-Instruct (same as EXL's proven approach)
   - **OCR layer:** GutenOCR (Roots' open-source Qwen2.5-VL fine-tune — Apache 2.0, HuggingFace)
   - **Fine-tuning:** LoRA SFT, rank 32, dim 16, Q/K/V layers (EXL's exact config)
   - **Training data:** Scrape SERFF rate filings (richest public insurance text) + SEC EDGAR insurance 10-Ks + FEMA NFIP claims (2.7M records) + Snorkel underwriting traces (380 real multi-turn examples) + synthetic augmentation
   - **Compute:** 2x H100 (cloud: ~$2-5K per training run on AWS/Lambda)
   - **Target:** 30%+ accuracy improvement over generic LLMs on insurance tasks (EXL's benchmark)
4. Create & publish "InsurBench" — first English insurance NLP benchmark. **No English equivalent exists today** (InsQABench is Chinese-only). Cover: document extraction, policy comparison, claims summarization, underwriting triage, regulatory compliance. Use ROUGE/BLEU/BERTScore + SME evaluation. This exploits Roots' biggest vulnerability (zero published benchmarks) AND establishes Superpose as the standard-setter.

**Days 31-60: Outreach**
5. Target 7 tech-forward MGAs with "AI Readiness Audit" ($25-50K): Accelerant, Skyward Specialty, Coalition, HDVI, Kinsale Capital, Method Insurance, Starwind Specialty
6. Apply for Guidewire Marketplace partner program (450+ apps, 220+ partners, no fine-tuning partner)
7. Build ACORD-aware connectors (XML/AL3/JSON) — this is the defensibility play

**Days 61-90: Validate**
8. Close 2-3 pilot deals ($25-50K each)
9. Attend ITC Vegas (Sep 29 - Oct 1) — book meetings in advance via the app
10. Iterate MVP based on pilot feedback. Document case studies

**First customer targets (MGAs — beachhead):**
| Target | Why | Size |
|--------|-----|------|
| Accelerant | Risk exchange, already FurtherAI customer (validate) | $1.5B+ premiums |
| Coalition | Cyber MGA, tech-native, $3.5B valuation | Large MGA |
| Skyward Specialty | Already using Gradient AI + Sixfold (receptive to AI) | $3.7B market cap |
| Kinsale Capital | E&S specialist, tech-forward, growing fast | $4.7B market cap |
| HDVI/Method Insurance | Already Pibit.AI customers (validate) | Mid-market |

---

## 12. Honest Assessment

### What's Our Real Chance?

**12–18% probability of becoming $100M+ company as vertical insurance AI.** (Unchanged from prior assessment, but CONVICTION increased after dead ideas revisit.)

**What increased conviction (Feb 12 revisit):**
- Every unicorn pattern (Harvey, EvenUp, BVP framework, Scale VP) points to vertical AI as fastest path
- 36 out of 46 zero-to-unicorn companies in 2025 were AI companies
- Predibase acquired by Rubrik (~$100M) — gap in privacy-first fine-tuning confirmed
- OpenPipe acquired by CoreWeave — fine-tuning platform space consolidating into infra companies
- Snorkel AI at $148M revenue proves data-centric AI for regulated industries is a real market
- Insurance integration complexity (Scale VP) is a barrier to entry AND a moat once overcome
- BVP expects 5+ vertical AI companies at $100M+ ARR within 2-3 years (2026 vintage)

**Why not higher:**
- Insurance sales cycles (12-18mo) vs pre-seed runway (15-18mo on $3M)
- Roots ($43.9M, 100% YoY), FurtherAI ($35.6M, a16z) have head start in insurance AI
- No insurance domain expertise on team (highest practical risk)
- SOC 2 Type 2 is a 3-6 month prerequisite blocker
- "Privacy-first fine-tuning" is a feature any competitor can add

**Why not lower:**
- No "Harvey AI for Insurance" exists — niche remains open
- EvenUp model maps directly: narrow wedge → data pipeline → expand
- 95% of enterprise GenAI pilots fail (MIT) — vendor-built succeeds 67% vs 22% internal
- Killed quantum/ML directions become platform features, not wasted R&D
- AI companies reaching $100M ARR in 8-36 months is the new normal (Cursor, Lovable, Harvey)

### What Would Kill Us

| Death Scenario | Probability | Description |
|---|---|---|
| **"Good Enough" Ceiling** | 40% | DatologyAI's heuristics capture 95% of value. QUBO adds 1% at 10x complexity. |
| **Pilot Purgatory** | 30% | Security reviews take 18 months. Burn $3M with zero revenue. Can't raise Series A. |
| **Scaling Dilution** | 20% | Pre-filtering to QUBO-solvable size does 90% of work. QUBO = "glorified greedy with quantum branding." Technical DD kills fundraise. |

### Plan B: If QUBO Doesn't Beat Classical

Drop quantum, keep everything else:
1. Replace QUBO with submodular maximization (LESS, facility location)
2. Keep privacy-first, deploy-in-your-cloud positioning
3. Keep data curation story ("we select the best training data")
4. Rebrand "quantum-optimized" → "mathematically-optimized"
5. Compete in the Predibase gap directly

**The company survives without quantum. It just has a less exciting investor narrative. But a boring company with revenue beats an exciting company with a whitepaper.**

### Investor Narrative

> "The $8B+ privacy-first fine-tuning market is growing 25–30% annually, driven by regulatory mandates. Superpose is the only company offering turnkey, on-premise LLM fine-tuning with quantum-inspired data optimization — giving regulated enterprises the AI capabilities they need without the data exposure they can't afford."

---

## 13. This Week's Priorities

| Priority | What | When | Success Criteria |
|----------|------|------|-----------------|
| **1. RUN THE BENCHMARK** | QUBO vs. random vs. greedy submodular vs. LESS on real downstream task (7–8B model) | Mon–Thu | If QUBO wins by 3%+: write it up. If ties/loses: pivot to Plan B immediately. |
| **2. BUILD THE AUDIT PRODUCT** | Repeatable "Data Readiness Audit" package. Input: S3 bucket. Output: beautiful PDF with quality scores, coverage gaps, contamination warnings. | Mon–Fri | Can generate revenue THIS MONTH |
| **3. FIRST OUTREACH** | Email 5 targets (Progressive, USAA, EXL, Intermountain, Coalition). Lead with Data Readiness Audit. | Thu–Fri | 2 calls booked by end of next week |
| **4. PREDIBASE GAP** | One-page "Why Predibase customers need a new home" doc → LinkedIn/HN | Fri | Time-sensitive opportunity |

---

## 14. Open Questions / What We Still Need to Find Out
<!-- Last updated: 2026-02-12 — Updated after Chevron/O&G vertical exploration (50+ searches, 3 engines) -->

1. **Does QUBO actually beat strong classical baselines on real SFT data?** EXISTENTIAL. Must benchmark against `submodlib` and LESS on real dataset (MIMIC-IV or public insurance). If QUBO doesn't win, pivot immediately.

2. ~~**Scale constraints.**~~ Moot if Plan B (classical) executes.

3. **What format do insurance customers actually give us?** ✅ PARTIALLY ANSWERED. ACORD XML/AL3/JSON, Guidewire/Duck Creek proprietary formats, massive unstructured data. Manual re-keying >40% of underwriter time. Building ACORD-aware connectors is the defensibility play.

4. **Will customers pay for data curation alone?** ✅ PARTIALLY ANSWERED. Benchmark: "$250K–$1M for LLM implementation." Stand-alone curation unproven — bundle with fine-tuning. Data Readiness Audit ($25–50K) is door opener.

5. **H2O.ai trajectory.** Progressive is their customer. Launched Enterprise LLM Studio (March 2025, FTaaS on Dell infrastructure, behind-firewall). Direct competitor for FTaaS. Claims "over half the Fortune 500." Monitor — especially for energy vertical expansion.

6. ~~**SIGIR 2024 paper.**~~ Already integrated.

7. **Anthropic direct deals eroding privacy story.** Travelers: 10K Claude assistants. Allianz: global partnership. **Counter:** EXL proved fine-tuning beats generic by 30%. UBIAI: 94.1% vs 67%. InsurancGPT whitepaper (Enkefalos) adds third data point: fine-tuned Mistral beats GPT-4 on insurance QA (ROUGE-L 0.476, BERTScore 0.727).

8. **Pricing validation.** ⚠️ UPDATED: After 97+ total searches (60 prior + 37 new), still zero public vendor pricing for carrier-grade insurance AI. Only hard data points: Harvey ~$1K-$1.2K/user/mo (legal AI), Patra $99/mo (agency self-serve), Verint $13M multi-year (single top-5 insurer), enterprise range $25K-$200K+/yr (synthesized). **Customer discovery calls are the ONLY remaining path to pricing validation. This cannot be solved with desk research.**

9. **Harvey AI insurance expansion.** ✅ LARGELY RESOLVED. Harvey's "insurance modules" are legal document tools for insurers' legal teams — NOT insurance operations (underwriting, claims, actuarial). Expansion roadmap is horizontal: legal → tax → accounting → finance → consulting. NOT going deep into insurance operations. **Risk downgraded from existential to monitor-quarterly.** Detail: `raw/2026-02-11-insurance-competitive-pricing-claude.md`

10. **Guidewire Agent Studio.** ✅ LARGELY RESOLVED. Agent Studio is an agent orchestration layer, NOT a fine-tuning platform. "Build, train, deploy" means configure agents with prompts/workflows using LLMs of choice — NOT fine-tune foundation models. Zero fine-tuning documentation exists. Guidewire invested $30M in Sixfold (AI underwriting) rather than building in-house. **Risk downgraded from existential to opportunity.** Superpose could build fine-tuned insurance LLMs that plug INTO Guidewire Agent Studio via their marketplace (450+ apps, 220+ partners). Detail: `raw/2026-02-11-insurance-competitive-pricing-claude.md`

11. **InsurancGPT / Enkefalos Technologies.** ✅ RESOLVED. Bootstrapped India-based IT services firm, 44 employees, zero external funding, zero named customers, founded 2015. InsurancGPT = fine-tuned Mistral + RAG + DPO. Whitepaper benchmarks (100 questions) show fine-tuned Mistral beats GPT-4 on insurance tasks. Only public case study is a quote comparison platform, not carrier-grade. **Not a competitive threat. Useful as thesis validation only.** Detail: `raw/2026-02-11-insurance-competitive-pricing-claude.md`

12. **No insurance domain expertise on team.** Highest practical risk. **Hire or advisory-board immediately.** Sources for insurance advisors: InsurTech Talent Partners (specialist recruiter), Cowen Partners (national insurance exec search), Munich Re consulting (advisory board participants). Target: recently retired VP-level from mid-market carrier (Erie, Auto-Owners, Grange). Budget: $2-5K/mo + 0.5% equity.

13. **Roots Automation (InsurGPT) competitive teardown.** ✅ DEEP DIVE COMPLETE (Feb 12). Key findings: Roots is a **workflow automation company with a fine-tuned Mistral 7B**, NOT a fine-tuning platform. $43.9M total funding (5 rounds), $9.5M revenue (Oct 2024), 35 customers, 100% YoY growth, 100+ employees. Tech stack: fine-tuned Mistral 7B via vLLM on A100 GPUs ($30K/yr for 20-30M docs) + proprietary GutenOCR (fine-tuned Qwen2.5-VL 3B/7B). 250M+ proprietary insurance docs = massive data moat via federated learning. **Cloud-only SaaS** ("born in the cloud, delivered as a service") — no on-prem option. **Critical vulnerability: zero published quantitative benchmarks** — they claim "outperforms GPT-4" but provide no evidence. Superpose differentiation: (1) "fine-tuning platform you own" vs "digital coworker you rent," (2) on-prem/VPC deployment for data sovereignty, (3) multi-model flexibility. New competitor map: FurtherAI ($35.6M, a16z), Gradient AI ($125.7M), Sixfold ($45M+, Guidewire-backed), Pibit.AI ($7.5M, YC). Pricing opaque — implied ACV ~$271K. Detail: `raw/2026-02-12-roots-automation-insurance-gtm-claude.md`, `raw/2026-02-12-roots-automation-insurance-gtm-gemini.md`

14. **Actual carrier AI budgets remain unknown.** Macro data (3-8% IT to AI → 20% in 3-5 years) is available but micro data (what does a $5B GWP mid-market carrier actually spend on AI annually?) requires customer calls. Insurance AI budget allocation (2025): 66.7% traditional AI, 21.5% GenAI, 11.8% agentic AI.

15. **NEW: SOC 2 Type 2 is a prerequisite blocker.** Every insurance enterprise deal requires SOC 2 Type 2 at minimum. Timeline: 3-6 months. Roots, FurtherAI, Gradient AI, and Sixfold all have it. Must begin immediately with compliance automation (Vanta/Drata/Secureframe, ~$10-20K/yr).

16. **NEW: MGA beachhead validated but specific targets identified.** Tech-forward MGAs buying AI: Accelerant (FurtherAI customer, risk exchange), Skyward Specialty (Gradient AI + Sixfold customer), HDVI/Method Insurance (Pibit.AI customers), Coalition ($3.5B cyber MGA), Kinsale Capital ($4.7B market cap E&S). MGAs have faster buying cycles, less legacy tech, smaller security burden than carriers.

17. **NEW: Insurance conference calendar for 2026.** Must-attend: ITC Vegas (Sep 29 - Oct 1, 9K+ attendees). Also: ITC Europe (May 28-29, Barcelona), Insurtech Insights USA (Jun 3-4, NYC). ITC Vegas is the single most important insurance networking event.

18. **NEW: MVP training data pipeline validated (Feb 12).** ✅ PARTIALLY ANSWERED. SERFF rate filings (free PDF access, richest insurance text), SEC EDGAR insurance 10-Ks (6B+ tokens, EDGAR-CRAWLER open source), FEMA NFIP claims (2.7M records, free API). EXL proved 13,500 records enough to beat GPT-4. **Remaining:** Need to actually scrape and assess SERFF filing quality. ACORD schemas require membership. Compute cost estimated at $2-5K per training run (2x H100 cloud). **NEW validation (Feb 12, v3):** EnergyLLM uses Mistral-Nemo to synthetically generate QA pairs from OnePetro corpus — this same approach should be applied to SERFF filings and SEC EDGAR to scale Superpose's insurance training data. EnergyGPT's data pipeline (DeBERTa quality classifier → hash dedup → MinHash fuzzy dedup → semantic filtering) is directly replicable.

19. **NEW: No English insurance NLP benchmark exists (Feb 12).** InsQABench is Chinese-only. INS-MMBench is vision/multimodal. insurance-llm-framework has 11 GitHub stars. **Creating "InsurBench" is highest-leverage Day 1 action** — first mover defines the standard, attracts industry attention, provides credible benchmark blog content. Need insurance SME for validation.

20. **NEW: Technical defensibility beyond fine-tuning (Feb 12).** Bessemer warns "data extraction becomes table stakes." Harvey's moat = trust stack + ecosystem integration + compliance architecture (NOT the model). EXL's entire model took 13,500 records — trivially replicable. **Superpose must build defensibility in ACORD connectors, compliance guardrails, workflow embedding (Guidewire), and data flywheel — NOT in model fine-tuning alone.** **NEW (Feb 12, v3):** MIT NANDA study (Aug 2025): 95% of enterprise GenAI pilots fail to deliver ROI. Vendor-built solutions succeed 67% vs ~22% for internal builds. Key failure causes: misaligned workflows, weak contextual learning, unfocused rollouts. Successful 5% share: (1) tackle ONE specific pain point, (2) leverage external vendors, (3) focus on back-office functions (compliance, ops support). **This validates Superpose's positioning as specialized vendor solving one problem (insurance document AI) rather than generic platform.**

21. **Oil & gas as second vertical — REJECTED WITH MAXIMUM CONFIDENCE (Feb 12, v3 final).** ✅ FULLY RESOLVED. Detail: `raw/2026-02-12-chevron-finetuning-v3-gemini.md`, `raw/2026-02-12-chevron-finetuning-v3-claude.md`

22. **Gate-based quantum computing as unicorn pathway — EXHAUSTIVELY ASSESSED, NOT VIABLE AT PRE-SEED (Feb 12).**

23. **Dead ideas revisit — can killed directions be revived with engineering mindset? (Feb 12).** ✅ FULLY RESOLVED. Revisited ALL killed/downgraded directions (A, B, D, F, G, H, I, J, K, non-ML QUBO, gate-based QC) plus 5 alternative directions (quantum-inspired, ML lifecycle platform, picks-and-shovels, OaaS, defense quantum software). Also studied unicorn patterns (Harvey, EvenUp, Cursor, Lovable, Cognition, Snorkel AI) and frameworks (BVP 10 Principles, Scale VP AI Verticals). **Conclusion: kills were correct but framing was wrong. Killed directions become FEATURES of insurance AI platform. Alternative directions all rejected (wrong team, wrong market, or unreplicable). Insurance AI (Plan B5) REINFORCED. EvenUp model is the blueprint: narrow wedge → data pipeline → expand.** One new idea: "quantum-informed optimization" as investor narrative (not product). Detail: `raw/2026-02-12-revisit-dead-ideas-unicorn-claude.md` ✅ DEFINITIVELY RESOLVED. Three rounds of research: (1) Chevron/energy quantum simulation (Gemini 136KB + Claude 35+ searches), (2) ALL gate-based QC applications comprehensive (Claude 34 searches, 10 page reads — QML, QAOA, quantum finance, PQC, drug discovery, sensing, QEC, middleware, compilers, QRNG, defense, quantum-inspired classical), (3) 20+ Engine 3 direct fact-checks. Total: 120+ searches across all gate-based QC. **Result: NO pathway viable at pre-seed.** Every application fails for one of three reasons: (a) no revenue exists yet (QML, QAOA, finance, QEC), (b) revenue requires massive capital ($50M+) and physics expertise (sensing, drug discovery, hardware), (c) revenue on classical hardware but well-funded competitors (Multiverse $100M ARR/$250M+ raised, SandboxAQ $950M, PQShield $65M). Key new finding: **Multiverse Computing = $100M ARR (Jan 2026) via quantum-INSPIRED tensor network compression on CLASSICAL hardware — the one model that works but unreplicable at $3M (160 patents, 7yr head start, $250M+ funding).** PQC market is real ($1.15B+, mandate-driven) but is classical cybersecurity, not quantum computing, and SandboxAQ/PQShield/QuSecure dominate. QML has ZERO demonstrated advantage over classical ML on real-world data (2025 benchmark consensus). Insurance AI (Plan B5) remains overwhelmingly the correct strategy. Detail: `raw/2026-02-12-gate-qc-chevron-energy-gemini.md`, `raw/2026-02-12-gate-qc-chevron-energy-claude.md`, `raw/2026-02-12-gate-qc-unicorn-pathways-claude.md`

---

## 15. Plan B Summary

**Recommended: B5 (Vertical Insurance AI) + B1 (Privacy-First FTaaS) combined.**

| Direction | Viability | Market | Defensibility | Team Fit | Time to Revenue |
|-----------|-----------|--------|---------------|----------|----------------|
| B1: Privacy-First FTaaS | 7/10 | $2-4B | 4/10 | 8/10 | 2-3 months |
| B2: Data Curation SaaS | 5/10 | $200-500M | 2/10 | 7/10 | 3-6 months |
| B3: LLM Eval Platform | 4/10 | $500M-1B | 2/10 | 3/10 | 4-6 months |
| B4: AI Data Flywheel | 6/10 | $1-3B | 3/10 | 5/10 | 6-9 months |
| B5: Vertical Insurance AI | 7/10 | $500M-1B | 7/10 | 5/10 | 3-6 months |

**Decision framework:**
- **QUBO beats GRAPE by >10%:** Keep quantum as backend advantage. Still use Plan B GTM.
- **QUBO ties or loses:** Execute Plan B immediately. Replace D-Wave with Gurobi/submodular. Drop quantum from all materials.
- **Either way:** Product, market, pricing, customers, and GTM are the same. Quantum vs classical is a backend detail.

**The company becomes:** "Privacy-first AI fine-tuning for regulated industries, starting with insurance."

**The EvenUp Blueprint (validated Feb 12):**
1. Start with ONE narrow wedge (InsurBench benchmark + fine-tuning for one task: claims summarization)
2. Build proprietary data pipeline (SERFF filings → GutenOCR → structured text → fine-tuning data)
3. Expand to adjacent features that share the same data (underwriting triage, policy comparison, compliance)
4. Integrate into workflows (Guidewire marketplace, ACORD connectors)
5. Data flywheel: each customer's usage (with consent) improves base model
6. The platform emerges organically from the vertical — don't design the platform first

**Speed target:** Harvey did $0 → $100M ARR in 36 months. Insurance is slower (integration complexity) but stickier. Realistic target: $1M ARR in 12-18 months, $10M ARR in 24-30 months.

*Full Plan B evaluation and insurance AI deep dive: `research/GTM-STRATEGY-DETAILS.md` §15–§16.*

---

---

## 17. MVP Technical Feasibility & Architecture (NEW — Feb 12)
<!-- Last updated: 2026-02-12 — After 20+ searches on insurance datasets, benchmarks, competitor architectures, and vertical AI defensibility -->

### EXL Insurance LLM Blueprint (Proven Reference Architecture)

EXL's published whitepaper provides the most detailed public evidence that fine-tuned small models beat frontier LLMs on insurance tasks:

| Parameter | EXL Insurance LLM |
|-----------|-------------------|
| **Base model** | Llama 3.1-8B-Instruct |
| **Fine-tuning** | LoRA SFT, rank 32, dim 16, Q/K/V layers |
| **Training data** | 13,500 records (9 yrs claims), structured + unstructured |
| **Data prep** | AWS Textract OCR → HIPAA de-identification (SHA256) |
| **Training hardware** | 2x NVIDIA H100 (80GB each) |
| **Inference** | 4x A10 GPUs (g5.24xlarge), NVIDIA NIM + TensorRT-LLM + Triton |
| **Evaluation** | BLEU, ROUGE, BERT, METEOR + 3 blinded SME reviewers (1-5 scale) |
| **Result** | Beats Claude 3.5 Sonnet, GPT-4, Gemini 1.5 Pro on all metrics |
| **Tasks** | Tag extraction (41 tags), medical record summarization, negotiation guidance, Q&A |

**Key insight:** Only 13,500 training records needed to beat frontier models. Domain-specific small data >>> generic large data.

### Roots' OCR Moat Is Gone: GutenOCR Is Open Source

Roots Automation open-sourced their OCR technology (Jan 2026):

| Component | Detail |
|-----------|--------|
| **Model** | GutenOCR-3B and GutenOCR-7B (fine-tuned Qwen2.5-VL) |
| **Training** | 31.8M real pages + 4.2M synthetic (OCR-IDL 26M, TabMe++ 122.5K, PubMed-OCR 1.5M) |
| **Performance** | Composite score 0.82 vs base Qwen2.5-VL 0.40 (2x improvement) |
| **Hardware** | 8x H100 GPUs for training |
| **License** | Apache 2.0 |
| **Available** | HuggingFace (rootsautomation/GutenOCR-3B, GutenOCR-7B), GitHub |

**Implication:** Superpose can use Roots' own OCR technology. Their remaining moats: 250M proprietary doc data, 35 enterprise customers, and insurance workflow knowledge. But OCR is no longer a differentiator for anyone.

### Insurance Benchmarks Landscape

| Benchmark | Coverage | Language | Type | Availability |
|-----------|----------|----------|------|-------------|
| **InsQABench** (Huazhong/Fudan) | Commonsense, Database, Clause QA | Chinese only | Text QA | GitHub |
| **INS-MMBench** (Fudan, ICCV 2025) | Auto, property, health, agricultural | English | Multimodal/Vision | GitHub |
| **insurance-llm-framework** (ozturkoktay) | Policy summarization, claims, risk assessment | English | Eval framework | GitHub (11 stars) |
| **Snorkel Multi-Turn Underwriting** | GL, Property, WC, Auto, Cyber, BOP | English | Agent traces | HuggingFace (380 rows) |
| **No English insurance text NLP benchmark exists** | — | — | — | **OPPORTUNITY** |

**INS-MMBench details:** 12,052 images, 10,372 questions, 22 fundamental + 12 meta + 5 scenario tasks. GPT-4o tops at 69.70%, Qwen-2.5-VL-32B at 64.10%, human baseline 60.45%. 57-64% of errors from lack of insurance domain knowledge. Accepted at ICCV 2025.

**Benchmark opportunity:** Create "InsurBench" — the first English insurance TEXT NLP benchmark. Tasks: (1) ACORD form field extraction, (2) policy comparison/diff, (3) claims narrative summarization, (4) underwriting triage decision, (5) regulatory compliance check, (6) loss run analysis, (7) coverage gap identification. Metrics: ROUGE/BLEU/BERTScore + SME evaluation. This is a high-leverage move: whoever defines the benchmark controls the conversation.

### Public Insurance Training Data Sources

| Source | Type | Size | Access | NLP Value |
|--------|------|------|--------|-----------|
| **SERFF Rate Filings** | Text (PDF) | 5,000+ filings per state per 3.5 yrs | Free public (portals.naic.org/serff-filing-access) | ⭐⭐⭐⭐⭐ — Richest insurance text: policy forms, actuarial memos, regulatory objections |
| **SEC EDGAR Insurance 10-Ks** | Text | 6B+ tokens in EDGAR-CORPUS | Free (sec.gov, EDGAR-CRAWLER open source) | ⭐⭐⭐⭐ — Risk Factors, Business Description, Management Discussion |
| **FEMA NFIP Claims** | Structured | 2.7M+ claims, 80+ fields | Free API (fema.gov) | ⭐⭐⭐ — Claims QA, damage assessment (structured, not text) |
| **State DOI rate filings** | Text (PDF) | Varies by state | Free public access varies | ⭐⭐⭐⭐ — Regulatory text, state-specific rules |
| **Snorkel Underwriting** | Agent traces | 380 rows, 6 tasks | HuggingFace (Apache 2.0) | ⭐⭐⭐ — Real underwriting multi-turn conversations |
| **Bitext Insurance Dataset** | Synthetic | 39 intents, ~39K examples | HuggingFace (free) | ⭐⭐ — Chatbot intent classification only |
| **CourtListener/PACER** | Legal text | Thousands of insurance dispute cases | Mixed (some free) | ⭐⭐⭐⭐ — Insurance legal reasoning, policy interpretation |
| **ACORD schemas** | XML/JSON | Standard forms 25/125/126/130/140 | Membership required | ⭐⭐⭐ — Template understanding, format validation |

**Data pipeline for MVP:** (1) Scrape SERFF filings from CA/NY/TX (free, PDF → OCR via GutenOCR → structured text). (2) Download SEC EDGAR insurance 10-Ks via EDGAR-CRAWLER. (3) Pull FEMA NFIP claims via API. (4) Augment with Snorkel underwriting traces + Bitext intents. (5) De-identify per HIPAA safe harbor. (6) Fine-tune with LoRA SFT.

### Technical Defensibility Stack (Lessons from Harvey AI + Bessemer)

Harvey AI's defensibility model (3 pillars): (1) Trust Stack — auditable, citation-grounded reasoning. (2) Ecosystem Integration — iManage + LexisNexis partnerships. (3) Compliance Architecture — audit trails, jurisdiction-aware configs.

Bessemer's 10 Principles for Vertical AI (key warnings):
- "Data extraction will become table stakes" — fine-tuning alone is NOT defensible
- "Models aren't a moat — multimodality can be"
- "Quality data > quantity" (EvenUp's approach)
- "Target nuanced needs" (compliance, security = multiple defensibility vectors)
- "Build for overlooked categories" (fine-tuning platform is overlooked)
- BVP vertical AI portfolio: ~56% gross margins at 1.6x burn ratio

**Superpose defensibility layers (in order of importance):**
1. **InsurBench benchmark** — define the standard, control the narrative, attract talent
2. **ACORD-aware connectors** — XML/AL3/JSON parsing mapped to ACORD Information Model. Nobody has this.
3. **Compliance guardrails** — NAIC AI Model Bulletin compliance engine, state-specific regulatory rules
4. **Privacy architecture** — VPC/on-prem/TEE deployment. NVIDIA Confidential Computing: <7% LLM inference overhead. Gartner: 60% of enterprises evaluating TEE by 2025.
5. **Guidewire/Duck Creek marketplace** — integration creates institutional switching costs
6. **Data flywheel** — each customer's fine-tuning (with consent) improves base model

**What won't work as defensibility:** Fine-tuning alone (EXL did it with 13,500 records). OCR alone (GutenOCR is open-source). Model selection alone (Bessemer: "models won't be a moat"). Raw data volume alone (Roots has 250M docs, we can't compete on volume).

### Existing Open-Source Insurance AI Tools

| Tool | What | Use for Superpose |
|------|------|------------------|
| GutenOCR (Roots) | Document OCR (Qwen2.5-VL fine-tune) | OCR layer — free, Apache 2.0 |
| Unstract | Open-source LLM-powered document ETL (AGPL) | Alternative/complement to GutenOCR |
| EDGAR-CRAWLER | SEC filing parser → structured JSON (WWW 2025) | Insurance 10-K text extraction |
| insurance-llm-framework | Streamlit eval framework for insurance LLMs | Evaluation harness skeleton |
| Open-Insurance-LLM-Llama3 | Llama 3 fine-tuned for insurance Q&A | Baseline comparison |
| SortSpoke | Insurance doc LLM (ACORD, loss runs, SOVs) | Competitive reference (not open-source) |
| ACORD Transcriber | NLP-powered ACORD doc → structured data | Competitive reference (ACORD product) |

---

## 18. Alternative Verticals Beyond Insurance (NEW — Feb 13)
<!-- Last updated: 2026-02-13 — After 33 sub-agent searches + 15+ direct searches across 9 verticals. Insurance deprioritized per founder preference. -->

**Question:** If not insurance, which regulated/specialized industry is the best fit for Superpose's privacy-first LLM fine-tuning platform?

**Answer: Accounting/Tax is the strongest alternative (8/10). Healthcare Prior Auth/Denial Management is #2 (7/10).**

### Vertical Ranking (all 9 evaluated)

| Rank | Vertical | Score | Key Rationale | Sales Cycle | Key Competitor |
|------|----------|-------|---------------|-------------|----------------|
| 1 | **Accounting/Tax** | **8/10** | Market forming NOW (Accrual launched Feb 2026). SMB-accessible (75K CPA firms). Harvey entering but focused on Big Four — mid-market wide open. Privacy matters (client financials). Seasonal urgency. | 1-3 months (SMB) | Accrual ($75M), Accordance ($13M) |
| 2 | **Healthcare: Prior Auth / Denial Mgmt** | **7/10** | $31B/yr on PA. HIPAA creates privacy moat. Provider sales cycles shortening (6.6mo). Clear ROI per recovered denial. | 4.7-6.6 months | Cohere Health ($200M, $5.5B val) |
| 3 | **Healthcare: Revenue Integrity / Coding** | **6/10** | SmarterDx model (5:1 ROI, contingency pricing). HIPAA moat. | 6.6 months | SmarterDx ($71M, 60+ health systems) |
| 4 | **Pharma Regulatory Submissions** | **5/10** | Weave Bio (97% time savings). High-value task. Small TAM (~$2-5B). | 10 months | Weave Bio ($36M) |
| 5 | **Legal: Niche Sub-Verticals** | **5/10** | Harvey proved $100M+ path. But $6B in legal tech in 2025 = overcrowded. | 3-6 months | Harvey ($11B), EvenUp ($2B) |
| 6 | **Financial Services: RegTech** | **4/10** | Large market ($60B by 2030). But bank sales cycles 6-12+ months. Incumbents strong. | 6-12+ months | Bretton AI ($75M), ComplyAdvantage |
| 7 | **Construction/Real Estate** | **3/10** | 79% have no AI (greenfield but long education cycle). Bad data infrastructure. | 3-6 months | Document Crunch ($30.5M) |
| 8 | **Government/Defense** | **2/10** | Perfect privacy fit but FedRAMP costs $250K+. Inaccessible at pre-seed. | 12-24 months | SandboxAQ, Palantir, Anduril |
| 9 | **Supply Chain/Logistics** | **2/10** | Document processing commoditized. No privacy moat. Not clearly an LLM fine-tuning use case. | 3-6 months | Reducto, many others |

### Top Pick: Accounting/Tax — Detailed Analysis

**Why the timing is perfect:**
- Accrual just publicly launched Feb 5, 2026 ($75M, General Catalyst). Market is forming RIGHT NOW.
- Accordance raised $13M seed (Khosla, General Catalyst, Anthropic, Sequoia, NEA) — heavyweight backing signals hot market.
- Filed raised $17.2M pre-seed (Northzone) — European tax automation.
- Harvey co-building custom tax model with PwC (Big Four partnership) — validates demand but targets enterprise only.
- KPMG launched Tax AI Accelerator Program (Feb 2026) — Big Four embracing AI.
- Fieldguide raised $75M Series C at $700M valuation (Goldman Sachs, Feb 2026) — audit/advisory AI is real.
- 60% of CFOs plan to increase finance AI investment 10%+ in 2026.

**Competitive landscape (who's doing what):**

| Company | Funding | Focus | Target Customer | Superpose Gap |
|---------|---------|-------|-----------------|---------------|
| Accrual | $75M (General Catalyst) | Tax return preparation (AI agents as preparers) | H&R Block, Armanino, top 100 firms | Cloud SaaS — no privacy-first option |
| Accordance | $13M (Khosla, Anthropic, Sequoia) | Tax/accounting AI brain (multi-agent on regulations) | Tax professionals | General purpose — not fine-tuning platform |
| Filed | $17.2M (Northzone) | Tax automation | European market | EU-focused |
| Harvey | $1.2B+ | Legal → Tax (PwC partnership) | Big Four, Am Law 100 | $1,200/user/month — inaccessible for SMB |
| Fieldguide | $75M ($700M val, Goldman) | AI audit/advisory platform | Top 100 CPA firms (50%) | Audit-focused, not tax prep |

**The open niche: privacy-first fine-tuning for mid-market CPA firms.**
- Harvey targets Big Four ($1,200/user/month). Accrual targets top 100 firms.
- 75,000+ CPA firms in the US, most <50 employees. Managing partner signs the check.
- These firms handle sensitive client data (SSNs, income, assets) and don't want it leaving their systems.
- An 8B model fine-tuned on tax code + IRS guidance + state regulations would outperform GPT-4 on tax extraction tasks (same pattern as EXL's insurance proof).

**Specific tasks for fine-tuned LLMs:**
1. Extract data from K-1s, 1099s, W-2s, multi-page statements → map to tax line items
2. Tax research assistant (fine-tuned on IRC + state codes + IRS guidance + Tax Court decisions)
3. Workpaper documentation automation
4. Engagement letter / client communication drafting
5. Multi-jurisdiction state tax compliance (50 different state codes)

**Public training data available:**
- Internal Revenue Code (IRC) — full text, freely available
- IRS Publications (500+) — complete guidance library
- State tax codes — 50 states, all public
- Tax Court decisions — available via PACER/Tax Court website
- IRS Private Letter Rulings (PLRs) — public after redaction
- AICPA standards — available with membership

**The EvenUp Playbook applied to Accounting:**
1. **Narrow wedge:** Tax return preparation from source documents (the task Accrual is tackling, but with privacy-first on-prem/VPC deployment)
2. **Data pipeline:** Build corpus from IRS publications, IRC, state codes, anonymized return data
3. **Expand:** Tax research → engagement management → audit support → advisory → bookkeeping
4. **Platform emerges:** Privacy-first fine-tuning platform for professional services, starting from accounting/tax

**a16z insight (Jan 2025 newsletter):** CAS (Client Advisory Services) is the fastest-growing segment in accounting at 30% median revenue growth YoY vs 9% industry-wide. The winning strategy is to lean into specific sub-verticals within accounting (construction accounting, healthcare accounting, etc.). Adaptive (a16z portfolio) exemplifies this by focusing exclusively on construction accounting.

### Runner-Up: Healthcare Prior Authorization / Denial Management

**Why it's strong:**
- $31B/year spent on prior authorization in the US
- 30-40% of denials are recoverable but unaddressed
- Each recovered denial = measurable revenue ($25 average rework cost per denied claim, hospitals losing $20B+ annually to denials)
- Provider-side sales cycles shortening: 6.6 months health systems (down from 8.0), 4.7 months outpatient (down from 6.0)
- HIPAA creates genuine privacy moat — on-prem/VPC deployment is a hard requirement
- Fine-tuned models demonstrably outperform generic LLMs on medical NLP (EXL pattern applies here too)
- Startups capture 85% of healthcare AI spending despite incumbent distribution (Menlo Ventures)

**Specific tasks:**
1. Parse denial letters and classify denial reasons (by CPT/ICD code, medical necessity, timely filing, etc.)
2. Match clinical documentation to payer-specific criteria (each payer has different rules)
3. Draft appeal letters grounded in medical policy and clinical evidence
4. Extract diagnosis/procedure codes from clinical notes

**Why it's riskier than accounting:**
- Cohere Health ($200M raised, $5.5B valuation, 12M PAs/year, auto-approves 90%) dominates payer-side
- Healthcare complexity is extreme — requires clinical domain expertise from Day 1
- Payer sales cycles are 11.3 months (UP from 9.4 — dangerous with 15-18mo runway)
- CMS mandating electronic PA by 2026-2027 may change market structure
- 67% of outpatient providers willing to switch AI vendors — low stickiness

**Key market data:**
- Total healthcare AI spending (2025): $1.4B (Menlo Ventures)
- Ambient clinical documentation: $600M (largest category, but saturating — 40% penetration plateau expected)
- Coding/billing automation: $450M
- Healthcare AI unicorns: 8 identified (Abridge $5.3B, Cohere Health $5.5B, Hippocratic AI $3.5B, Ambience)
- Private healthcare AI VC: $14B across 527 deals in 2025 (average deal $29.3M, up 42% YoY)

### Key Companies Across Verticals (Reference)

**Healthcare AI:**
| Company | Funding | Valuation | Focus |
|---------|---------|-----------|-------|
| Abridge | $773M | $5.3B | Ambient scribe (30% market share, 200+ health systems) |
| Hippocratic AI | $404M | $3.5B | Patient-facing AI agents (50+ health systems, 115M interactions) |
| Cohere Health | $200M | $5.5B | Prior authorization (12M PAs/year) |
| Ambience | $243M+ | N/A | AI medical scribe (13% share) |
| SmarterDx | $71M | N/A | Revenue integrity/coding (60+ systems, 5x growth) |

**Audit/Advisory AI:**
| Company | Funding | Valuation | Focus |
|---------|---------|-----------|-------|
| Fieldguide | $125M | $700M | AI audit/advisory (50% of top 100 CPA firms, 30-40% efficiency gains) |

**Financial Services / RegTech:**
| Company | Funding | Focus |
|---------|---------|-------|
| Bretton AI | $75M+ | AML risk remediation (Mercury, Ramp, Robinhood) |
| Hebbia | $159M ($700M val) | Finance document analysis (33% of top asset managers) |
| Aveni | £11M | FinLLM for UK financial services (Lloyds Banking Group) |
| Flagright | $4.3M | AI-native AML compliance (93% fewer false positives) |

**Construction AI:**
| Company | Funding | Focus |
|---------|---------|-------|
| Document Crunch | $30.5M | Contract compliance AI (Balfour Beatty, PCL, tripled rev 3 yrs) |
| PermitFlow | $54M | AI permit automation |
| ALICE Technologies | $47M | Construction scheduling optimization |

### What This Means for the Strategy

**If founder rejects insurance, the recommended path is:**

1. **Accounting/Tax (primary)** — Enter as "privacy-first fine-tuning for mid-market CPA firms." Start with tax return preparation from source documents. Seasonal urgency means selling in Q4, deploying in Q1, proving ROI by April. 75K+ potential customers with 1-3 month sales cycles. Accrual/Accordance are well-funded but focused on cloud SaaS/enterprise — the privacy-first on-prem niche for smaller firms is open.

2. **Healthcare Prior Auth (secondary)** — Larger TAM ($31B/yr) but requires clinical domain expertise and longer sales cycles. Better as a Series A expansion after proving the accounting model.

3. **The meta-strategy is unchanged:** EvenUp model (narrow wedge → data pipeline → expand). Privacy-first deployment. Domain-specific fine-tuning on 8B models. Compliance architecture. The vertical changes; the playbook doesn't.

**Detail:** `raw/2026-02-12-alternative-verticals-claude.md`

---

*Sources: Grand View Research, GM Insights, Polaris Market Research, Precedence Research, MarketsandMarkets, Menlo Ventures, EU AI Act official docs, CMMC/DoD publications, HIPAA guidance, company websites, Crunchbase, TechCrunch, Sacra, ABA Legal Industry Report 2025, PHUSE 2025, PMC/NIH, D-Wave case studies, SIGIR/ICTIR 2024, QuantumCLEF 2025, InsurancGPT whitepaper, Guidewire Connections 2025, Sixfold AI, Roots Automation, Gradient AI, Patra AI, FurtherAI, Pibit.AI, Panta, Amera, SignalFire, Forrester, NAIC, Fenwick, ZenML, Latka, AlleyWatch, Pulse2, Insurance Journal, SiliconANGLE, Getlatka, PeerSpot, Capterra, IBM Institute for Business Value, ITC Vegas, Quarles, EXL Insurance LLM whitepaper, NVIDIA NeMo/NIM, Bessemer Venture Partners (Vertical AI Playbook Jan 2026), Harvey AI/OpenAI case study, INS-MMBench (ICCV 2025), InsQABench (arxiv 2501.10943), FEMA OpenFEMA, NAIC SERFF Filing Access, SEC EDGAR, Hugging Face (Bitext, Snorkel, llmware, GutenOCR), Milliman (SERFF filing analysis), Shift Technology, ACORD.org, OpenOntology, OMG P&C Data Model, Chevron Newsroom, VentureBeat, Emerj, Microsoft Customer Stories, SPE JPT/OnePetro, nPlan, Klover.ai, Mordor Intelligence, Yahoo Finance, arxiv (EnergyGPT 2509.07177), AWS Blog (O&G fine-tuning), Chevron Careers, The Org, CGG/CMGL Accelerate, Protiviti, Hart Energy, ADNOC/AIQ, i2k Connect, H2O.ai, TotalEnergies, Baptista Research, BCG, EY, IBM IBV (O&G in AI era), Thomson Reuters (Thoughttrace acquisition), Honeywell (Chevron refinery collab Oct 2024), Publicis Sapient (Chevron supply chain), NobleAI (VIP Platform Jun 2025), Kiana Analytics, RECON Intelligence, Grooper/BisOK, nuEra/EAG, SparkCognition NLP, Landman.ai, ISG Provider Lens 2025 (O&G), C3.ai/Baker Hughes, Palantir (BP deal), CoLab Software, Snowflake, Shell.ai, Mistral AI, Cognite, Predictive Layer, GEP SMART, Arkestro, Percepto, MindBridge.ai, Bloomberg (Multiverse Computing €1.5B valuation), Multiverse Computing (CompactifAI, $215M raise Jun 2025, €100M ARR Jan 2026), Quantinuum ($800M Nov 2025, Helios 98 qubits), SandboxAQ ($5.75B, AQCat25, Aramco AI agreement), PsiQuantum ($7B, photonic QC), IonQ (NYSE: IONQ, $43M 2024 revenue), IQM ($320M Series B), Classiq ($200M+), QSimulate (Quelo/QIDO, Mitsui/Quantinuum), Phasecraft ($34M, Google/IBM partnerships), Algorithmiq ($38.8M, Aurora platform), HQS Quantum Simulations, Riverlane ($75M Series C, QEC), PQShield ($65M, NIST finalist), QuSecure (DoD customers), Strangeworks ($3.7M revenue), Horizon Quantum Computing ($500M SPAC), Zapata AI (bankrupt Oct 2024, restructured as Zapata Quantum Sep 2025), Q-CTRL ($50M+ sales 2025), Crypto Quantique (IoT security), Contrary Research (Harvey AI business breakdown), Scale VP (AI verticals framework), BVP (10 Principles for Vertical AI), EvenUp ($2B valuation, vertical AI unicorn), Modal Labs ($2.5B valuation), Cursor ($29.3B valuation, $1B ARR), Lovable ($100M ARR in 8 months), Cognition AI ($10.2B valuation, Devin), Predibase (acquired by Rubrik ~$100M Jun 2025), Snorkel AI ($148M revenue, $1.3B valuation), Strangeworks/Quantagonia acquisition (Aug 2025), Gurobi ($6.5M revenue, 35.2% market share), FICO Xpress (30.5% market share), Fortune Business Insights (MLOps, AI governance, privacy-preserving AI markets), Data Horizon Research (math optimization market), Protege AI ($65M raised, a16z), ValidMind (AI governance for banking/insurance), Waxed Mandrill Substack (Zapata collapse analysis). 310+ web searches across 25 research sessions (4 engines). All data as of February 2026.*
