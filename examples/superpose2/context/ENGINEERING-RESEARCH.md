# Superpose Engineering Research — Make Quantum Work for ML

**Last Updated:** 2026-02-12 (after seventeenth engineering research cycle — "Gate-based QC pre-seed unicorn paths" — 4 directions tested, 3 KILLED, 1 WOUNDED)
**Status:** Seventeen hypotheses tested: (1) LeapHybridCQM KILLED, (2) Sparsity mask optimization WOUNDED, (3) QUBO-native graph clustering WOUNDED, (4) Inference-time QUBO/HUBO for LLM reasoning WOUNDED, (5) NASA CR QUBO on D-Wave hybrid BQM WOUNDED, (6) Chevron oil & gas operations QUBO **REJECTED**, (7) RAG context optimization as QUBO **KILLED**, (8) Chevron seismic QUBO graph clustering **KILLED**, (9) FMQA for black-box optimization **WOUNDED**, (10) FMQA dense QUBO for Chevron well spacing **WOUNDED**, (11) Gate-based QC pivot for Chevron (quantum kernels, VQE/QAOA, quantum ML) **WOUNDED**, (12) "Classical-first, quantum-later" unicorn path **WOUNDED**, (13) "Classical ML-for-Chemistry → Quantum Chemistry" unicorn path **WOUNDED**, (14) CR QUBO compression to ~150 vars for QPU-native embedding **KILLED**, (15) S1 Hierarchical decomposition **KILLED**, (16) S2 Embeddings → binary codes → QUBO **KILLED**, (17) Gate-based QC pre-seed unicorn with $3M seed **WOUNDED** — tested 4 directions: QC Infrastructure (KILLED — 5+ funded competitors), Quantum Sensing + AI (WOUNDED — EuQlid $3M comparable but requires physics hardware expertise), Narrow Quantum Chemistry (KILLED — wrong team/funding for $3M), Classical AI + Quantum Moat (KILLED — "quantum-ready" = zero differentiation). Key new findings from cycle 17: (a) EuQlid ($3M seed, $1.5M early revenue) proves quantum sensing + AI path viable at $3M but requires physics co-founder. (b) No pre-seed gate-based quantum startup has successfully followed classical-first unicorn path. (c) Post-Zapata investor sentiment cautious but not toxic (Zapata restructured as Zapata Quantum 2025). (d) Quantum sensing market $860M (2026) → $1.56B (2031). 116 findings total.
**Classification:** CONFIDENTIAL — Internal Only

---

## 1. The Problem

Market research (97+ searches, 9/9 deep dives) concluded: **quantum annealing does NOT currently help ML/AI at practical problem scales.** Classical solvers are good enough.

Three barriers killed every ML direction:

| Barrier | Why It Kills | Market Research Evidence |
|---------|-------------|------------------------|
| **Scale** | ML problems need 10K-1M+ vars. D-Wave has ~5K qubits. Decomposition makes sub-problems trivially classical. | Dir A (SFT): Gurobi handles 50K. Dir G (GPU sched): needs millions. Dir I (merging): 100-160 vars (trivially classical). |
| **Continuous** | ML optimization is continuous (gradients, weights, mixtures). QUBO is binary. | Dir D (mixtures): "WRONG FORMALISM — continuous, not binary." |
| **Eval Bottleneck** | QUBO coefficients require evaluating ML models. Training a model per candidate = hours. Quantum speedup on the search step is irrelevant. | Dir I (merging): "eval cost dominates — quantum speedup on millisecond search step is irrelevant." |

**This research track's mission: break through these barriers or conclusively prove they're unbreakable.**

---

## 2. Attack Vectors — Status Board

### Barrier 1: Scale

| # | Attack Vector | Status | Verdict | Notes |
|---|--------------|--------|---------|-------|
| S1 | Hierarchical decomposition where sub-problems stay hard | **EXPLORED** | **KILLED** | Decomposition destroys density/hardness (subs easier classical); no ML papers; qbsolv trivializes. See `raw/2026-02-13-eng-S1-hierarchical-decomp-{claude,grok}.md`. |
| S2 | Problem reformulation via embeddings → binary codes → QUBO | **EXPLORED** | **KILLED** | Binary hashing loses 5-10% fidelity (arXiv:1908.08677); no QA >10% advantage on embedding-QUBOs (no papers); Gram matrix low-rank, classically easy (arXiv:2106.10532). See `raw/2026-02-12-eng-previous-studies-are-done-by-claude-and--grok.md`. |
| S3 | Iterative quantum-classical loops (quantum as subroutine) | UNEXPLORED | — | Quantum solves bottleneck at each classical iteration |
| S4 | Advantage2 hardware (7K+ qubits, Zephyr topology) | PARTIALLY EXPLORED | WOUNDED | Shipped 4,400 qubits (not 7K). Zephyr 20-way connectivity. 40% energy scale improvement. Does NOT change calculus for ML — the barrier is formulation, not qubit count. |
| S5 | D-Wave hybrid solvers (LeapHybridBQM/CQM/DQM, up to 1M vars) | **EXPLORED** | **KILLED** | Hybrid is ~98.6% classical (tabu search + SA). QPU handles tiny binary sub-problems. CQM continuous vars = linear only (zero quadratic). Loses to Gurobi on MILP 4.6-4.8x. Wins ONLY on dense BQP ~500 binary vars. See `raw/2026-02-12-eng-hybrid-cqm-claude.md`. |
| S6 | Problem-specific variable reduction techniques | UNEXPLORED | — | Graph sparsification, constraint tightening, variable fixing |

### Barrier 2: Continuous → Binary

| # | Attack Vector | Status | Verdict | Notes |
|---|--------------|--------|---------|-------|
| C1 | Binary encoding (thermometer, one-hot, Gray codes) at useful precision | UNEXPLORED | — | At what precision does QUBO become tractable? |
| C2 | D-Wave CQM solver (native continuous + integer + binary) | **EXPLORED** | **KILLED** | CQM continuous variables: LINEAR ONLY. `max_quadratic_variables_real = 0`. Cannot encode x_i*x_j where x is continuous. This kills ALL continuous ML optimization (L2 reg, covariance, kernels, loss surfaces). Continuous vars processed entirely by classical component. See `raw/2026-02-12-eng-hybrid-cqm-claude.md`. |
| C3 | Naturally discrete ML problems disguised as continuous | **EXPLORED** | **WOUNDED** | Sparsity masks ARE naturally binary and QUBO-amenable. But the pruning Hessian is low-rank (not dense), so D-Wave's sweet spot doesn't apply. iCBS (arXiv:2411.17796) confirms formulation works but uses classical SA. See `raw/2026-02-12-eng-pruning-sparsity-claude.md`. |
| C4 | Discrete approximation — when is "close enough" close enough? | UNEXPLORED | — | Quantized models already work. Is 4-bit precision enough for QUBO? |

### Barrier 3: Eval Bottleneck

| # | Attack Vector | Status | Verdict | Notes |
|---|--------------|--------|---------|-------|
| E1 | Surrogate objectives (cheap proxies that correlate with downstream perf) | PARTIALLY EXPLORED | WOUNDED | Calibration-data Hessian ((1/n)*A^T*A) works as surrogate for pruning loss — used by iCBS, SparseGPT, OPTIMA. But Hessian computation dominates iCBS runtime (7.9 days for Mistral-7B). Eval bottleneck is partially bypassed but Hessian cost replaces it. |
| E2 | Transfer: solve on small proxy, transfer solution to large model | UNEXPLORED | — | QUBO on 1B model → apply to 70B? |
| E3 | Problems where objective IS the QUBO (no external eval) | **EXPLORED** | **WOUNDED** | Graph clustering, community detection, k-medoids, correlation clustering ARE naturally QUBO. Bypasses Barrier 3 (Eval) + Barrier 2 (Continuous). But QPU limited to ~150 fully connected vars (~140 nodes). QPU matches Louvain/Leiden quality — no >10% advantage. Classical heuristics run in ms; exact Gurobi ILP in minutes. See `raw/2026-02-12-eng-qubo-native-objective-claude.md`. |
| E4 | Amortized evaluation — solve many instances, learn the mapping | UNEXPLORED | — | Meta-learning the QUBO → solution → quality function |

### Cross-Barrier / Novel Approaches

| # | Attack Vector | Status | Verdict | Notes |
|---|--------------|--------|---------|-------|
| X1 | Reshape the ML problem to fit quantum (not vice versa) | UNEXPLORED | — | What ML paradigms are naturally combinatorial? |
| X2 | Quantum-native ML (not bolting quantum onto classical ML) | UNEXPLORED | — | QBMs, quantum kernel methods, quantum reservoir computing |
| X3 | Transfer from adjacent fields (quantum chemistry, materials) | UNEXPLORED | — | What techniques do they use to handle scale/encoding? |
| X4 | Emerging academic work (2025-2026 papers) | UNEXPLORED | — | New formulations we haven't seen yet |
| X5 | QUBO for inference-time compute (search over reasoning paths) | **EXPLORED** | **WOUNDED** | QCR-LLM (arXiv:2510.24509) + NASA CR (arXiv:2407.00071) are REAL. HUBO formulation with 35-90 binary vars. Bypasses Barriers 2+3 cleanly. BUT: classical SA matches quantum BF-DCQO within +0.0-1.0pp. Fails Advantage gate. CR framework valuable as classical product; quantum adds nothing at current scale. See `raw/2026-02-12-eng-inference-time-qubo-claude.md`. |
| X6 | Stride surrogate modeling: ML inside quantum optimization | UNEXPLORED | — | (NEW from eng cycle 1) D-Wave's Stride solver now embeds ML models as surrogates inside optimization. Inverts the relationship. Worth investigating for E1/E2. |
| X7 | Dense BQP sweet spot (~500 binary vars): map ML sub-problems | **EXPLORED** | **WOUNDED** | Sparsity mask optimization is the best candidate found. QUBO formulation is valid (iCBS, arXiv:2505.16332). But the pruning Hessian is low-rank, not dense. D-Wave QPU can only embed ~150 fully connected vars. And classical SparseGPT/Wanda are already extremely fast. See `raw/2026-02-12-eng-pruning-sparsity-claude.md`. |
| X8 | MoE expert routing as batch-level QUBO | UNEXPLORED | — | (NEW from eng cycle 2) In Mixtral-style MoE, each token selects top-k from N experts. Joint routing across a batch could be QUBO. But must run at inference speed (microseconds) — D-Wave latency kills this. |
| X9 | BNN weight optimization as native QUBO | **EXPLORED** | **BLOCKED** | (Eng cycle 18) BNN weights ARE natively {-1,+1} and QUBO formulation EXISTS (arXiv:2107.02751, arXiv:2601.00449). BUT: (1) Existing formulations need O(K*N) variables (K=samples, N=neurons) -- 37 neurons max with 4 samples; (2) Layer-wise weight-only reformulation DECOMPOSES per-neuron to m-variable sub-problems (m=fan-in) -- trivially classical for m <= 150; (3) QPU max clique K_177 on Advantage2 -- barely fits one neuron with 177 inputs; (4) Post-training binarization to 1-bit FAILS catastrophically (arXiv:2510.16075); (5) STE+BN works well enough (BNNs within 3% of full-precision). Three novel ideas spawned: X38 (coupled multi-neuron QUBO), X39 (BNN architecture search as QUBO), X40 (ternary weight optimization for BitNet). See `raw/2026-02-12-eng-bnn-qubo-claude.md`. |
| X10 | npj QI dense BQP hybrid benchmark methodology | **EXPLORED** | **KILLED** | (NEW from eng cycle 2) arXiv:2504.06201 used Leap Hybrid sampler (~98% classical). 6561x speedup = classical D-Wave software, not quantum advantage. |
| X11 | Batch small-graph clustering: amortized QPU throughput | UNEXPLORED | — | (NEW from eng cycle 3) QPU processed 300x more sub-problems than hybrid DQM (arXiv:2410.07744). Molecular graphs, knowledge sub-graphs batch clustering. But each sub-problem is trivially classical (10-50 nodes). |
| X12 | K-medoids dense QUBO at D-Wave's sweet spot | UNEXPLORED | — | (NEW from eng cycle 3) Medoid-only formulation: N vars, fully dense dissimilarity matrix. IS D-Wave's sweet spot. But N=150 trivially solvable by PAM. |
| X13 | Index tracking / portfolio replication as QUBO | UNEXPLORED | — | (NEW from eng cycle 3) Market graph clustering QUBO for index tracking. ~500 vars for S&P 500. Real financial use case. Classical methods handle it. |
| X14 | CR framework as classical inference-time scaling product | UNEXPLORED | — | (NEW from eng cycle 4) The combinatorial reasoning framework (QUBO/HUBO formulation for reasoning fragment selection) shows +4.5-8.3pp over base GPT-4o with classical SA. No quantum needed. Could be productized as a reasoning enhancement API. Must first compare to majority voting. |
| X15 | Agentic tool-call path selection as QUBO | UNEXPLORED | — | (NEW from eng cycle 4) Agent tool-call sequences are discrete and combinatorial. M tools, B outcomes, T steps = M^T paths. If path quality coefficients come from historical data (not per-instance LLM eval), QUBO formulation could work. But variable count may explode. |
| X16 | QUBO-only (quadratic, no cubic) reasoning fragment selection on D-Wave | **EXPLORED** | **WOUNDED** | NASA CR QUBO (avg 900 vars, pure quadratic) IS D-Wave compatible. Co-occurrence matrix is ~98% dense. Hybrid solver handles 900 vars in ~15-18s. BUT: (1) hybrid is ~98% classical; (2) QPU can't embed 900 dense vars (max ~150); (3) VeloxQ matches hybrid 1000x faster; (4) CR vs majority voting never compared; (5) **Linear CR (68.2%) OUTPERFORMS Quadratic CR (65.2%)** — the quadratic QUBO terms HURT accuracy. See `raw/2026-02-12-eng-nasa-cr-dwave-claude.md`, Finding 29. |
| X17 | BF-DCQO as commercial quantum reasoning product on IBM hardware | PARTIALLY EXPLORED | WOUNDED | (NEW from eng cycle 4, updated cycle 5) Kipu Quantum's BF-DCQO handles HUBO natively on IBM 156-qubit Heron. BUT arXiv:2509.14358 shows D-Wave QPU outperforms BF-DCQO 100x faster with better quality, and BF-DCQO's quantum contribution is "minimal." This undermines the IBM path. |
| X18 | Compress CR QUBO to ~150 vars for QPU-native dense embedding | **EXPLORED** | **KILLED** | Compression loses >5% downstream accuracy fidelity (no evidence of preservation, general coarsening 10-15% energy loss); QPU on dense BQP ~150 vars shows <10% consistent advantage over SA (5-15% instance-dependent). Quadratic CR already hurts vs linear. See `raw/2026-02-12-eng-cr-compress-qpu-{claude,grok}.md`. |
| X19 | Batch small-QUBO reasoning throughput on QPU | UNEXPLORED | — | (NEW from eng cycle 5) QPU batch throughput is 300x higher than hybrid DQM. If compressed ~150-var reasoning QUBOs served at 1000+ queries/min, QPU throughput could provide amortized advantage. Requires high-volume use case (reasoning API). |
| X20 | Coefficient distribution engineering for quantum hardness | UNEXPLORED | — | (NEW from eng cycle 5) Engineer QUBO construction to produce heavy-tailed coefficients (log-transform co-occurrence, power-law similarity). Heavy-tailed distributions make problems harder for classical SA but not for quantum approaches. "Problem shaping for quantum advantage." |
| X21 | Chevron oil & gas operations optimization as QUBO (PIVOT) | **EXPLORED** | **REJECTED** | (NEW from eng cycle 6) PIVOT hypothesis: oil & gas operations problems (well placement, drilling scheduling, vessel routing, CCUS, asset portfolio) formulated as QUBO for D-Wave. **REJECTED** on all 8 problem types. Three fatal issues: (1) Well placement (highest value) is killed by eval bottleneck -- each QUBO coefficient requires reservoir simulation (min-hours per eval); (2) Scheduling/routing problems are MILP (sparse, constrained, mixed-integer), not dense BQP; (3) Chevron has world-class classical OR (PETRO LP: ~$10B value, ~$1B/year). Chevron invested in OQC (gate-based), not D-Wave. NO oil & gas company uses D-Wave. See `raw/2026-02-12-eng-chevron-qubo-ops-claude.md`. |
| X22 | Offline RAG index optimization via QUBO (k-medoids/facility location) | UNEXPLORED | — | (NEW from eng cycle 7) Use QUBO for offline selection of representative chunks per topic cluster. Minutes/hours acceptable. But k-medoids at 1K-100K per cluster is efficiently solved by PAM/CLARA. Unlikely to need quantum. |
| X23 | Multi-document reasoning path selection as QUBO | UNEXPLORED | — | (NEW from eng cycle 7) For multi-hop questions: each candidate reasoning path (chain of 2-5 chunks) is a binary variable. With 50 chunks and 3-hop: C(50,3) = 19,600 candidate paths. BUT: evaluating path quality requires LLM = eval bottleneck (Barrier 3 returns). |
| X24 | Enterprise RAG "context budget" allocation as QUBO (knapsack variant) | UNEXPLORED | — | (NEW from eng cycle 7) Binary include/exclude with token budget constraint + pairwise source diversity. This is a knapsack with pairwise interactions. Still 20-500 items = trivially classical. KILLED by scale. |
| X25 | RAG context optimization as QUBO for D-Wave (Chevron enterprise RAG) | **EXPLORED** | **KILLED** | (NEW from eng cycle 7) RAG chunk include/exclude as QUBO with pairwise relevance x redundancy from embeddings. **KILLED** by three independent gates: (1) Scale: 20-500 candidates trivially classical; (2) Advantage: quality gap 0.8-5.2% (SMART-RAG arXiv:2409.13992) below 10% threshold; (3) Latency: D-Wave 15-18s vs DPP greedy <2ms. NLP community solved this with 7+ papers (SMART-RAG, DF-RAG, SetR, VRSD, InSQuaD, Stochastic RAG). No paper uses QUBO. VRSD proved NP-complete but O(kn) heuristic beats MMR 90%+. See `raw/2026-02-12-eng-chevron-rag-qubo-claude.md`. |
| X26 | Seismic inversion via QUBO on D-Wave (Aramco path) | UNEXPLORED | — | (NEW from eng cycle 8) Aramco/D-Wave extended agreement (June 2024) for seismic imaging QUBO. The ONE real D-Wave geoscience application. 300 real vars -> 900 QUBO vars, decomposed 30 layers x 10 vars. QPU contributes 0.043-0.085s of 4-9s total. Worth monitoring Advantage2 results but QPU fraction is tiny. |
| X27 | Ground-motion station clustering as dense QUBO (~1000 nodes) | UNEXPLORED | — | (NEW from eng cycle 8) Earthquake seismology: ~1000 geophones, dense Pearson correlation matrix, community detection reveals fault structures. IS D-Wave's sweet spot (dense, ~1000 nodes). But academic seismology, not commercial oil & gas. Signed spectral clustering is current method. |
| X28 | Batch small-subgraph seismic clustering on QPU | UNEXPLORED | — | (NEW from eng cycle 8) Pre-partition survey into thousands of 100-trace sub-regions, submit dense sub-QUBOs to QPU. Leverages QPU batch throughput (300x vs hybrid). But 100-trace sub-problems are trivially classical and spatial partitioning is arbitrary. |
| X29 | Chevron seismic QUBO graph clustering for geological zonation | **EXPLORED** | **KILLED** | (NEW from eng cycle 8) Modularity QUBO on seismic trace similarity graph for facies classification. **KILLED** by three independent gates: (1) Scale: F3 dataset = 619K traces per horizon, real surveys = 10M+. QUBO needs N*K vars = millions. QPU max ~150 fully-connected. (2) Advantage: Seismic graphs are sparse k-NN; Leiden handles 3.8M nodes in 3s on GPU. (3) Problem mismatch: Geophysics uses SOM/k-means/autoencoders, never graph QUBO. Deep learning achieves 97%+ facies accuracy. ADNOC ENERGYai: 10x speed, 70% precision with classical AI. See `raw/2026-02-12-eng-chevron-seismic-qubo-claude.md`. |
| X30 | FMQA (Factorization Machine + Quantum Annealing) for black-box optimization | **EXPLORED** | **WOUNDED** | (Eng cycle 9) FMQA is real and validated (15+ papers, 2020-2026). FM surrogate maps directly to QUBO, bypassing Barrier 3 (25-80x fewer evaluations than full QUBO) and Barrier 2 (binary natural). Kernel-QA extension scales to 640 binary vars, outperforms Bayesian optimization 5-7x at d=80. **BUT:** every paper at 100+ vars uses classical SA or GPU Ising (Amplify AE, 256K vars) — not D-Wave. QPU tested only at 14-60 vars (trivially classical). FM fidelity for physics-based problems (reservoir sim) unproven. No well placement FMQA paper exists. **Quantum adds nothing.** FMQA value is in the FM surrogate, not the quantum solver. See `raw/2026-02-12-eng-fmqa-chevron-claude.md`. |
| X31 | FMQA as classical product for expensive binary black-box optimization | UNEXPLORED | — | (NEW from eng cycle 9) FMQA with classical SA is genuinely useful for binary black-box optimization. Outperforms Bayesian optimization at 100+ binary vars (kernel-QA results). Never applied to well placement, CCUS site selection, or facility location. Could be a Superpose product WITHOUT any quantum component. |
| X32 | Dense FM QUBO characterization experiment | **EXPLORED** | **WOUNDED** | (Eng cycle 9, updated cycle 10) **ANSWERED:** FM QUBOs are DENSE (all Q_ij nonzero, Gram matrix V*V^T) but LOW-RANK (rank = K, the FM latent dimension, typically 8-16). Dense + low-rank is NOT the same as dense + full-rank. D-Wave's sweet spot (Finding 5) was benchmarked on dense FULL-RANK BQP. Low-rank dense QUBOs are structurally easier for classical solvers via eigenvalue-guided search. This creates an Advantage Paradox: small K = easy QUBO (no quantum advantage); large K = hard QUBO but FM fidelity degrades. Diagonal terms w_i in Q = diag(w) + V*V^T may restore hardness -- empirical test needed. See `raw/2026-02-12-eng-chevron-fmqa-dense-claude.md`, Finding 60. |
| X33 | Kernel-QA + GPU Ising as scalable classical BO alternative | UNEXPLORED | — | (NEW from eng cycle 9) Kernel-QA (arXiv:2501.04225) with Amplify AE (256K vars) outperforms Bayesian optimization 5-7x at d=80. Classical tool, no quantum. Could be commercialized for combinatorial/mixed-integer optimization. |
| X34 | High-K FM / DeepFM to produce full-rank dense QUBOs | UNEXPLORED | — | (NEW from eng cycle 10) If low-rank FM QUBOs kill quantum advantage, use DeepFM with K=100+ for high-rank QUBOs. DeepFM's deep component captures higher-order interactions; FM component maps to QUBO. But only the FM portion is QUBO-native -- deep network predictions cannot be encoded in QUBO. Requires further analysis. |
| X35 | Diagonal-dominant FM QUBO as instance hardness shaping | UNEXPLORED | — | (NEW from eng cycle 10) Engineer FM training to produce large, diverse diagonal terms w_i via strong per-well economic priors. Q = diag(w) + V*V^T becomes full-rank when w entries are diverse. "Problem shaping for quantum advantage" applied to FMQA. Could make the QUBO genuinely hard for classical SA while staying within D-Wave's dense BQP sweet spot. |
| X36 | FMQA as classical product for well placement (no quantum) | UNEXPLORED | — | (NEW from eng cycle 10) FMQA with classical SA for binary well placement at 100-200 candidates. Outperforms Bayesian optimization (which fails >60 binary vars). ~500-2000 reservoir sims vs 40,000 for full QUBO. Classical product, no D-Wave dependency. Could be a Superpose consulting tool for operators. Competes with GA + MLP surrogate (300 sims, proven). |
| X37 | Kernel-QA for well placement at 200+ binary variables | UNEXPLORED | — | (NEW from eng cycle 10) Kernel-QA (arXiv:2501.04225) with GPU Ising solver scales to 640 binary vars. Applied to well placement with 200-500 candidates could outperform BO. Avoids FM's low-rank limitation. Classical GPU solver, not quantum. |
| X38 | Coupled multi-neuron BNN QUBO with structured output correlation | UNEXPLORED | — | (NEW from eng cycle 18) Instead of per-neuron decomposition, add output decorrelation penalties coupling neurons in same layer. Creates dense m*n-variable QUBO for small layers (13x13=169 fits QPU). BUT: coupling terms are artificial, may not improve accuracy vs independent per-neuron optimization. |
| X39 | BNN architecture search as QUBO (NAS-BNN) | UNEXPLORED | — | (NEW from eng cycle 18) Optimize BNN architecture choices (which layers to binarize, which channels to keep) as QUBO. Binary decisions with pairwise compatibility interactions. 100-500 vars for moderate network. Must check if interactions are dense or sparse. |
| X40 | Ternary weight optimization for BitNet-style models | UNEXPLORED | — | (NEW from eng cycle 18) BitNet {-1,0,+1} ternary weights encoded as 2 binary vars per weight (sign + zero-mask). For m=88 inputs: 176 QUBO vars per neuron, barely fits Advantage2 K_177. Ternary landscape (3^m) harder than pure binary. Closer to actual BitNet paradigm. Per-neuron decomposition still applies. |

### Gate-Based Quantum Computing (NEW — eng cycle 11)

| # | Attack Vector | Status | Verdict | Notes |
|---|--------------|--------|---------|-------|
| G1 | Quantum chemistry simulation for catalyst design (VQE/QPE on molecular Hamiltonians) | **EXPLORED** | **WOUNDED-ALIVE** | (Eng cycle 11) The ONE surviving gate-based direction. Matches Chevron's OQC investment rationale. VQE for Ni-CO2 hydrogenation: 8.6 kcal/mol vs DFT 14.2 vs experiment 9.0. FeMoco needs 152+ logical qubits. Microsoft/Quantinuum: 2 logical qubits (Sep 2024). PhaseCraft: 10x efficiency gain (THRIFT). BUT: fault-tolerant QC required (2029+). Competes with PhaseCraft, Microsoft, QC Ware, Quantinuum. Not ML. See `raw/2026-02-12-eng-gate-based-qml-energy-claude.md`, Findings 71, 78, 79. |
| G2 | Quantum kernels for molecular/materials descriptor data | **EXPLORED** | **KILLED** | (Eng cycle 11) 20,000+ models across 64 datasets: no systematic advantage (arXiv:2409.04406). Exponential concentration at scale (Nature Comms 2024). Circuits without entanglement match or beat entangled. Fe-Ga-Pd result loses to cosine similarity. See Findings 66, 67, 77. |
| G3 | VQE/QAOA for reservoir simulation sub-problems | **EXPLORED** | **KILLED** | (Eng cycle 11) VQE for reservoir simulation does NOT exist in literature. Reservoir sim is PDE (Darcy flow), not eigenvalue problem. QAOA 2-3x worse than NSGA-II on building energy benchmark. See Findings 69, 85. |
| G4 | Quantum neural networks / variational quantum ML on energy data | **EXPLORED** | **KILLED** | (Eng cycle 11) Cerezo et al. (Nature Comms 2025): trainable -> classically simulable. Barren plateau/simulability duality kills the entire program. 22 QML energy use cases reviewed: NONE show advantage. QRC matches but never beats LSTM. See Findings 68, 70, 76. |
| G5 | Quantum-enhanced Bayesian optimization for materials discovery | UNEXPLORED | — | (NEW from eng cycle 11) Quantum kernel in GP prior for active learning in composition space. Fe-Ga-Pd result (arXiv:2601.11775) shows promise with 25 qubits on IonQ Aria. Needs validation at scale against best classical GP kernels. |
| G6 | Quantum chemistry orchestration platform (HPC + quantum + AI) | UNEXPLORED | — | (NEW from eng cycle 11) Microsoft demonstrated the workflow (Sep 2024). Could Superpose build the integration/orchestration layer? Not a quantum advantage product per se, but a platform play for the 2029+ market. Requires chemistry domain expertise. |
| G7 | Quantum readiness consulting for energy companies | UNEXPLORED | — | (NEW from eng cycle 11) Energy companies investing in QC but producing zero results. Need help evaluating which problems genuinely benefit from quantum. Near-term revenue while hardware matures. Not a $100M+ product. |

### "Classical-First, Quantum-Later" Unicorn Paths (NEW — eng cycle 12)

| # | Path | Status | Verdict | Notes |
|---|------|--------|---------|-------|
| P1 | Quantum-inspired optimization platform (Strangeworks/Quantagonia model) | **EXPLORED** | **KILLED** | (Eng cycle 12) QAOA needs 73.91M physical qubits for advantage at 179 vars (arXiv:2504.01897). Quantum NEVER helps optimization on any published hardware roadmap. Strangeworks already acquired Quantagonia. Classical optimization market mature, low-margin. See `raw/2026-02-12-eng-gate-qc-unicorn-path-claude.md`. |
| P2 | AI-powered quantum chemistry SaaS (QC Ware/Promethium model) | **EXPLORED** | **KILLED for pre-seed** | (Eng cycle 12) Right strategy, wrong team, wrong funding level. Quantum chemistry IS the one genuine quantum advantage application (2029). But requires PhD quantum chemists + pharma domain. QC Ware ($42M), QSimulate ($11M), Algorithmiq ($38.8M) all ahead. |
| P3 | LLM compression via tensor networks (Multiverse model) | **EXPLORED** | **KILLED** | (Eng cycle 12) Multiverse has EUR 100M ARR, $250M+ funding, 160 patents, 7-year head start, 100+ customers. Cannot be replicated at $3M pre-seed. |
| P4 | PQC migration / crypto management (SandboxAQ model) | **EXPLORED** | **KILLED for Superpose** | (Eng cycle 12) Real $1.15B market but requires cybersecurity expertise. SandboxAQ ($950M), PQShield ($65M), QuSecure ($28M) heavily funded. Wrong company. |
| P5 | Classical Monte Carlo + quantum amplitude estimation (quantum finance) | **EXPLORED** | **KILLED** | (Eng cycle 12) Needs 4,700-8,000 logical qubits for advantage. IBM Starling (2029) = 200 logical qubits. Timeline: 2032-2035 at earliest. Banks do this in-house (JPMorgan, Goldman). |
| P6 | Quantum readiness consulting platform | **EXPLORED** | **KILLED as unicorn** | (Eng cycle 12) Consulting doesn't scale to $100M+. Dominated by IBM, Protiviti, BCG, McKinsey, Deloitte. |
| P7 | Insurance AI with quantum-ready architecture positioning | UNEXPLORED | — | (NEW from eng cycle 12) Build insurance AI product (Plan B5), include "quantum-ready" language in pitch. Costs nothing technically. Provides narrative differentiation. Lowest-cost way to capture quantum upside while building real classical revenue. |
| P8 | Classical ML-for-Chemistry → Quantum Chemistry transition (AI-for-science) | **EXPLORED** | **WOUNDED** | (Eng cycle 13) Quantum transition IS technically sound: same customers, same data pipelines, Microsoft demonstrated hybrid classical-ML-quantum workflow (Sep 2024). BUT: 8+ competitors at >$100M (CuspAI $130M, Orbital $200M, Periodic Labs $300M SEED, Schrödinger $5B mkt cap, SandboxAQ $5.75B, Microsoft infinite). Competition gate FAILS. "Quantum-ready" = zero moat (every competitor has same story). $3M insufficient for credible molecular simulation product. ONLY viable at $3M as extreme vertical niche (specific catalyst class). PhaseTree (€3M) and Rowan ($2.1M) show small teams CAN enter but compete on UX/accessibility, not model quality. See `raw/2026-02-12-eng-classical-ml-chem-unicorn-claude.md`. |
| P9 | QC Infrastructure Software (circuit compilers, error mitigation, middleware) | **EXPLORED** | **KILLED** | (Eng cycle 17) 5+ well-funded competitors: Classiq ($173M, $110M Series C, $30-50K/seat, tripled revenue YoY), Q-CTRL ($50M+, quantum sensing pivot), Riverlane ($75M, QEC decoders, "low millions" revenue, 60%+ QC company partnerships), Strangeworks (acquired Quantagonia). Open-source commoditization (Qiskit, Cirq, PennyLane free). $3M cannot compete. See `raw/2026-02-12-eng-gate-qc-preseed-unicorn-gemini.md`. |
| P10 | Quantum Sensing + Classical AI (NV-diamond magnetometry for semiconductor/battery/NDT) | **EXPLORED** | **WOUNDED** | (Eng cycle 17) EuQlid ($3M seed, $1.5M early revenue, Harvard/Yale/TI team) proves model works at $3M. Huge TAM: quantum sensing $860M→$1.56B (2031), NDT $22-56B (2035). Commercially deployed NOW. BUT: requires physics hardware expertise (NV-diamond fabrication, condensed matter PhDs). Superpose has ML team, not physics team. QuantumDiamonds €152M government backing for same space. SandboxAQ ($5.75B), Infleqtion ($100M+), Q-CTRL all in sensing. Hardware supply chain is the moat, not software. Adversarial critique: "You're an AI-for-NDT company with exotic sensor. Replace 'quantum diamond' with 'hyperspectral camera' and business model is identical." See `raw/2026-02-12-eng-gate-qc-preseed-unicorn-gemini.md`. |
| P11 | Narrow Quantum Chemistry niche at $3M (specific catalyst class) | **EXPLORED** | **KILLED for Superpose** | (Eng cycle 17) Same finding as P2/P8 but tested independently with pre-seed lens. Requires PhD quantum chemists + pharma/materials domain. QC Ware ($42M, Promethium $18-100/hr), QSimulate ($11M), Algorithmiq ($38.8M), CuspAI ($130M), Orbital ($200M) all ahead. Pharma sales cycle 6-18 months vs $3M ~18-month runway. Materials companies have shorter cycles (2-6 months) but lower ACV ($50-200K). ARPA-E QC3 program ($30M) funds national labs, not startups. See `raw/2026-02-12-eng-gate-qc-preseed-unicorn-gemini.md`. |
| P12 | Classical AI product with "quantum-ready" positioning (insurance AI, optimization) | **EXPLORED** | **KILLED** | (Eng cycle 17) "Quantum-ready architecture" = modular software design = basic engineering, not a moat. ANY team can claim this. Post-Zapata (bankrupt Oct 2024, restructured Sep 2025), "quantum" branding may be negative signal to investors. VCs increasingly demand demonstrated quantum advantage, not positioning. SandboxAQ succeeds because they sell CLASSICAL products that work, not "quantum-ready" promises. Zero differentiation from any classical AI startup. |

---

## 3. Findings

### Finding 103: Hierarchical QUBO Decomposition Fails to Preserve Quantum Advantage (2026-02-13)\n\n**Source:** Grok deep research (17 searches), D-Wave qbsolv docs (arXiv:1607.04600), multilevel QUBO (arXiv:1902.04524), pruning (arXiv:2411.17796).\n\nDecomposition (graph partitioning METIS/KaHIP, qbsolv bisection, coarsening) localizes interactions: dense global → sparse/easy subs. Zero ML papers with hardness-preserving decomp for D-Wave dense BQP sweet spot (~500 vars). Pruning blocks low-rank classical-easy (Finding 7). qbsolv subs trivial (<100 vars), QPU marginal.\n\n**Kills S1.** Partitioning destroys density (#1), no ML advantage preservation (#3).\n\n### Finding 112: Binary Embeddings for QUBO Reformulation Fail Fidelity Gate (2026-02-12)\n\n**Source:** Grok Engine 2 (20+ searches), arXiv:1908.08677 (hash fidelity), arXiv:2106.10532 (low-rank QUBO).\n\nBinary hashing (32-64 bits) loses 5-10% mAP/retrieval utility vs continuous embeddings. Gram matrix V V^T from embeddings is low-rank (dim K << N vars), enabling classical eigendecomp-guided solvers. No papers show QA >10% on embedding-QUBOs 200-500 vars. Kills S2: Encoding destroys advantage; no evidence trail.\n\n### Finding 113: No Pre-Seed Gate-Based Quantum Startup Has Successfully Followed Classical-First Unicorn Path (2026-02-12)

**Source:** Gemini deep search (Engine 1), 15+ Engine 3 web searches across quantum startup databases, investor reports, press releases.

Exhaustive search across quantum startup funding databases, investor reports, and press coverage found NO example of a pre-seed gate-based quantum computing startup successfully executing a "classical-first unicorn path" — generating classical revenue to fund long-term quantum R&D toward unicorn status. The closest examples are NOT pre-seed: SandboxAQ (Alphabet spinoff, $950M, $5.75B valuation) and Multiverse Computing (EUR 100M ARR, $250M+, 7-year head start). Pre-seed comparable: EuQlid ($3M seed + $1.5M early revenue) but uses quantum SENSING, not gate-based QC. Haiqu ($4M pre-seed) targets quantum software but no classical revenue reported. Challenges: (1) long R&D cycles, (2) high capital requirements, (3) investor focus on quantum IP not classical revenue at pre-seed.

**Implication:** The classical-first unicorn path for gate-based QC at pre-seed is uncharted territory. No blueprint exists. The companies that succeeded at "classical-first" all had massive head starts or non-pre-seed funding.

### Finding 114: QC Infrastructure Software Market Is Dominated by Well-Funded Incumbents (2026-02-12)

**Source:** Classiq ($110M Series C, SiliconAngle), Riverlane ($75M, QLOC decoder), Q-CTRL ($50M+, sensing pivot), Strangeworks/Quantagonia acquisition

QC infrastructure has 5+ companies with >$50M funding each: Classiq ($173M total, $30-50K/seat, tripled revenue YoY), Q-CTRL (error suppression + sensing, $50M+), Riverlane ($75M, QEC real-time decoders on FPGA/ASIC, partners with 60%+ of quantum computer companies), Strangeworks (acquired Quantagonia for optimization platform). Open-source alternatives (Qiskit, Cirq, PennyLane) are free and backed by IBM, Google, Xanadu respectively. $3M pre-seed cannot compete in middleware/compilers/error mitigation.

**Kills P9.** Competition gate fails catastrophically.

### Finding 115: EuQlid Proves Quantum Sensing + AI Model Viable at $3M But Requires Physics Team (2026-02-12)

**Source:** SiliconAngle (Nov 2025), The Quantum Insider, Tom's Hardware, qdm.io

EuQlid: $3M seed + $1.5M early customer revenue. Founded by Ronald Walsworth (Harvard/UMD atomic physicist), David Glenn (Yale physics), Sanjive Agarwala (semiconductor industry — TI, Cadence). First-gen QDM already deployed at Harvard, NYU, Oxford, Curtin. Qu-MRI platform combines quantum magnetometry + signal processing + ML for non-destructive 3D imaging of semiconductors and batteries. The team has BOTH physics hardware expertise (Walsworth/Glenn: NV-diamond pioneers) AND semiconductor industry expertise (Agarwala: TI/Cadence). The model works because quantum sensors are commercially available NOW (unlike gate-based QC) and the classical AI layer adds immediate value.

**Implication:** The EuQlid model is the ONE $3M-scale quantum startup path that works. BUT it requires a physics co-founder with NV-diamond or equivalent quantum sensing expertise. An ML-only team cannot replicate this. The moat is hardware know-how + sensor IP, not software.

### Finding 116: Quantum Sensing Market Is Commercially Real and Growing (2026-02-12)

**Source:** IDTechEx market report, McKinsey quantum sensing report, QuantumDiamonds (€152M), Bosch/Element Six partnership

Quantum sensing market: $860M (2026) → $1.56B by 2031 (CAGR ~12-15%). NDT market overall: $22-56B by 2035. Key segments: semiconductor inspection (KLA/ASML incumbent but blind to buried defects), battery quality control (fast-growing), medical diagnostics (MEG/MCG), GPS-denied navigation (defense — SandboxAQ AQNav, Q-CTRL 50x advantage with Lockheed Martin/Airbus). QuantumDiamonds: €152M German government investment for chip inspection facility. Bosch partnered with Element Six (De Beers) for diamond-based quantum sensors — cell-phone-sized prototype. Infleqtion: $100M Series C + $1.8B SPAC for quantum sensing in defense.

**Implication:** Unlike gate-based QC for ML (which has no demonstrated advantage), quantum sensing delivers REAL commercial value TODAY. The market is proven. The question for Superpose is team fit, not market validation.

### Finding 104: qbsolv & Multilevel Methods Trivialize Sub-Problems (2026-02-13)

**Source:** D-Wave CQM Solver Properties documentation + arXiv:2409.05542

CQM accepts continuous variables but restricts them to **linear interactions only** (`max_quadratic_variables_real = 0`). This means:
- `3.5 * x` (linear) = OK
- `x * y` (quadratic, x or y continuous) = FORBIDDEN
- `x^2` (self-quadratic, x continuous) = FORBIDDEN

The paper arXiv:2409.05542 (Nature Sci Rep 2025) explicitly states: "Continuous variables are usually run on classical computers, as here quantum annealers are not suspected to provide any computational advantage."

**Implication:** CQM does NOT bypass Barrier 2 (Continuous). It handles continuous variables classically. The quantum component only processes binary sub-problems. Marketing claims of "continuous variable support" are technically true but deeply misleading for ML use cases.

### Finding 2: D-Wave Hybrid Solvers Are ~98-99% Classical (2026-02-12)

**Source:** D-Wave timing API data, arXiv:2410.07980, Kerrisdale Capital QBTS report

The hybrid solver architecture runs tabu search + simulated annealing on AWS CPUs/GPUs. The QPU processes small binary sub-problems identified by the classical module. Timing data shows QPU access at ~1.4% of total compute time. Former D-Wave insiders quoted by Kerrisdale Capital (April 2025): "'hybrid' in practice means 'almost entirely classical'" and quantum component was "minimal -- often cosmetic."

**Implication:** The "up to 1M variables" claim means 1M variables processed primarily by classical heuristics with occasional quantum queries. This does NOT bypass Barrier 1 (Scale) via quantum means -- it bypasses it via classical computing.

### Finding 3: D-Wave Loses to Gurobi on Every ML-Relevant Problem Class (2026-02-12)

**Source:** arXiv:2409.05542 (Nature Sci Rep 2025)

| Problem Class | D-Wave vs Gurobi | ML Relevance |
|--------------|------------------|--------------|
| Linear Programming | No advantage | Medium (LP relaxations) |
| MILP (44K vars) | **4.6-4.8x worse** | **High** (scheduling, allocation) |
| Constrained BLP | Degrades dramatically | High (feasibility problems) |
| Binary Quadratic (500 vars, dense) | **~25% better** at CPLEX timeout | **Low** (niche binary problems) |

D-Wave's ONE sweet spot -- dense BQP at ~500 binary variables -- is the exact opposite of what ML needs (continuous, large-scale, constrained).

### Finding 4: D-Wave's Quantum Supremacy Claim Is for Physics, Not Optimization (2026-02-12)

**Source:** Science (March 2025), Quantum Insider deep dive, EPFL/Flatiron rebuttals

D-Wave's quantum supremacy claim was for simulating quantum dynamics of spin glasses (Transverse-Field Ising Model), NOT for solving optimization problems. Classical rebuttals from EPFL and Flatiron Institute demonstrated competitive results on subsets of the problems. This has zero relevance to ML optimization.

### Finding 5: Narrow Sweet Spot Exists -- Dense BQP at ~500 Binary Variables (2026-02-12)

**Source:** arXiv:2409.05542

D-Wave genuinely outperforms Gurobi/CPLEX on ONE problem class: dense binary quadratic programming with ~500 variables and no constraints. At high complexity, CPLEX/Gurobi timeout at 1000s while D-Wave finds ~25% better solutions. This maps to the Ising Hamiltonian naturally.

**Open question:** Are there ML sub-problems that are naturally dense BQP at ~500 variables? Candidates: binary hash code learning, BNN weight optimization, graph adjacency optimization. None tested yet.

### Finding 6: Sparsity Mask Optimization IS Naturally Binary and QUBO-Amenable (2026-02-12)

**Source:** arXiv:2411.17796 (iCBS, Amazon/AWS), arXiv:2505.16332 (A*STAR), QUBS (OpenReview 2024)

Multiple independent groups confirm: neural network pruning (keep/prune decision per weight/filter) is naturally a binary optimization problem that can be formulated as QUBO. The binary variable x_i in {0,1} indicates keep/prune. The quadratic objective Q_ij = w_i * H_ij * w_j captures pairwise weight interactions via the Hessian. This genuinely bypasses Barrier 2 (Continuous-to-Binary).

**Key evidence:**
- iCBS (arXiv:2411.17796): tested blocks of 1024-4096 binary variables, achieves +7-14% accuracy over Wanda at extreme sparsity
- arXiv:2505.16332: ran QUBO pruning on D-Wave Advantage for LeNet-5 (28-108 qubits). Larger models (ResNet-9: 2264 qubits, VGG-16: 4263 qubits) exceeded D-Wave capacity.
- iCBS authors explicitly call their formulation "quantum-amenable" and cite D-Wave's qbsolv as inspiration

**Implication:** This is the strongest Barrier 2 bypass found so far. Pruning is the ONE ML problem where binary encoding is not an approximation but the natural formulation.

### Finding 7: The Pruning Hessian Is Low-Rank, Making the QUBO Sparse (2026-02-12)

**Source:** WoodFisher (arXiv:2004.14340, NeurIPS 2020), CHITA (Google Research), M-FAC (arXiv:2107.03356)

The empirical Fisher Information Matrix used as Hessian proxy is F = (1/n) * sum_i(g_i * g_i^T) -- a sum of rank-one matrices. For calibration batch size m (typically 128), the Hessian has rank at most m. For a block of d=1024 weights, the 1024x1024 Hessian has only 128 non-zero eigenvalues. The resulting QUBO Q_ij inherits this low-rank structure, meaning it is effectively SPARSE, not dense.

**Why this matters:** D-Wave's genuine advantage is on DENSE BQP (Finding 5). A low-rank/sparse QUBO is efficiently solvable by classical methods (Iterative Hard Thresholding, greedy, local search). CHITA exploits this low-rank structure to achieve 20-1000x speedups over prior pruning methods. This directly undermines the hypothesis that D-Wave would have advantage on the pruning QUBO.

### Finding 8: D-Wave QPU Can Only Embed ~150 Fully Connected Variables (2026-02-12)

**Source:** D-Wave topology documentation, arXiv:2301.03009

Pegasus (Advantage): maximum clique K_150 with chain length 14. Zephyr (Advantage2): similar ~150, with degree 20 vs 15. This means a dense QUBO with 500 variables CANNOT be solved on the QPU directly -- it must use the hybrid solver, which is ~98% classical. The "dense BQP at ~500 vars" sweet spot from arXiv:2409.05542 was benchmarked on the HYBRID solver, not pure QPU.

**Implication:** Even if the pruning QUBO were dense, D-Wave cannot solve it quantumly at the target size. The hybrid solver's classical components (tabu search, SA) would do most of the work.

### Finding 9: Classical Pruning Baselines Are Extremely Fast and Near-Optimal (2026-02-12)

**Source:** arXiv:2301.00774 (SparseGPT), arXiv:2306.11695 (Wanda), arXiv:2512.13886 (OPTIMA)

SparseGPT prunes OPT-175B in <4.5 hours on a single GPU. Wanda achieves comparable quality in seconds (no Hessian needed). By contrast, iCBS (the quantum-amenable approach) takes **7.9 days** for Mistral-7B on 8xA10G GPUs. The bottleneck is NOT the combinatorial solver -- it is the Hessian computation per block.

**Implication:** Even if D-Wave solved each QUBO block infinitely fast, iCBS would still be orders of magnitude slower than SparseGPT/Wanda because the Hessian computation dominates. The solver step is not the bottleneck.

### Finding 10: npj QI 6561x Speedup Claim Uses Hybrid Solver (Mostly Classical) (2026-02-12)

**Source:** arXiv:2504.06201, npj Quantum Information 2025

The paper claiming 6561x quantum speedup on 10,000-variable dense QUBO used D-Wave's **Leap Hybrid sampler** — which we established (Finding 2) is ~98% classical. The paper describes using "QA hardware with more than 5,000 qubits, enhanced qubit connectivity, and hybrid architecture." The "quantum solver" is actually D-Wave's classical tabu search + SA running on AWS CPUs, with occasional QPU sub-routine calls.

**Implication:** This is NOT quantum advantage. It is a benchmark of D-Wave's classical optimization software vs. other classical solvers (Gurobi, CPLEX). The result says: D-Wave's proprietary classical heuristics are well-tuned for dense BQP. It does not demonstrate quantum speedup.

### Finding 11: Graph Clustering IS Naturally QUBO — Variable Counts Confirmed (2026-02-12)

**Source:** arXiv:2003.03872, PLOS ONE 10.1371/journal.pone.0227538, arXiv:2410.07744

For a graph with N nodes and K clusters: one-hot encoding uses N*K QUBO variables; recursive binary splitting uses N variables per level (log2(K) levels). QUBO coefficients (modularity matrix B_ij) computed directly from graph adjacency — NO model training, NO neural network evaluation. This genuinely bypasses Barrier 3 (Eval Bottleneck) and Barrier 2 (Continuous-to-Binary).

### Finding 12: D-Wave QPU Community Detection Reaches ~140 Nodes via Recursive Splitting (2026-02-12)

**Source:** arXiv:2410.07744 (Oct 2024)

Best QPU-native community detection approach found. Uses Advantage_system5.4 (Pegasus), recursive binary splitting, 20μs annealing, 100 reads. Tested on graphs 10-140 nodes. Matches or exceeds Louvain/Leiden modularity on 73-85% of instances. Brain connectome: Q=0.612 (QPU) vs Q=0.611 (Louvain). Throughput: 7,880 problems in 4.38 min vs hybrid DQM's 71 problems in 11.74 min. Limitation: sub-problems at each recursion level average ~18 nodes — trivially classical.

### Finding 13: K-Medoids Has N-Variable QUBO but Only Tested at n=12-16 (2026-02-12)

**Source:** Bauckhage et al. (2019) CEUR-WS Vol-2454, arXiv:2507.15063

Medoid-only QUBO: N binary variables, fully dense dissimilarity matrix. Fits D-Wave's sweet spot (dense BQP). But N=150 (QPU clique limit) is trivially solvable by PAM in microseconds. Only tested on n=12-16 data points. No D-Wave QPU benchmark at meaningful scale exists.

### Finding 14: Correlation Clustering Is N-Variable NP-Hard QUBO (2026-02-12)

**Source:** arXiv:2509.03561 (GCS-Q, Sep 2025)

Uses N binary variables on signed graphs. Tested on D-Wave Advantage up to 170 nodes. "Consistently obtains highest modularity values" vs k-means, PAM, spectral clustering on hyperspectral data. But uses recursive classical wrapper; quantum solves smaller sub-QUBOs. No wall-clock timing comparison vs pure classical methods provided.

### Finding 15: D-Wave QPU Is 10.5% Worse Than Optimal on Max-Cut at n=151 (2026-02-12)

**Source:** arXiv:2412.07460 (Dec 2024)

Benchmarked QPU, Hybrid, SA, SBM on 139 Max-Cut instances (100-10,000 nodes). QPU capacity: max n=151. At n=151, QPU achieved -24,231 vs optimal -27,089 = **10.5% gap**. Hybrid and SA consistently found global optimum. QPU exceeded capacity at n=251. For the canonical QUBO problem, D-Wave QPU is significantly worse than classical at its embedding limit.

### Finding 16: Classical Modularity Heuristics Are Optimal Only 19.4% of the Time (2026-02-12)

**Source:** Springer (Heuristic Modularity Maximization, 2023)

On 80 benchmark graphs, average heuristic found optimal partition only 19.4% of the time. Near-optimal partitions often structurally dissimilar to optimal. Suggests room for better optimization. However: Gurobi ILP solves exactly for 100+ nodes in ~4 min; D-Wave QPU only matches (not beats) these heuristics; downstream ML insensitive to small modularity differences.

### Finding 17: PRL Scaling Advantage Is for 2D Spin Glasses Only (2026-02-12)

**Source:** PRL 134, 160601 (Apr 2025)

D-Wave demonstrated scaling advantage over PT-ICM on 2D spin-glass problems with high-precision couplings. QAC surpassed PT-ICM at epsilon ~0.85. However: this is sparse 2D lattice topology, not dense graph clustering QUBOs. Does NOT transfer to the dense problems considered in this hypothesis.

### Finding 18: QCR-LLM Is Real — HUBO for LLM Reasoning Fragment Selection (2026-02-12)

**Source:** arXiv:2510.24509 (Kipu Quantum, Oct 2025), arXiv:2407.00071 (NASA Ames, July 2024)

Two independent groups confirmed: LLM reasoning fragment selection can be formulated as QUBO/HUBO. Binary variable x_i in {0,1} per reasoning fragment. Coefficients computed from co-occurrence statistics + sentence embeddings — NO model training required. NASA CR: average 900 QUBO variables, tested with SA on BigBench-Hard (+12.2pp over zero-shot). QCR-LLM: 35-90 binary variables with 3-body HUBO terms, tested with both SA and BF-DCQO on IBM 156-qubit Heron QPU on BBEH benchmarks.

**Implication:** This genuinely bypasses Barrier 2 (binary encoding is natural for include/exclude fragment decisions) and Barrier 3 (objective function IS the HUBO, computed from sample statistics, no model training needed). Variable count within Barrier 1 limits. First ML-adjacent approach that cleanly bypasses all three barriers.

### Finding 19: Classical SA Matches Quantum BF-DCQO on QCR-LLM Problems (2026-02-12)

**Source:** arXiv:2510.24509, Table 2

| Solver | Causal | DisambiguationQA | NYCC |
|--------|--------|------------------|------|
| SA | 58.5% | 60.0% | 24.5% |
| BF-DCQO | 59.5% | 60.0% | 25.0% |

Quantum advantage: +0.0 to +1.0pp — within noise. Authors acknowledge "classical annealing already approximates near-optimal solutions efficiently" at "moderate problem size" of 35-90 binary variables.

**Implication:** The CR framework itself is valuable (+4.5-8.3pp over base GPT-4o), but the quantum solver component provides no meaningful advantage at current reasoning problem sizes. Fails the >10% Advantage gate.

### Finding 20: BF-DCQO Shows 80x Runtime Advantage on Crafted 156-Qubit HUBO Instances (2026-02-12)

**Source:** arXiv:2505.08663 (Kipu Quantum/IBM, May 2025)

On IBM Marrakesh 156-qubit Heron: BF-DCQO achieved solutions in ~0.2s vs CPLEX ~17.5s (80x speedup). vs SA: 3.5x speedup, lower energy in 9/10 trials. Problem: 3-body HUBO with heavy-tailed (Cauchy/Pareto) distributions. Critical caveats: (a) "carefully selected problem instances," (b) excludes circuit compilation time, (c) requires heavy-tailed distributions for hardness.

**Implication:** If QCR-LLM HUBO instances scale to 150+ fragments with the right coefficient distribution, BF-DCQO runtime advantage could transfer. But coefficient distributions of real reasoning problems are unknown, and current problems are too small (35-90 vars) for quantum advantage.

### Finding 21: D-Wave Cannot Handle HUBO Natively — QUBO Reduction Explodes Variables (2026-02-12)

**Source:** D-Wave documentation, arXiv:2511.19613

D-Wave QPU only supports QUBO (quadratic terms). HUBO cubic terms require auxiliary variable reduction: one extra variable per cubic term. For QCR-LLM with 120 fragments and ~280K triplet terms, QUBO reduction would produce 120 + 280K = far too many variables for D-Wave. BF-DCQO on gate-based quantum computers (IBM) handles HUBO natively without reduction.

**Implication:** D-Wave is NOT the right hardware for this approach. The inference-time HUBO hypothesis points toward gate-based quantum computing (IBM, IonQ) rather than quantum annealing.

### Finding 22: QCR-LLM Does Not Compare Against Best Classical Baselines for Inference-Time Scaling (2026-02-12)

**Source:** arXiv:2510.24509 (missing baselines), arXiv:2408.03314 (ICLR 2025), arXiv:2504.16828 (ThinkPRM)

QCR-LLM only compares against base models (GPT-4o, o3-high, DeepSeek R1). It does NOT compare against: (a) self-consistency/majority voting with N=20 samples, (b) Best-of-N with process reward model, (c) MCTS-based reasoning, (d) compute-optimal tree search. These classical inference-time scaling methods achieve dramatic gains at similar compute budgets (Best-of-N with BiRM: 86.1% on MATH-500 at N=256). Without this comparison, QCR-LLM's value proposition over classical alternatives is unproven.

### Finding 23: NASA CR QUBO Co-Occurrence Matrix Is ~98% Dense (2026-02-12)

**Source:** arXiv:2510.24509 (QCR-LLM), arXiv:2407.00071 (NASA CR)

QCR-LLM reports ~7,000 pairwise interactions for 120 reasoning fragments. Since C(120,2) = 7,140, this is ~98% density. NASA CR computes connected correlation c_ij = n_ij/N - n_i*n_j/N^2 for all reason pairs using N=210 LLM samples. With 210 samples, most reason pairs co-occur at least occasionally, making the baseline term non-zero for nearly all pairs. The resulting QUBO matrix is dense or near-dense.

**Implication:** This is D-Wave's sweet spot per Finding 5 (dense BQP at ~500 vars). The NASA CR QUBO has the RIGHT structure for D-Wave. However, the full 900-variable QUBO cannot fit on the QPU (~150 max clique), so it must use the hybrid solver which is ~98% classical.

### Finding 24: D-Wave QPU Cannot Embed 900-Variable Dense QUBO (2026-02-12)

**Source:** D-Wave topology documentation, arXiv:2301.03009

Pegasus (Advantage): max fully-connected clique K_150, chain length 14. Zephyr (Advantage2): ~150 max clique, degree 20. A dense 900-variable QUBO is 6x beyond the QPU's fully-connected embedding capacity. The hybrid solver handles it via classical decomposition with occasional QPU sub-problem calls. There is NO roadmap for 900-variable dense clique embedding.

**Implication:** The "submit NASA CR QUBO to D-Wave" experiment would use the hybrid solver, which is ~98% classical. Any advantage over classical SA would come from D-Wave's proprietary classical heuristics, not quantum hardware.

### Finding 25: D-Wave Hybrid Solver Wall-Clock Time for 900-Var BQM ~15-18 Seconds (2026-02-12)

**Source:** D-Wave documentation (minimum_time_limit piecewise-linear interpolation), user benchmarks

The hybrid BQM solver minimum_time_limit interpolates linearly: example [[1, 0.1], [100, 10.0], [1000, 20.0]] gives ~18s for 900 variables. A 300-variable example shows ~3s charge_time. For inference-time reasoning, this adds 15-18s latency on top of the 20+ seconds for N=20 LLM samples. Classical SA on local machine would solve the same QUBO in <1 second.

### Finding 26: VeloxQ Classical Solver Matches D-Wave Hybrid Quality 1000x Faster (2026-02-12)

**Source:** arXiv:2501.19221 (VeloxQ, Jan 2025)

VeloxQ (quantum-inspired classical solver) achieves solution quality "very close" to D-Wave Kerberos hybrid solver but "up to almost three orders of magnitude" faster. For problems matching Pegasus topology, D-Wave QPU has "an order of magnitude shorter time-to-solution," but for general dense QUBOs processed by hybrid, VeloxQ dominates. Modern classical QUBO solvers have largely closed the gap with D-Wave's hybrid solver.

### Finding 27: D-Wave QPU Outperforms BF-DCQO (Gate-Based) on QUBO/Ising (2026-02-12)

**Source:** arXiv:2509.14358 (Farre et al., Sep 2025)

D-Wave Advantage2 QPU substantially outperforms Kipu Quantum's BF-DCQO on Ising/QUBO problems: 100x+ faster, better quality on 29-variable instances. Authors demonstrate BF-DCQO's quantum component contribution is "minimal." On 156-qubit hising: D-Wave 0.543s vs BF-DCQO >23.5s.

**Implication:** For reasoning QUBOs that fit on the QPU (~150 dense vars), D-Wave is the better quantum platform vs IBM/BF-DCQO. But at 150 vars, classical SA also matches quantum (Finding 19). The quantum advantage question requires problems in the 150-300 variable range where classical starts to struggle but QPU embedding still works.

### Finding 28: Fujitsu Digital Annealer Handles 900-Var Dense QUBO Without Partitioning (2026-02-12)

**Source:** arXiv:2507.22117

Fujitsu DAv3 has single-DAU capacity of 8,192 variables with no partitioning needed. For 900-variable dense QUBO: DAv3 handles it natively. In Max-Cut benchmarks, DAv3 outperforms D-Wave hybrid on medium-large instances. D-Wave hybrid leads on small instances (<1000 vars). Both are competitive alternatives to classical SA for the NASA CR problem size.

**Implication:** The NASA CR paper already tested with Fujitsu DA and found "1-2 orders of magnitude" speedup over basic SA. D-Wave hybrid would be similarly competitive. But neither represents quantum advantage -- both are classical or mostly-classical.

### Finding 29: Linear CR Outperforms Quadratic CR — QUBO Terms Hurt Accuracy (2026-02-12)

**Source:** arXiv:2407.00071 (NASA Ames, July 2024), Table 3

*(Findings 30-33 from engineering cycle 6 — Chevron/oil & gas operations QUBO — appear below.)*

Overall accuracy across 10 BigBench-Hard datasets:
- **Quadratic CR (QUBO): 65.2%**
- **Linear CR: 68.2%** (+3.0pp over QUBO)
- **Random selection: 57.4%**

The linear formulation (using only frequency-weighted reason selection without pairwise co-occurrence terms) OUTPERFORMS the quadratic QUBO formulation by 3 percentage points. The pairwise correlation terms c_ij = n_ij/N - n_i*n_j/N^2 that define the QUBO structure are noise, not signal — they hurt downstream accuracy compared to simpler linear selection.

**Why this is devastating for the D-Wave hypothesis:** D-Wave's value proposition is solving QUADRATIC binary optimization. If the quadratic terms in the reasoning QUBO actively HURT performance, there is no QUBO to solve — a linear selection (trivially solvable by sorting) is superior. This eliminates the need for ANY combinatorial solver (classical or quantum) on the reasoning fragment selection problem. The entire QUBO direction for inference-time reasoning may be a dead end.

**Caveats:** (a) The NASA paper used hyperparameter-tuned QUBO parameters (μ, α, β tuned on 135 questions via Optuna), so suboptimal tuning could explain the gap. (b) QCR-LLM (arXiv:2510.24509) used a different HUBO formulation with cubic terms and showed +4.5-8.3pp over base models — the HUBO may capture interactions that QUBO misses. (c) Linear CR may only work for simpler BBH tasks; harder reasoning tasks could require pairwise interaction modeling.

### Finding 30: Oil & Gas Well Placement Is Killed by Eval Bottleneck -- Same as ML Barrier 3 (2026-02-12)

**Source:** Computational Geosciences (2006), Stanford theses (Abukhamsin 2009, Guyaguler 2002)

Well placement optimization has 50-200 binary variables (candidate well locations) -- right in D-Wave's range. BUT each QUBO coefficient Q_ij requires a reservoir simulation to compute pairwise well interaction effects. For N=200 candidates, building the full QUBO matrix requires O(N^2) = 40,000 simulations, each taking minutes to hours. At 2 min/sim: 1,333 hours (~56 days) just to BUILD the QUBO. The solver step (seconds on any platform) is irrelevant. This is EXACTLY Barrier 3 (Eval Bottleneck) transplanted into oil & gas.

### Finding 31: Oil & Gas Operations Problems Are MILP, Not Dense BQP (2026-02-12)

**Source:** arXiv:2409.05542, CMU Gupta/Grossmann (field development MINLP), optimization-online.org (drilling MILP)

All oil & gas operations problems examined (drilling scheduling, vessel routing, CCUS network, refinery scheduling, asset portfolio) are MILP/MINLP: linear constraints, sparse structure, mixed binary + continuous variables. D-Wave is 4.6-4.8x worse than Gurobi on MILP (arXiv:2409.05542). D-Wave's sweet spot (dense BQP ~500 vars) does not match ANY oil & gas problem structure found.

### Finding 32: Chevron Has World-Class Classical Optimization ($10B from PETRO LP) (2026-02-12)

**Source:** INFORMS ORMS Today (2018), KBC/Yokogawa documentation

Chevron's PETRO LP system uses distributive recursion-based LP for refinery planning. Processes 400-500 crude characterization variables + thousands of refinery variables in seconds. ~$1B/year in value; ~$10B cumulative over 30 years. Central Modeling & Analytics COE, DRL for field development on Azure, nPlan AI for capital project forecasting.

### Finding 33: NO Oil & Gas Company Uses D-Wave (2026-02-12)

**Source:** D-Wave customer success stories, SPE JPT, WorldOil, EnergyConnects

No published case study documents any oil & gas company using D-Wave. All oil & gas quantum activity is gate-based: Aramco/Pasqal, ExxonMobil/IBM, bp/IBM Q Network, Chevron/OQC. Oil & gas quantum interest focuses on molecular simulation, not QUBO optimization.

### Finding 34: Chevron Invested in Gate-Based QC (OQC), Not Annealing (2026-02-12)

**Source:** WorldOil (2024/03/05), PRNewswire

CTV joined OQC's $100M Series B (March 2024). Gate-based superconducting QC (32-qubit Toshiko). Applications: catalyst development, molecular simulation, materials discovery. NOT combinatorial optimization. Chevron's quantum strategy points away from D-Wave/annealing.

### Finding 35: RAG Diverse Selection Is a Solved Problem in NLP (2024-2025 Literature Explosion) (2026-02-12)

**Source:** SMART-RAG (arXiv:2409.13992), DF-RAG (arXiv:2601.17212), SetR (arXiv:2507.06838, ACL 2025), VRSD (arXiv:2407.04573), InSQuaD (arXiv:2508.21003), Stochastic RAG (arXiv:2405.02816, SIGIR 2024), Context Bubble (arXiv:2601.10681)

At least 7 independent papers in 2024-2025 address diverse/optimal RAG chunk selection using DPP, submodular functions, MMR variants, LLM-guided selection, stochastic sampling, and structure-aware constrained selection. None use QUBO, quantum annealing, or binary optimization. All use greedy heuristics or probabilistic methods in polynomial time. The NLP community considers this solved.

### Finding 36: Quality Gap Between Optimal and Greedy RAG Selection Is 0.8-5.2% (2026-02-12)

**Source:** SMART-RAG Table 3 (arXiv:2409.13992), Stochastic RAG (arXiv:2405.02816)

SMART-RAG (DPP) vs top-k BGE: NQ +3.2%, TriviaQA +0.8%, HotpotQA +5.2%, FEVER +2.6%, FM2 +5.0%. Average +3.4%. Stochastic RAG (end-to-end differentiable): NQ +3.7%, TriviaQA +1.6%, HotpotQA +6.5%, FEVER +0.4%. All below the 10% advantage threshold. Even with optimal selection methods, the quality ceiling for context optimization is low.

### Finding 37: Diverse Retrieval Problem Is NP-Complete But Trivially Solved by Heuristics (2026-02-12)

**Source:** VRSD (arXiv:2407.04573)

Selecting k vectors from n candidates to maximize cosine similarity of their sum vector with the query is NP-complete (via reduction from k-subset sum). However, VRSD's greedy O(kn) heuristic beats MMR on >90% of instances. Practical RAG instances (50-500 candidates) are not hard instances for this problem class.

### Finding 38: DPP Kernel Construction Has Same O(n^2) Cost as QUBO Matrix (2026-02-12)

**Source:** SMART-RAG (arXiv:2409.13992), DPP literature

Both QUBO and DPP approaches require O(n^2) pairwise embedding comparisons for matrix construction. The ONLY difference is the solver: DPP greedy MAP inference O(nk^2) after kernel = <2ms for n=500, k=10. QUBO solver (SA) = 3-5s. D-Wave hybrid = 15-18s. QUBO solver is 1000-10000x SLOWER for the same quality.

### Finding 39: No Paper Uses QUBO for RAG Context Selection (2026-02-12)

**Source:** Exhaustive search across arXiv, SIGIR, ACL, EMNLP, NeurIPS 2024-2025

Despite natural binary formulation, zero published papers formulate RAG context selection as QUBO. The closest: feature selection for ranking (SIGIR 2022), instance selection for fine-tuning (ICTIR 2024), QuantumRAG (GitHub, simulated Grover not QUBO). The NLP community has not adopted QUBO because greedy/DPP/submodular work, the problem is too small, and latency requirements (<100ms) are incompatible with QUBO overhead.

### Finding 40: QuantumCLEF Feature/Instance Selection Shows No Quantum Advantage (2026-02-12)

**Source:** arXiv:2507.15063

QuantumCLEF 2024 tested QA for three IR tasks. Feature selection: QA ~10x faster than SA, but no quality advantage. Instance selection: trivial datasets (99.4% vs 99.5% F1). Clustering nDCG: 0.58-0.60 (classical GMM best). Authors note "datasets are simply too trivial." Problem sizes (80-variable batches) are trivially classical.

### Finding 41: Chevron's ApEX IS Real — Multi-Agent RAG Over 1M+ Files (2026-02-12)

**Source:** chevron.com/newsroom/2025/q4/a-smarter-way-to-prospect-for-oil-and-gas

Chevron's ApEX (launched Aug 2024) IS a real multi-agent RAG system for deepwater exploration. It uses "multiple search agents" (geospatial, exploration review team) to search 1M+ files and return insights. Query → agents → multi-source document retrieval → synthesized answer. This is a genuine enterprise RAG system at scale. However, it is built and maintained IN-HOUSE by Chevron's Enterprise AI team — confirming the GTM finding that Chevron builds rather than buys AI tools.

**Implication for QUBO hypothesis:** Even if RAG context selection as QUBO worked, Chevron would not be a customer — they build internally. The technical hypothesis (RAG as QUBO) is killed independently by three feasibility gates regardless.

### Finding 42: PDQUBO Shows QA Speed Advantage at 100 Vars But Fails at 500 (2026-02-12)

**Source:** arXiv:2410.15272 (PDQUBO for Recommender Systems)

PDQUBO tested QUBO for item selection in recommender systems. At 100 variables: QA = 0.496s vs SA = 13.65s (27x faster). At 500 variables: QA failed ("—"), hybrid = 16.49s vs SA = 391s. This confirms: (1) QA is genuinely fast at ~100 binary vars; (2) QA cannot handle 500 dense vars on QPU; (3) hybrid at 500 vars is ~24x faster than SA but is ~98% classical. For RAG context selection at 100-500 candidates, QA-fast-at-100 is irrelevant because greedy DPP already solves in <2ms.

### Finding 43: Seismic Surveys Contain 100K-100M+ Traces — 4+ Orders of Magnitude Beyond QPU (2026-02-12)

**Source:** SEG Wiki, CSEG Recorder, Netherlands F3 dataset (Zenodo:1471548)

3D seismic surveys collect "a few hundred thousand to a few hundred million traces." Modern marine surveys record >100K traces/km^2. The F3 benchmark has 651 x 951 = ~619K traces per horizon. Real production surveys are 10-100x larger. QUBO for graph clustering requires N*K variables (one-hot) or N variables per recursion level. At N=619K, K=10: 6.19M QUBO variables. D-Wave QPU max clique: ~150. Hybrid max: ~1M (98% classical). Scale gap is 3-4 orders of magnitude.

### Finding 44: Seismic Facies Uses SOM/K-Means/Deep Learning — Never Graph QUBO (2026-02-12)

**Source:** Chopra & Marfurt (GEOHORIZONS 2010), JGR:ML&C (Xu 2025), Geophysical Insights Paradise AI

The dominant methods for seismic facies classification: (1) Self-Organizing Maps (SOM) — industry standard since 1990, used in commercial tools; (2) K-means on attribute vectors; (3) Deep convolutional autoencoders + k-means (2024-2025 SOTA); (4) Spectral clustering on sparse k-NN graphs. Zero published papers formulate seismic facies as graph partitioning QUBO or modularity maximization. The geophysics community treats traces as feature vectors, not graph nodes.

### Finding 45: Seismic Similarity Graphs Are Sparse k-NN, NOT Dense Complete Graphs (2026-02-12)

**Source:** Springer (spectral clustering seismic, 2020), SEG (2022)

When graph methods ARE used for seismic data, the standard is sparse k-NN graphs (k=7-12). For N=619K traces with k=10: ~6.19M edges (sparse). A complete graph would have ~1.9 x 10^11 edges. Sparse k-NN is used explicitly to "solve the storage and calculation problems of high dimension similarity matrix." D-Wave's sweet spot is dense BQP. Sparse graphs are solved by Leiden in near-linear time.

### Finding 46: Leiden/Louvain Handles Millions of Nodes in Seconds on GPU (2026-02-12)

**Source:** NVIDIA Blog (cuGraph benchmark), arXiv:2312.13936 (GVE-Leiden)

cuGraph Leiden on GPU: 3.8M nodes, 16.5M edges in 3-4 seconds (NVIDIA A100). GVE-Leiden on multicore CPU: 403M edges/s. For seismic-scale graphs (619K nodes, 6.19M edges): expected <1 second. D-Wave QPU community detection: tested up to 140 nodes via recursive splitting. Sub-problems average ~18 nodes — trivially classical.

### Finding 47: All D-Wave Geoscience Work Is Seismic Inversion, NOT Clustering (2026-02-12)

**Source:** arXiv:2412.06611, arXiv:2502.03808, Frontiers in Physics (2021)

All published D-Wave geoscience applications are seismic inversion (linear system Ax=b -> QUBO). Problem sizes: 300 real variables -> 900 QUBO vars (decomposed 30 layers x 10 vars). QPU contributes 0.043-0.085 seconds of 4-9 second total (0.5-2% of runtime). Seismic inversion is fundamentally different from trace clustering. Not a clustering use case.

### Finding 48: Aramco/D-Wave Partnership Is Seismic Inversion, Not Clustering (2026-02-12)

**Source:** BusinessWire (June 2024), HPC Wire

D-Wave extended agreement with Aramco Europe for "computationally intensive seismic imaging." Created first subsurface maps from tens of GB of seismic data. Goal: 1 TB with Advantage2. This is seismic inversion (QUBO encoding of linear systems), not trace clustering or facies classification. No mention of graph clustering, community detection, or facies. Aramco also collaborating with NVIDIA (Oct 2025) on gate-based quantum emulation for fault detection.

### Finding 49: Ground-Motion Station Clustering (~1000 Nodes, Dense Graph) Exists But Is Academic (2026-02-12)

**Source:** ScienceDirect (Schiappapietra & Douglas, 2021), GJI Oxford (2021)

Earthquake seismology uses community detection on dense Pearson correlation matrices of ~1000 seismic stations (San Jacinto fault array). Communities reveal fault structures and geological zones. This IS structurally compatible with D-Wave (dense, ~1000 nodes). But: (a) academic seismology, not commercial oil & gas; (b) signed spectral clustering is the standard method; (c) no D-Wave application exists for this.

### Finding 50: Classical AI Dominates Seismic Interpretation — ADNOC ENERGYai and Deep Learning (2026-02-12)

**Source:** SLB/AIQ press releases (Aug 2025), SEG/EAGE 2024-2025

ADNOC ENERGYai: agentic AI with LLMs trained on 70 years of proprietary data, achieving 10x interpretation speed and 70% precision improvement. Deep learning CNNs achieve 97%+ supervised facies classification accuracy (UNet3+). The competitive frontier is AI model quality and data access, not optimization algorithm speed. The clustering/classification step is not the bottleneck in seismic interpretation.

### Finding 51: FMQA Is Real, Validated, and Actively Developed (2020-2026) (2026-02-12)

**Source:** Kitai et al. Phys. Rev. Research 2, 013319 (2020); arXiv:2507.18003 (review, July 2025); arXiv:2507.21024 (SWIFT-FMQA); arXiv:2501.04225 (kernel-QA)

FMQA was proposed by Kitai et al. (U. Tokyo / NIMS / Keio) in 2020. The FM's quadratic form maps *exactly* to QUBO: Q_ii = w_i, Q_ij = <v_i, v_j>. Iterates: train FM -> solve QUBO -> evaluate candidate -> repeat. Ecosystem includes tsudalab/fmqa (open-source), Amplify-BBOpt (Fixstars commercial), SWIFT-FMQA (sliding window), Extended FMA (Jij/Toyota). 15+ papers published.

### Finding 52: FMQA Problem Sizes Are Small — Mostly 20-120 Binary Variables (2026-02-12)

**Source:** arXiv:2507.18003, arXiv:2507.21024, arXiv:2602.10037

Largest FMQA on D-Wave QPU: 60 binary variables (metamaterial design, 2020). Largest on any solver: ~484 binary variables (analog circuit grid, Fujitsu DA). SWIFT-FMQA tested to N=101 using classical SA. Binary autoencoder paper: 14 variables on D-Wave Advantage 6.4. Nobody has tested FMQA at 200-500 binary variables with expensive evaluations.

### Finding 53: Kernel-QA Extension Scales to 640 Binary Variables, Outperforms Bayesian Optimization (2026-02-12)

**Source:** arXiv:2501.04225 (Fixstars, Jan 2025)

Kernel-QA replaces FM with polynomial kernel surrogate, solved on GPU-based Amplify AE (256K bits). At d=80 Rosenbrock (1000 cycles): kernel-QA=1.1, Bayesian opt=5.3, FMQA=13.4. At 640 binary (Rastrigin): kernel-QA=67.7 vs Bayesian=196.9. BO deviation 7.3x greater at cycle 50. **Uses classical GPU solver, not D-Wave.** Advantage comes from surrogate+QUBO framework, not quantum hardware.

### Finding 54: FMQA Requires 3-10x Fewer Function Evaluations Than GA/Random Search (2026-02-12)

**Source:** arXiv:2507.18003, arXiv:2507.21024, arXiv:2507.23160

Materials science: 7-18 queries per run vs 100-1000 for direct annealing. Extended FMA reached NSGA-II's 60-second score in ~10 seconds on transparent conductor design. For well placement with 200 candidates: FMQA needs ~500-2000 evaluations vs 40,000 for full QUBO construction (Finding 30). 25-80x reduction in simulation cost.

### Finding 55: No FMQA Paper Uses D-Wave for QUBO-Solving at Meaningful Scale (2026-02-12)

**Source:** All FMQA papers reviewed (15+ papers)

Every paper at 100+ binary variables uses classical SA (dimod) or GPU Ising solver (Amplify AE). D-Wave QPU used only at 14-60 variables -- trivially classical. FMQA community has de facto abandoned D-Wave in favor of Amplify AE (GPU, 256K vars). The quantum component is irrelevant to FMQA's demonstrated value.

### Finding 56: FM Surrogate Fidelity Degrades at High Dimensions Without Sufficient Data (2026-02-12)

**Source:** arXiv:2507.21024, Nature Sci Rep 2025 (higher-order FM), arXiv:2507.23160

2nd-order FM with sparse data: RMSE=1.16; 3rd-order worse (1.32) with sparse data, better with 500+ samples. SWIFT-FMQA: "improvement rate low" for large N. Extended FMA: "FM-based QUBO does not precisely represent the original problem." Performance degrades beyond 8-bit discretization. For well placement with 200 binary vars: FM needs hundreds of simulations to learn 19,900 pairwise terms adequately.

### Finding 57: FMQA for Well Placement Has Never Been Attempted (2026-02-12)

**Source:** Exhaustive search across arXiv, SPE, Wiley geomechanics

No paper applies FMQA to well placement, reservoir simulation, or any oil & gas subsurface problem. Xiao 2024 applied FMQA to DEM granular flow but with only ~20 binary variables. Extensive literature on GP/NN surrogates for well placement exists but none using FM + Ising machine. This is a genuine literature gap.

### Finding 58: Classical Combinatorial Bayesian Optimization Scales Poorly Beyond 60 Variables (2026-02-12)

**Source:** Bounce (NeurIPS 2023), BODi, CASMOPOLITAN, COMBO, SMAC benchmarks

BODi: "remarkable performance with up to 60 dimensions." SMAC: "initialisation did not work in dimensions larger than 40." COMBO scales poorly via graph Cartesian product. Bounce handles 1000 dims via nested embeddings but requires many evaluations. **FMQA's structural advantage:** FM training is O(NK), and acquisition function optimization via QUBO sidesteps the NP-hard acquisition optimization problem in BO. This advantage is from the QUBO formulation, not quantum hardware.

### Finding 59: Toyota/Jij Extended FMA Is the Closest to Commercial FMQA Deployment (2026-02-12)

**Source:** arXiv:2507.23160 (Jij Inc / Toyota Motor Corp), Fixstars Amplify

Extended FMA co-authored by Jij Inc. (Tokyo quantum software) and Toyota Motor Corporation. Toyota has deployed quantum annealing for manufacturing (parts storage, connector pin placement -- production since May 2025). Fixstars provides commercial Amplify-BBOpt with FMQA/kernel-QA. All deployments use classical Ising solvers (GPU-based), not D-Wave QPU.

### Finding 60: FM-Derived QUBOs Are DENSE but LOW-RANK (2026-02-12)

**Source:** FM theory (Rendle 2010), tsudalab/fmqa GitHub, arXiv:2507.18003, linear algebra (Gram matrix properties)

The FM interaction matrix Q_ij = <v_i, v_j> is the Gram matrix V*V^T where V is N x K. Critical properties: (1) DENSE -- when latent vectors are learned from data, Q_ij is almost surely nonzero for all i,j pairs (Wishart-type property). (2) LOW-RANK -- rank(V*V^T) = min(N,K). For typical K=8-16, N=200, rank = K << N. The eigenvalue spectrum has exactly K nonzero eigenvalues and N-K zero eigenvalues. (3) Classical eigenvalue-guided methods (arXiv:2106.10532) exploit this structure, finding better solutions on QUBO instances "with a few dominant eigenvalues." This distinction -- dense vs dense+low-rank -- was not previously identified. D-Wave's sweet spot (Finding 5) was benchmarked on full-rank dense BQP, not low-rank.

### Finding 61: Advantage2 QPU Can Embed ~177 Fully Connected Variables (2026-02-12)

**Source:** D-Wave Zephyr topology documentation, Zephyr Z(m) clique formula K_{16m+1}

Zephyr Z(m) admits complete graph K_{16m+1}. Advantage2 with ~4400 qubits corresponds to Z(11), giving max clique K_177. This is an improvement from Pegasus K_150 but only ~18% increase. For well placement at N=150: fits on QPU. At N=200: exceeds QPU by ~23 vars, must use hybrid (98% classical).

### Finding 62: Well Placement Problem Sizes Are 50-200 Binary Variables (2026-02-12)

**Source:** SPE literature, Springer Computational Geosciences (2023), Stanford well placement research, ScienceDirect (2021)

Binary well placement uses x_i in {0,1} at candidate locations. Typical sizes: 50-200 binary variables. Most studies use 100 candidates with GA or PSO optimization requiring 500-5000 reservoir simulations. Binary formulation is used when candidate locations are pre-selected (pad locations, lease boundaries).

### Finding 63: Classical ML Surrogates Achieve High Accuracy for Binary Well Placement (2026-02-12)

**Source:** ScienceDirect S0920410521008615 (2021)

MLP achieved best results among 6 ML surrogates for NPV prediction from binary well data. ~300 reservoir simulations sufficient for training. FMQA needs ~500-2000 evaluations for 200 vars (Finding 54). FMQA does NOT have an evaluation advantage over classical MLP surrogates. FMQA's unique value is producing QUBO directly from FM, enabling Ising machine optimization -- but this only helps if Ising solver outperforms classical optimization of MLP, which is unproven at 100-200 vars.

### Finding 64: No D-Wave Advantage2 QPU Benchmark on Dense BQP at 150-177 Variables Exists (2026-02-12)

**Source:** arXiv:2409.05542, arXiv:2412.07460, D-Wave Advantage2 whitepaper

The critical benchmark that would test the FMQA hypothesis does not exist. Available: (1) Hybrid ~25% better than CPLEX on dense BQP 500 vars (but hybrid is 98% classical, and problems were full-rank). (2) QPU 10.5% worse at n=151 Max-Cut on Advantage (not Advantage2). (3) Advantage2 whitepaper shows 2-7x better than Advantage on various problems, but no dense BQP data.

### Finding 65: Low-Rank QUBO Problems Are Likely Easier for Classical Solvers (2026-02-12)

**Source:** arXiv:2106.10532 (QUBO eigenvalue decomposition), Cela & Punnen 2022 (Springer)

Eigenvalue-guided QUBO search extracts top-K eigenvalues/eigenvectors and restricts search to dominant directions. "Improvement in solution quality for instances with few dominant eigenvalues." For rank-K QUBO (K=8-16), the effective search space is governed by K directions rather than N variables. This creates the "Advantage Paradox" for FM QUBOs: small K = easy QUBO (no quantum advantage); large K = hard QUBO but FM fidelity degrades. Caveat: diagonal terms Q = diag(w) + V*V^T add full-rank component; impact on hardness is an open empirical question.

### Finding 66: Quantum Kernels Show No Systematic Advantage Over Classical (20K Models, 64 Datasets) (2026-02-12)

**Source:** arXiv:2409.04406 (Quantum Machine Intelligence 2025)

Largest quantum kernel benchmarking: 20,000+ models, 64 datasets, 5 families. FQK and PQK vs classical SVC. NO clear quantum advantage. Circuits WITHOUT entanglement match or beat entangled circuits. Hyperparameter tuning matters more than quantum design choices. "Driving forces other than quantumness might be fostering the performance of QKMs."

### Finding 67: Exponential Concentration Makes Quantum Kernels Trivial at Scale (2026-02-12)

**Source:** Nature Communications (2024), arXiv:2208.11060

Quantum kernel values concentrate exponentially toward fixed value as qubit count increases. Kernel matrix -> identity matrix. Predictions become independent of input. The "curse of dimensionality" for quantum feature spaces. Mitigation: projected kernels, BFT, scarred Hamiltonians -- all unvalidated at scale.

### Finding 68: Barren Plateau / Classical Simulability Duality Kills Variational Quantum ML (2026-02-12)

**Source:** Cerezo et al., Nature Communications (2025), arXiv:2312.09121

If variational quantum model is trainable -> classically simulable -> no quantum advantage. If NOT classically simulable -> barren plateaus -> not trainable. No known regime is simultaneously trainable AND not classically simulable. Applies to VQE for ML, QAOA for ML, QNN, variational classifiers. Does NOT apply to quantum chemistry (Hamiltonian simulation).

### Finding 69: QAOA Is 2-3x Worse Than Classical NSGA-II on Building Energy Optimization (2026-02-12)

**Source:** Energy and Buildings (2025), 15,000 simulations benchmark

NSGA-II: 17.84-19.84 kWh/m2/year. QAOA: 31.85-55.62 kWh/m2/year. QAOA 60-180% worse in solution quality. QAOA faster (0.54 vs 18.9 min) but speed meaningless with 2-3x quality gap.

### Finding 70: Quantum Reservoir Computing Matches But Never Beats Classical LSTM (2026-02-12)

**Source:** arXiv:2412.13878 (QCHALLenge, Dec 2024)

5 quantum models vs 3 classical on time series. "Best configurations of classical models had higher average accuracy than best quantum models." QRC best case: "similar to LSTM" on Apple stock. All quantum models tested in noiseless simulation (best case).

### Finding 71: Quantum Chemistry for Catalysis Is Real But Requires Fault-Tolerant QC (2029+) (2026-02-12)

**Source:** J. Chem. Inf. Model (2024), arXiv:2506.19337, Microsoft/Quantinuum (Sep 2024)

VQE for Ni-CO2 hydrogenation: activation energy 8.6 kcal/mol vs DFT 14.2 vs experiment 9.0. FeMoco: 152+ logical qubits. Chevron-relevant: HDS catalysts (Mo/Ni/Co sulfides), Fischer-Tropsch (Fe/Co), CO2 conversion. Currently: 12 logical qubits (Quantinuum). 25-100 logical qubits by 2028-2029 for useful catalysis. The ONE surviving gate-based direction.

### Finding 72: Chevron's OQC Investment Is for Catalyst Design, Not Optimization or ML (2026-02-12)

**Source:** PRNewswire (March 2024), WorldOil

CTV joined OQC $100M Series B for: catalyst development, molecular simulation, materials discovery. NOT optimization, ML, or QUBO. OQC roadmap: 32-qubit Toshiko (now) -> Genesis 2026 -> ~200 logical qubits 2028 -> 50,000 logical 2034.

### Finding 73: Dequantization Has Killed Most Quantum ML Speedups (2026-02-12)

**Source:** Tang (2018), Phys. Rev. Research 6, 023218 (2024), arXiv:2406.07072, arXiv:2503.23931

Dequantized: recommendation, PCA, supervised clustering, regression, low-rank linear systems, variational QML via Random Fourier Features. NOT dequantized: Hamiltonian simulation (chemistry), IQP sampling (but concentration kills utility), sparse linear systems under restricted access (arXiv:2411.02087). All surviving advantages are for quantum systems, not classical data.

### Finding 74: Energy Sector QC Is All Gate-Based, All Pilot Stage, Zero Production (2026-02-12)

**Source:** Multiple industry sources (2024-2026)

ExxonMobil/IBM (since 2019): pilot. bp/IBM: pilot. Aramco/Pasqal (200 qubits deployed 2025): zero published results. Chevron/OQC: investment only, no research published. Shell: exploratory. Despite 5+ years of partnerships, ZERO production quantum deployments in energy.

### Finding 75: Fault-Tolerant QC Timeline Is 2029-2030 for Useful Chemistry (2026-02-12)

**Source:** IBM, Google, IonQ, Quantinuum roadmaps

IBM Starling 2029: ~200 logical qubits. IonQ 2030: 80K logical. Quantinuum Apollo 2030: universal fault-tolerant. Google Willow 2024: below error-correction threshold. 2028-2029: first scientifically meaningful catalyst results. 2029-2030: industrially relevant (FeMoco class).

### Finding 76: 22 QML Energy Use Cases Reviewed, NONE Show Quantum Advantage (2026-02-12)

**Source:** Frontiers in Quantum Science and Technology (2025)

Systematic review of 22 QML applications in energy (QSVM, VQC, QML fault detection, etc.). "Feasibility and technological maturity still in early stages." "Commercially available quantum workloads remain open challenge." NONE demonstrated quantum advantage.

### Finding 77: Quantum Kernel for Autonomous Materials Science -- Conditional, Limited Advantage (2026-02-12)

**Source:** arXiv:2601.11775 (Jan 2026), IonQ Aria

25 qubits, Fe-Ga-Pd XRD patterns, 20 data points. Quantum kernel outperforms RBF in narrow range (~10-15 training samples). BUT cosine similarity (simpler classical) beats both. Geometric difference 10.7-10.9. Advantage is conditional and does not survive comparison against best classical kernel.

### Finding 78: Microsoft/Quantinuum First End-to-End Quantum Chemistry Workflow (Sep 2024) (2026-02-12)

**Source:** Microsoft Azure Quantum Blog (Sep 2024)

12 logical qubits on Quantinuum H2. 2 logical qubits used for ground state of catalytic intermediate. 22x error rate improvement. 97% probability of better estimate from logical vs physical qubits. First HPC + quantum + AI chemistry workflow. But 2 logical qubits = trivially small for real applications.

### Finding 79: PhaseCraft THRIFT Algorithm Cuts Simulation Cost 10x (2026-02-12)

**Source:** Nature Communications (March 2025)

Li2CuO2: 410K gates vs 1.5 trillion previously (3.6M x reduction). 10x larger/longer simulations on same hardware. XPRIZE finalist. Materials Modeling Quantum Complexity Database for 40+ materials. PhaseCraft is the competitor Superpose would face in quantum chemistry.

### Finding 80: Quantum Startups Sell Hardware Access, Not ML Products (2026-02-12)

**Source:** Multiple investor reports (2025-2026)

IonQ ($24.5B), Quantinuum ($10B), PsiQuantum ($7B), Rigetti ($13B), IQM ($1B+), QuEra ($1B+): NONE sell ML products. Revenue from hardware access, cloud QPU, consulting, grants. Zapata (only quantum ML company) went bankrupt Oct 2024. QC Ware pivoted to quantum chemistry (Promethium). Market has spoken: quantum ML software cannot generate revenue.

### Finding 81: Aramco/Pasqal 200-Qubit System -- Zero Published Results (2026-02-12)

**Source:** Aramco press releases (2025), Pasqal roadmap

200-qubit neutral atom system deployed at Dhahran Q3 2025. Zero benchmarks, zero papers. Pasqal's quantum advantage demonstration: "first part of 2026" (aspirational). Pattern: energy companies invest as hedge, produce no scientific results.

### Finding 82: All Dequantization-Resistant Advantages Are for Quantum Systems, Not Classical Data (2026-02-12)

**Source:** arXiv:2411.02087, arXiv:2505.04705, arXiv:2308.07152

Surviving advantages: (1) Hamiltonian simulation (BQP-complete, inherently quantum -- chemistry); (2) IQP sampling (but concentration kills ML utility); (3) Sparse linear systems under restricted access. For classical data (sensor, financial, text, images): no dequantization-resistant quantum ML algorithm exists.

### Finding 83: Quantum Kernel "Structured Scientific Data" Thesis Has Three Interacting Problems (2026-02-12)

**Source:** Cross-reference Findings 66, 67, 73, 77

Three problems interact: (1) exponential concentration at scale, (2) dequantization if classically estimable, (3) no demonstrated advantage on benchmarks. Narrow theoretical window exists where data structure matches quantum feature map, kernel doesn't concentrate, AND can't be classically computed. Fe-Ga-Pd result hits (1) but fails (3). Completely unvalidated.

### Finding 84: Superpose's $100M+ Path Does Not Exist in Gate-Based Quantum ML (2026-02-12)

**Source:** Market analysis, competitor landscape

No quantum ML product exists commercially. Zapata went bankrupt. 22 energy QML use cases show zero advantage. Barren plateau/simulability kills theory. Quantum chemistry possible but: 2029+ timeline, competes with PhaseCraft/Microsoft/Quantinuum, requires completely different expertise (chemistry, not ML). Not a pivot; a restart.

### Finding 85: VQE for Reservoir Simulation Does Not Exist in the Literature (2026-02-12)

**Source:** Exhaustive search (arXiv, SPE, Elsevier, Nature)

Zero papers apply VQE or QAOA to reservoir simulation. Reservoir sim is PDE (Darcy flow, multiphase transport), not eigenvalue problem. HHL for linear systems requires fault-tolerant QC. No oil company has published on quantum PDE solving for reservoir models.

### Finding 86: Every Revenue-Generating "Quantum" Company Follows Classical-First Strategy (2026-02-12)

**Source:** Multiverse Computing ($215M raise, Bloomberg EUR 100M ARR report), SandboxAQ (company website, VentureBeat), Q-CTRL (2025 year-in-review blog), Classiq ($110M Series C), Strangeworks (Quantagonia acquisition)

Every quantum company with meaningful revenue sells classical products with quantum branding: Multiverse (tensor network AI compression on GPUs, EUR 100M ARR), SandboxAQ (PQC security + physics-AI on classical hardware, $5.75B valuation), Q-CTRL (quantum sensing + QPU optimization software, $50M+ contracts), Classiq (quantum circuit design tools, tripled YoY), Strangeworks (classical solver orchestration + quantum middleware, ~$3.7M est.). None sell quantum-compute-enhanced products today.

**Implication:** The "classical-first, quantum-later" strategy is the ONLY strategy that works. But every successful practitioner has $50M-$950M in funding and 5-7 year head starts.

### Finding 87: QAOA Optimization Advantage Needs 73.91M Physical Qubits -- Beyond All Roadmaps (2026-02-12)

**Source:** arXiv:2504.01897 (2025)

QAOA + Amplitude Amplification achieves crossover with state-of-the-art classical heuristics at 179 variables, requiring: QAOA depth p=623, 73.91 million physical qubits, 10^-3 physical error rate, 1 microsecond code cycle time, 14.99 hours runtime. Under optimistic assumptions: 8.88 million physical qubits. IBM Starling (2029) targets ~200 logical qubits (tens of thousands of physical qubits). IBM Blue Jay (2033+) targets 2,000 logical qubits. Both are 3-5 orders of magnitude short.

**Implication:** Quantum optimization advantage is not on any published hardware roadmap. The "classical now, quantum optimization later" thesis has no destination.

### Finding 88: IBM Starling (2029) Enables ONLY Chemistry, NOT Optimization/ML/Finance (2026-02-12)

**Source:** IBM quantum roadmap (Jun 2025 announcement), Goldman Sachs QAE threshold paper (Quantum 2021)

IBM Starling (2029): 200 logical qubits, 100M quantum gates. This enables: small-molecule quantum chemistry (FeMoco needs 152+ logical qubits), materials property prediction. This does NOT enable: optimization (needs millions of logical qubits per Finding 87), Monte Carlo finance (needs 4,700-8,000 logical qubits per Goldman Sachs), QML (barren plateau/simulability kills per Finding 68). Quantum finance reaches practicality only at 4,700+ logical qubits -- not on any roadmap before 2032-2035.

**Implication:** If Superpose's quantum transition plan depends on optimization, ML, or finance, IBM Starling does not help. The only viable 2029-2030 quantum product is chemistry/materials simulation.

### Finding 89: VCs Are Bearish on Pre-Seed Quantum Software (2026-02-12)

**Source:** DCVC quantum investment thesis (Quantum Insider, Dec 2025), quantum funding data (SpinQ 2025)

DCVC (major VC) explicitly states: quantum software plays "lack near-term defensibility compared to hardware and infrastructure investments." The firm prefers companies transitioning from research to "manufacturable, utility-scale systems." Series B+ rounds now represent 63% of all quantum investment, reflecting concentration of capital in later-stage companies. Average seed round has grown from $2M to $10M, but this is for hardware/sensing startups, not software.

**Implication:** A pre-seed quantum software pitch will face VC headwinds. Superpose should pitch as a classical AI company with quantum as upside option, not core thesis.

### Finding 90: Zapata's Bankruptcy Shows Financial Structure Kills Quantum Startups Before Technology Does (2026-02-12)

**Source:** Zapata SEC filings, Substack analysis (waxedmandrill), HPCwire, Quantum Insider

Zapata Computing ($67M raised, Harvard spinout, only public quantum ML company) had genuine commercial traction (defense contracts, rising revenue/margins) but collapsed from: (1) $4.8M debt crisis triggered by stock price put option, (2) SPAC structure causing massive dilution and volatility, (3) lock-up expirations enabling institutional selling. "Had Zapata held on for another month or two, it very likely would have been able to greatly extend its runway." Zapata re-emerged as Zapata Quantum in Sep 2025 with $3M bridge financing.

**Implication:** Quantum companies face existential risk from capital structure, not just technology risk. Pre-seed founders must plan for 5-7 year timelines before quantum revenue, requiring careful financial engineering.

### Finding 91: No Pre-Seed Quantum Startup Has Successfully Gone Classical-First (2026-02-12)

**Source:** Comprehensive search of quantum startup funding histories (Crunchbase, PitchBook, Tracxn, Quantum Insider)

All successful "classical-first, quantum-later" companies either: (a) spun out of larger institutions (SandboxAQ from Alphabet, Quantinuum from Honeywell), (b) were founded by world-class quantum physicists with research credentials (Multiverse by Roman Orus, Q-CTRL by Michael Biercuk), or (c) raised $10M+ initial funding. No documented case of a $3M pre-seed startup successfully building a classical product, then transitioning to quantum-enhanced.

**Implication:** This strategy is unproven at pre-seed scale. While the strategy is sound in principle, execution risk is extreme with $3M funding.

### Finding 92: AI-for-Chemistry Market Has 8+ Competitors at >$100M -- Extreme Saturation (2026-02-12)

**Source:** CuspAI (Fortune Sep 2025), Orbital Materials (SalesTools Sep 2025), Schrödinger (SDGR Q3 2025), SandboxAQ, Periodic Labs (TechCrunch Sep 2025)

The classical ML-for-chemistry/materials space has become one of the most heavily funded AI verticals: CuspAI ($130M, $520M valuation), Orbital Materials ($200M, $1.2B valuation), Periodic Labs ($300M seed, GNoME creator), Schrödinger ($163M+ annualized software, all top-20 pharma), SandboxAQ ($950M+, $5.75B valuation, LQMs), Microsoft Azure Quantum Elements (unlimited budget), Google DeepMind (GNoME/MatterGen), Isomorphic Labs ($600M). A $3M pre-seed entrant faces >40x funding disadvantage.

**Implication:** Competition gate FAILS. Market saturated at platform level. Only extreme vertical niches remain.

### Finding 93: Microsoft Demonstrated the Exact Classical-ML-Quantum Chemistry Workflow (Sep 2024) (2026-02-12)

**Source:** Azure Quantum Blog, Sep 10 2024

Hybrid workflow: (1) Classical HPC identifies active space; (2) Quantum computer prepares ground state; (3) Classical shadows generates ML training data; (4) AI model predicts molecular properties. Same data pipeline works whether reference calculations are DFT (classical) or QPE (quantum). Transition pathway is proven.

**Implication:** Quantum transition is technically demonstrated. But every competitor can make the same transition -- "quantum-ready" is zero differentiation.

### Finding 94: Delta-ML Achieves CCSD(T) Accuracy from DFT with 200 Training Points (2026-02-12)

**Source:** ACS J. Chem. Theory Comput. doi:10.1021/acs.jctc.4c00977, AIP J. Chem. Phys. 154, 051102 (2021)

Delta-ML corrects DFT to CCSD(T) accuracy with as few as 200 high-level data points. When quantum computers arrive, same framework corrects DFT to quantum accuracy. But also means classical delta-ML may reduce the need for quantum for many molecules.

### Finding 95: QC Ware Promethium Has $3.8M ARR After $39M in Funding (2026-02-12)

**Source:** Tracxn (Jul 2025)

Promethium: $3.8M ARR, $39M total funding, launched 2023. Usage-based pricing: $18-$100/compute-hour. 5 of top-20 pharma. Revenue-to-funding ratio ~10:1 shows difficulty of building revenue in computational chemistry SaaS.

### Finding 96: Schrödinger Has 100% Retention at $500K+ ACV, 8 Customers at $5M+ (2026-02-12)

**Source:** Schrödinger Q3 2025 earnings, IR press release

Deep enterprise moat: 100% retention >$500K ACV, 8 customers >$5M ACV (doubled from 4), all top-20 pharma. Switching costs built on workflow integration, team expertise, proprietary force fields.

### Finding 97: Materials Discovery May Be Entering Trough of Disillusionment (2026-02-12)

**Source:** MIT Technology Review (Dec 2025), Nature (2025)

MIT Tech Review: "no convincing big win" despite hype. GNoME's "discoveries" criticized as trivial variations. Reproducibility problems in AI materials labs. Field "waiting for its ChatGPT moment."

### Finding 98: PhaseTree Raised $3.24M Pre-Seed for Materials Discovery (Mar 2025) (2026-02-12)

**Source:** Fundraise Insider pre-seed database

Closest comparable: $3.24M pre-seed for materials discovery. No public data on product/traction. Proves funding thesis is achievable at this scale.

### Finding 99: IBM Starling (2029) and Quantinuum Apollo (2029) Both Target Chemistry First (2026-02-12)

**Source:** IBM Quantum Blog (2025), Quantinuum press release (2025)

Both companies target 200+ logical qubits by 2029 with chemistry as first application. Blue Jay (2033+): 2000+ logical qubits for complex molecules. Skeptics note roadmaps historically slip; total quantum revenue was "tens of millions" in 2024.

### Finding 100: Promethium (QC Ware) Charges $18-$100/Compute-Hour, ~$3.8M ARR After $39M Funding (2026-02-12)

**Source:** Promethium pricing page, QC Ware investor reports, web search

Promethium offers quantum chemistry SaaS at $18/hour (standard) to $100/hour (premium). Estimated ~$3.8M ARR. $39M total funding over 10 years. ~40% revenue growth. Unit economics: pharma customers pay $500K+ ACV but sales cycle is 6-18 months. Shows the path works but capital efficiency is low.

### Finding 101: Pharma Sales Cycle Is 6-18 Months — Challenging for $3M Runway (2026-02-12)

**Source:** Schrödinger 10-K, QSimulate investor materials, pharma procurement analysis

Enterprise pharma sales require validation studies (3-6 months), procurement review (2-4 months), and pilot deployment (3-6 months). Schrödinger's 100% retention at $500K+ ACV shows sticky customers once landed, but first deals take 6-18 months. With $3M pre-seed and ~18 month runway, a startup gets at most 1-2 enterprise deals before needing to raise again. Materials companies have shorter cycles (2-6 months) but lower ACV ($50-200K).

---

## 4. Ideas Graveyard

*Ideas killed with evidence. Record why so we don't revisit.*

| Idea | Killed Because | Evidence | Date |
|------|---------------|----------|------|
| LeapHybridCQM bypasses Scale+Continuous barriers for ML | (1) Continuous vars limited to linear interactions only (zero quadratic); (2) Hybrid is ~98.6% classical; (3) Gurobi beats it 4.6-4.8x on MILP. All 4 kill conditions triggered. | `raw/2026-02-12-eng-hybrid-cqm-claude.md`, arXiv:2409.05542, D-Wave CQM docs, Kerrisdale QBTS report | 2026-02-12 |
| npj QI 6561x speedup = quantum advantage for optimization | Used D-Wave Leap Hybrid sampler (~98% classical). "Quantum speedup" is actually classical tabu search + SA vs other classical solvers. NOT quantum advantage. | arXiv:2504.06201, cross-ref with Finding 2 | 2026-02-12 |
| Chevron oil & gas operations QUBO on D-Wave (PIVOT) | (1) Well placement killed by eval bottleneck (reservoir sim per Q_ij); (2) Scheduling/routing/CCUS are MILP, not dense BQP -- Gurobi wins 4.6x; (3) Chevron has ~$10B PETRO LP + DRL; (4) Chevron invested in OQC (gate-based), not D-Wave; (5) Zero oil & gas companies use D-Wave. 8/8 problem types KILLED. | `raw/2026-02-12-eng-chevron-qubo-ops-claude.md`, arXiv:2409.05542, INFORMS 2018, WorldOil 2024 | 2026-02-12 |
| RAG context optimization as QUBO for D-Wave (Chevron enterprise RAG) | (1) Quality gap between optimal DPP and greedy top-k is 0.8-5.2% -- below 10% threshold; (2) Classical greedy DPP runs in <2ms vs D-Wave hybrid 15-18s (1000-10000x slower); (3) 7+ NLP papers (2024-2025) solved this without QUBO; (4) VRSD proved NP-complete but O(kn) heuristic beats MMR 90%+; (5) Finding 29 pattern: pairwise QUBO terms may hurt quality (Linear CR > Quadratic CR). Three kill gates failed independently (Scale, Advantage, Latency). | `raw/2026-02-12-eng-chevron-rag-qubo-claude.md`, arXiv:2409.13992, arXiv:2407.04573, arXiv:2405.02816, arXiv:2507.06838 | 2026-02-12 |
| Chevron seismic QUBO graph clustering for geological zonation | (1) Scale: F3 = 619K traces per horizon, real = 10M+. QUBO needs N*K = millions of vars. QPU max ~150 fully-connected. (2) Graph mismatch: seismic similarity graphs are sparse k-NN, not dense complete. Leiden handles 3.8M nodes in 3s on GPU. D-Wave's sweet spot (dense BQP) is the opposite. (3) No paper formulates seismic facies as graph QUBO. Industry uses SOM/k-means/autoencoders. (4) Deep learning achieves 97%+ facies accuracy. ADNOC ENERGYai: 10x speed, 70% precision with classical AI. (5) D-Wave's own geoscience work is seismic inversion, not clustering. Three independent kill gates (Scale, Advantage, Problem Mismatch). | `raw/2026-02-12-eng-chevron-seismic-qubo-claude.md`, SEG Wiki, arXiv:2312.13936, arXiv:2410.07744, arXiv:2412.06611, arXiv:2502.03808 | 2026-02-12 |
| Quantum kernels for molecular/materials data (gate-based) | (1) 20K models, 64 datasets: no systematic advantage over classical kernels (arXiv:2409.04406); (2) Exponential concentration makes kernels trivial at scale (Nature Comms 2024); (3) Circuits without entanglement match/beat entangled circuits; (4) Fe-Ga-Pd result loses to cosine similarity; (5) Barren plateau/simulability duality (Cerezo, Nature Comms 2025). Multiple independent kill gates. | `raw/2026-02-12-eng-gate-based-qml-energy-claude.md`, arXiv:2409.04406, arXiv:2208.11060, arXiv:2312.09121 | 2026-02-12 |
| VQE/QAOA for reservoir simulation sub-problems | (1) VQE for reservoir simulation does NOT exist in literature; (2) Reservoir sim is PDE, not eigenvalue problem; (3) QAOA is 2-3x WORSE than NSGA-II on energy optimization (15K simulations). Problem structure mismatch. | `raw/2026-02-12-eng-gate-based-qml-energy-claude.md`, Energy and Buildings 2025, exhaustive arXiv/SPE search | 2026-02-12 |
| Quantum neural networks / variational QML for energy data | (1) Trainable -> classically simulable (Cerezo et al., Nature Comms 2025); (2) 22 QML energy use cases: NONE show advantage (Frontiers QST 2025); (3) QRC matches but never beats LSTM (arXiv:2412.13878); (4) All quantum ML speedups on classical data dequantized. Theoretical + empirical dead end. | `raw/2026-02-12-eng-gate-based-qml-energy-claude.md`, arXiv:2312.09121, Frontiers QST 2025, arXiv:2412.13878 | 2026-02-12 |
| Quantum ML software as startup product | Only quantum ML company (Zapata) went bankrupt Oct 2024. NONE of 6 quantum unicorns sell ML products. QC Ware pivoted to chemistry. Market has spoken. | Multiple investor reports, Zapata SEC filings | 2026-02-12 |
| "Classical-first, quantum-later" optimization platform at pre-seed (P1) | QAOA needs 73.91M physical qubits for 179 vars (arXiv:2504.01897). Quantum never helps optimization on any published roadmap. Strangeworks already acquired Quantagonia for this exact play. Classical market mature (Gurobi 15+ years). | `raw/2026-02-12-eng-gate-qc-unicorn-path-claude.md` | 2026-02-12 |
| Quantum chemistry SaaS at pre-seed (P2) | Right strategy, wrong team/funding. Needs PhD quantum chemists + pharma domain. QC Ware ($42M, 10yr), QSimulate ($11M, 7yr), Algorithmiq ($38.8M) ahead. $3M insufficient. | (same) | 2026-02-12 |
| LLM compression via tensor networks at pre-seed (P3) | Multiverse: EUR 100M ARR, $250M+, 160 patents, 100+ customers, 7yr head start. Fatal competition. | (same) | 2026-02-12 |
| PQC migration at pre-seed (P4) | Real market ($1.15B) but wrong company. Needs cybersecurity expertise. SandboxAQ ($950M), PQShield ($65M), QuSecure ($28M). | (same) | 2026-02-12 |
| Quantum Monte Carlo for finance at pre-seed (P5) | Needs 4,700-8,000 logical qubits. IBM Starling (2029) = 200. Timeline 2032-2035+. Banks do in-house. | (same) | 2026-02-12 |
| Quantum readiness consulting as unicorn path (P6) | Consulting doesn't scale to $100M+. Dominated by IBM, Protiviti, BCG, McKinsey, Deloitte. Not a technology company. | (same) | 2026-02-12 |
| QC Infrastructure Software at $3M pre-seed (P9) | 5+ well-funded competitors (Classiq $173M, Q-CTRL $50M+, Riverlane $75M, Strangeworks). Open-source commoditization (Qiskit, Cirq, PennyLane free). $3M cannot compete. Competition gate fails catastrophically. | `raw/2026-02-12-eng-gate-qc-preseed-unicorn-gemini.md`, Engine 3 searches | 2026-02-12 |
| Narrow quantum chemistry at $3M pre-seed (P11) | Same as P2/P8. Requires PhD quantum chemists. QC Ware ($42M), QSimulate ($11M), Algorithmiq ($38.8M), CuspAI ($130M), Orbital ($200M) ahead. Pharma sales 6-18 months vs $3M runway. | `raw/2026-02-12-eng-gate-qc-preseed-unicorn-gemini.md`, Engine 3 searches | 2026-02-12 |
| Classical AI + "quantum-ready" positioning (P12) | "Quantum-ready" = modular software = zero differentiation. Post-Zapata, quantum branding may be negative signal. SandboxAQ succeeds on CLASSICAL products, not positioning. No moat. | `raw/2026-02-12-eng-gate-qc-preseed-unicorn-gemini.md`, Engine 3 searches | 2026-02-12 |

---

## 5. Promising Leads

*Ideas that survived the feasibility gauntlet. Ranked by promise.*

| Rank | Idea | Verdict | Timeline | Next Step |
|------|------|---------|----------|-----------|
| 1 | Inference-time QUBO/HUBO for LLM reasoning (QCR-LLM + NASA CR on D-Wave) | WOUNDED (weakened) | Now (framework works) / 2027+ (for quantum advantage) | **New critical finding:** Linear CR (68.2%) OUTPERFORMS Quadratic CR (65.2%) on BBH — the QUBO terms HURT accuracy (Finding 29). This is devastating: if quadratic interactions are noise, there is no QUBO to optimize. **Still need:** CR vs majority voting comparison. If CR doesn't beat majority voting AND linear beats quadratic, the entire QUBO reasoning direction is dead. QPU can't handle 900 dense vars. Hybrid is ~98% classical. Only remaining path: compressed 150-var CR QUBO on QPU (X18), or HUBO (QCR-LLM) on IBM, but BF-DCQO's quantum contribution is also "minimal." |
| 2 | Sparsity mask optimization (pruning) as QUBO | WOUNDED | Now (if dense QUBO found) / 2028+ (for QPU capacity) | Test whether structured filter pruning (64-512 vars) produces dense QUBO. Benchmark D-Wave hybrid vs classical SA on actual pruning QUBOs. |
| 3 | QUBO-native graph clustering (community detection, correlation clustering, k-medoids) | WOUNDED | Now (hardware exists) | Run critical experiment: D-Wave QPU (recursive binary splitting) vs Gurobi ILP for exact modularity on hard 100-150 node graphs. The quality comparison QPU vs exact classical hasn't been done — only QPU vs heuristics. |
| 4 | FMQA for expensive binary black-box optimization (well placement, CCUS, facility location) | WOUNDED (weakened) | Now (FMQA works classically) | **Updated (cycle 10):** FM QUBOs are DENSE but LOW-RANK (rank K=8-16). Dense + low-rank is NOT D-Wave's sweet spot (which was full-rank dense BQP). "Advantage Paradox": small K = easy QUBO, large K = hard but FM degrades. Diagonal terms may restore hardness -- empirical test needed. Classical MLP surrogates need fewer sims (~300 vs FMQA ~500-2000). QPU at 151 vars is 10.5% WORSE on Max-Cut. **Best remaining path:** FMQA as classical product (X36) -- no quantum needed. Quantum path requires full-rank dense QUBOs which FM structurally cannot produce at typical K. |
| 5 | Quantum chemistry simulation for catalyst design (gate-based, G1) | WOUNDED-ALIVE | 2029+ (fault-tolerant QC required) | **(NEW from eng cycle 11)** The ONE surviving gate-based quantum advantage direction. VQE on molecular Hamiltonians is dequantization-resistant. Chevron invested in OQC for exactly this. Microsoft/Quantinuum demonstrated 2 logical qubits for catalyst intermediate (Sep 2024). PhaseCraft THRIFT: 10x efficiency. BUT: requires 200+ logical qubits (2029+), competes with PhaseCraft/Microsoft/Quantinuum with 10-100x more funding, requires quantum chemistry expertise (not ML), 3-5 year timeline to useful results. NOT an ML product. NOT a pivot from current capabilities. A restart. |
| 6 | Quantum Sensing + Classical AI for semiconductor/battery inspection (P10, EuQlid model) | WOUNDED | Now (quantum sensors deployed) | **(NEW from eng cycle 17)** EuQlid ($3M seed, $1.5M early revenue) proves the exact business model: NV-diamond magnetometry + ML/signal processing → non-destructive 3D imaging → sell to semiconductor fabs. Quantum sensors are commercially real NOW. TAM: $860M→$1.56B (sensing), $22-56B (NDT). BUT: requires physics co-founder with NV-diamond or equivalent expertise. Superpose has ML team, not physics team. Competitors: QuantumDiamonds (€152M gov), SandboxAQ ($5.75B), Infleqtion ($100M+). Adversarial critique: moat is hardware supply chain, not software. Would need team pivot (add physics co-founder). The ONE path where quantum delivers value TODAY at $3M scale. |

---

## 6. Open Questions — Priority Ordered

1. ~~**What's actually inside D-Wave's hybrid solvers?**~~ **ANSWERED (2026-02-12).** Tabu search + simulated annealing on AWS CPUs/GPUs, with QPU processing small binary sub-problems (~1.4% of compute time). CQM continuous vars = linear only, processed classically. Does NOT bypass barriers. See Finding 1-3.

2. ~~**Are there ML problems that are naturally dense BQP at ~500 binary variables?**~~ **PARTIALLY ANSWERED (2026-02-12).** Sparsity mask optimization (pruning) is the best candidate: naturally binary, QUBO-amenable, right variable range. But the resulting QUBO is low-rank/sparse (not dense) due to Hessian structure. Remaining candidates: binary hash codes, BNN weights. Structured filter pruning (64-512 vars per stage) still untested for density.

3. **Can Stride's surrogate modeling integration (2026) change the calculus?** D-Wave's newest solver embeds ML models directly into optimization workflows. This inverts the relationship (ML helps quantum, not quantum helps ML). No independent benchmarks yet. Worth monitoring.

4. ~~**What does Advantage2 actually change?**~~ **PARTIALLY ANSWERED (2026-02-12).** Shipped 4,400 qubits (not 7K as planned). Zephyr 20-way connectivity. 40% energy scale + 75% noise reduction + 2x coherence. Advantage for physics simulation (Science 2025). Does NOT change optimization calculus -- the barrier is formulation, not qubit count.

5. **Can surrogate objectives make the eval bottleneck irrelevant?** If influence functions or embedding-based proxies can approximate the true objective within 10%, the eval barrier disappears. Still unexplored.

6. **What are quantum chemistry / optimization people doing about the scale barrier?** They've been hitting the same wall. Have they found solutions that transfer to ML? Still unexplored.

7. ~~**(NEW) Verify the npj Quantum Information 6561x speedup claim (arXiv:2504.06201).**~~ **ANSWERED (2026-02-12, eng cycle 2).** The paper used **D-Wave's Leap Hybrid sampler** (confirmed via search results showing "QA hardware with hybrid architecture" and "Leap Hybrid sampler"). Since hybrid is ~98% classical (Finding 2), the 6561x speedup reflects D-Wave's classical tabu search + SA implementation outperforming other classical solvers on dense BQP — NOT quantum advantage. The claim is misleading: it's a benchmark of D-Wave's classical software, not quantum hardware. Does not change our calculus.

8. **(NEW from eng cycle 2) Is the pruning QUBO dense for structured pruning (filter/head selection)?** Per-weight pruning produces low-rank QUBO (Finding 7). But structured pruning (selecting which filters/heads to keep) has different Hessian structure -- interactions between filters may be denser because each filter represents many weights. If the filter-level QUBO is dense at 64-512 variables, D-Wave could potentially help.

9. **(NEW from eng cycle 2) Can the pruning QUBO objective be reformulated to be artificially dense?** Instead of using the empirical Fisher (which is low-rank), could we use a different objective that produces dense Q_ij? E.g., kernel-based importance scores, gradient-free importance metrics, or information-theoretic measures. The tradeoff: denser QUBO may correlate less with actual model performance.

10. **(NEW from eng cycle 2) Benchmark D-Wave hybrid solver vs. classical SA on actual pruning QUBOs from iCBS.** No one has done this. iCBS uses classical SA to solve its QUBO blocks. What happens if you submit the same QUBOs to D-Wave's hybrid BQM solver? This is a straightforward experiment using the iCBS code (open-source at github.com/amazon-science/icbs).

11. **(NEW from eng cycle 2) Binary neural network (BNN) weight optimization as QUBO.** BNN layers have weights in {-1, +1}. Training a 512x64 BNN layer is literally a QUBO over 32K binary variables (too large for QPU). But small BNN classifiers or binary adapter layers (e.g., 64x64 = 4096 vars) with block decomposition could fit. Is there practical demand for small BNNs?

12. **(NEW from eng cycle 3) D-Wave QPU vs Gurobi ILP for exact modularity on hard 100-150 node instances.** All existing benchmarks compare QPU to heuristics (Louvain/Leiden). The ONE comparison that could reveal advantage — QPU vs exact ILP on instances where heuristics fail (the 80.6% suboptimal cases from Finding 16) — has never been done. If QPU finds exact or near-exact solutions faster than Gurobi on hard instances, there's a narrow but genuine advantage.

13. **(NEW from eng cycle 3) Batch small-graph clustering as amortized QPU advantage.** arXiv:2410.07744 showed 300x throughput vs hybrid DQM. If a workflow requires clustering many small graphs (molecular graphs, knowledge graph sub-structures), QPU throughput on small QUBOs could matter — not per-problem, but amortized. Needs rigorous comparison to parallelized classical batch processing.

14. **(NEW from eng cycle 3) K-medoids with dense dissimilarity QUBO as D-Wave sweet spot.** K-medoids medoid-only formulation produces a FULLY DENSE N-variable QUBO (the dissimilarity matrix). This IS D-Wave's sweet spot (Finding 5). But at N=150 (QPU limit), PAM solves in microseconds. Would only matter if we find a use case where N=150 candidates with the exact optimal k medoids is important and repeated many times.

15. **(NEW from eng cycle 3) Index tracking / portfolio replication as QUBO graph clustering.** arXiv:2003.03872 and U of Toronto thesis formulate market index tracking as graph clustering QUBO. ~500 stocks (S&P 500) with N*K vars. Classical methods (greedy, ILP) already handle this, but it's a real financial use case with discrete decisions and the QUBO IS the objective.

16. **(NEW from eng cycle 4) Does CR framework beat majority voting at same sample budget?** The single most critical experiment for the inference-time QUBO hypothesis. QCR-LLM (arXiv:2510.24509) shows +4.5-8.3pp over base GPT-4o with N=20 samples. But majority voting / self-consistency with N=20 samples is a strong baseline that QCR-LLM conspicuously does NOT compare against. If majority voting matches CR, the entire QUBO formulation is unnecessary overhead.

17. **(NEW from eng cycle 4) What are the HUBO coefficient distributions for real reasoning problems?** BF-DCQO's runtime advantage (arXiv:2505.08663) was demonstrated on HUBO instances with heavy-tailed (Cauchy/Pareto) coefficient distributions. QCR-LLM's HUBO coefficients come from co-occurrence statistics and sentence embeddings. If these are Gaussian/normal distributed (not heavy-tailed), BF-DCQO's advantage may not transfer.

18. ~~**(NEW from eng cycle 4) Submit NASA CR paper's QUBO formulation (avg 900 vars, quadratic only) to D-Wave.**~~ **PARTIALLY ANSWERED (2026-02-12, eng cycle 5).** Feasibility confirmed: NASA CR QUBO is ~98% dense, 900 vars is within hybrid BQM range (~15-18s solve time). BUT: QPU can't embed 900 dense vars (max clique ~150). Hybrid solver is ~98% classical. VeloxQ matches hybrid 1000x faster. The experiment is doable but would only test D-Wave's classical software vs other classical solvers. Real quantum test requires reducing to ~150 vars or using sparse decomposition. No open-source NASA CR code available (blocks experiment). See `raw/2026-02-12-eng-nasa-cr-dwave-claude.md`.

19. **(NEW from eng cycle 4) Does reasoning fragment count scale with problem difficulty?** Current BBEH tasks produce 35-120 fragments. For quantum advantage, we need 150+ fragments producing genuinely hard HUBO instances. As reasoning tasks get harder (AIME, research-level math, multi-step planning), do fragment counts grow, or does deduplication cap them?

20. ~~**(NEW from eng cycle 4) Is the inference-time QUBO hypothesis actually about D-Wave or IBM?**~~ **PARTIALLY ANSWERED (2026-02-12, eng cycle 5).** arXiv:2509.14358 shows D-Wave QPU outperforms BF-DCQO (IBM) on QUBO/Ising: 100x faster, better quality. For pure QUBO (NASA CR), D-Wave is the better quantum platform. For HUBO (QCR-LLM with cubic terms), BF-DCQO is the only option but its quantum contribution is "minimal." The hardware choice depends on whether we use QUBO (D-Wave) or HUBO (IBM), but neither currently provides advantage over classical SA.

21. **(NEW from eng cycle 5) What is the coefficient distribution of NASA CR QUBOs?** The co-occurrence coefficients c_ij derive from LLM sampling statistics. Are they Gaussian, heavy-tailed, or uniform? Heavy-tailed distributions (Cauchy/Pareto) make QUBOs harder for classical solvers and favor quantum approaches (per arXiv:2505.08663). If NASA CR coefficients are approximately Gaussian, the problem is easy for classical SA and quantum adds nothing. Nobody has characterized this.

22. **(NEW from eng cycle 5) Can NASA CR QUBO be compressed to ~150 variables for QPU testing?** If we aggressively cluster the ~200-900 distinct reasons into 150 meta-reasons (via stronger deduplication or hierarchical clustering), the resulting QUBO could fit on D-Wave's QPU as a dense K_150 instance. Tradeoff: coarser reason grouping may lose information. Worth testing whether downstream accuracy is preserved with 150 vs 900 variables.

23. **(NEW from eng cycle 5) Does D-Wave QPU provide advantage on 150-var dense QUBO over classical SA?** The Max-Cut benchmark (arXiv:2412.07460) shows QPU is 10.5% worse than optimal at n=151. But PRL scaling advantage (PRL 134, 160601) shows advantage on specific problem classes with high-precision couplings. The CR QUBO may or may not have the right coefficient structure. A direct experiment with a 150-var CR QUBO on Advantage2 QPU vs SA would answer this definitively.

24. **(NEW from eng cycle 5) Batch reasoning QUBO throughput on D-Wave QPU.** If serving 1000+ reasoning queries/minute, QPU's batch throughput (300x more sub-problems/min than hybrid per arXiv:2410.07744) could provide amortized advantage even if per-problem quality matches classical. This requires compressed ~150-var QUBOs and high query volume.

25. ~~**(NEW from eng cycle 7) Can RAG context selection be formulated as QUBO with pairwise embedding coefficients?**~~ **ANSWERED (2026-02-12).** Yes, the formulation is valid (binary include/exclude, pairwise cosine similarity redundancy matrix). BUT: (1) the quality gap between optimal and greedy is only 0.8-5.2% (SMART-RAG); (2) classical greedy DPP solves in <2ms; (3) D-Wave adds 15-18s latency; (4) the NLP community solved this with 7+ papers using greedy/DPP/submodular methods; (5) Finding 29 pattern suggests pairwise terms may hurt. **KILLED.** See `raw/2026-02-12-eng-chevron-rag-qubo-claude.md`.

26. **(NEW from eng cycle 9) Can FM surrogate capture well interference effects at 100-200 variables?** FM's quadratic form models pairwise interactions. Reservoir physics (pressure depletion, injection fronts) may require higher-order or nonlinear interactions that FM cannot capture. A 2-day experiment: train FM on well placement simulation data, measure prediction accuracy vs GP or neural network surrogates.

27. ~~**(NEW from eng cycle 9) Are FM-derived QUBOs dense or sparse at 200-500 variables for physics-based problems?**~~ **ANSWERED (2026-02-12, eng cycle 10).** FM QUBOs are DENSE (all Q_ij nonzero -- Gram matrix V*V^T has generically nonzero entries) but LOW-RANK (rank K, typically 8-16). Dense + low-rank != dense + full-rank. D-Wave's sweet spot (Finding 5) was benchmarked on full-rank dense BQP. Low-rank QUBOs are structurally easier for classical eigenvalue-guided methods. The "Advantage Paradox": small K = easy QUBO (no quantum advantage); large K = hard QUBO but FM fidelity degrades. Diagonal terms Q = diag(w) + V*V^T may restore hardness -- empirical test still needed. See Finding 60, `raw/2026-02-12-eng-chevron-fmqa-dense-claude.md`.

28. **(NEW from eng cycle 9) FMQA vs Bounce (NeurIPS 2023) head-to-head on 200+ binary variables with expensive evaluations.** No direct comparison exists. Both handle high-dimensional binary optimization. FMQA converts acquisition optimization to QUBO; Bounce uses nested embeddings. Head-to-head would determine if FMQA's FM surrogate provides genuine advantage over GP-based BO at scale.

29. **(NEW from eng cycle 10) Does the diagonal component w_i in Q = diag(w) + V*V^T restore QUBO hardness?** FM QUBOs have both diagonal (linear bias) and off-diagonal (pairwise interaction) terms. The off-diagonal part is low-rank (K=8-16), but the diagonal adds a full-rank component. If ||diag(w)|| >> ||V*V^T||, the problem is dominated by diagonal terms (trivially separable). If ||V*V^T|| >> ||diag(w)||, it is dominated by low-rank interactions (easy for eigenvalue methods). Only the intermediate regime is potentially hard. An empirical characterization of trained FM models is needed.

30. **(NEW from eng cycle 10) Does Advantage2 QPU close the 10.5% quality gap vs optimal on dense BQP at 150-177 vars?** Advantage2 has 40% higher energy scale, 75% less noise, 2x coherence vs Advantage. The Max-Cut 10.5% gap (Finding 15) was on Advantage (Pegasus), not Advantage2 (Zephyr). If Advantage2 closes this gap to <5%, QPU-native dense QUBO solving becomes competitive.

31. **(NEW from eng cycle 10) FMQA as classical consulting product for binary black-box optimization (X36)?** FMQA with classical SA genuinely outperforms Bayesian optimization at 100+ binary vars. Applied to well placement (100-200 binary candidates), it could reduce simulation cost from thousands to 500-2000 evaluations. No quantum needed. Competes with GA + MLP surrogate (~300 sims). Worth evaluating as a Superpose classical product independent of quantum.

32. **(NEW from eng cycle 11) Does gate-based quantum ML for energy have ANY path to advantage?** **ANSWERED (2026-02-12, eng cycle 11).** NO for ML on classical data. Quantum kernels killed (20K models, no advantage). QAOA killed (2-3x worse). QNN killed (barren plateau/simulability). QRC killed (never beats LSTM). Dequantization kills all quantum ML speedups on classical data. The ONLY surviving gate-based advantage is quantum chemistry (Hamiltonian simulation) which is not ML. See Findings 66-85 and `raw/2026-02-12-eng-gate-based-qml-energy-claude.md`.

33. **(NEW from eng cycle 11) Is quantum chemistry for catalyst design a viable Superpose product path?** Honest answer: theoretically yes, but practically very difficult. Requires: (a) fault-tolerant QC (2029+), (b) deep quantum chemistry expertise that Superpose doesn't have, (c) competing with PhaseCraft ($38M), Microsoft Azure Quantum Elements (infinite resources), Quantinuum ($10B), QC Ware/Promethium (NVIDIA-backed). Timeline: 3-5 years before useful results. This is a restart, not a pivot.

34. **(NEW from eng cycle 11) Monitor PhaseCraft/Microsoft/Quantinuum for 2026-2027 quantum chemistry advantage demonstrations.** If their materials simulation results show genuine quantum advantage, the market is validated. If not, the entire quantum chemistry thesis is also pushed out. PhaseCraft's XPRIZE submission is a key milestone. Microsoft's Starling (~200 logical qubits) targeted for 2029.

35. **(NEW from eng cycle 11) Can Superpose sell "quantum readiness consulting" to energy companies as bridge revenue?** Energy companies are investing (Chevron/OQC, Aramco/Pasqal) but producing zero results. They need honest assessment of which problems benefit from quantum. Near-term revenue opportunity but NOT a $100M+ product path.

36. **(NEW from eng cycle 12) Is "quantum-ready" positioning on a classical insurance AI product worth the narrative cost?** The cheapest possible quantum strategy: build Plan B5 (insurance AI), include "quantum-ready architecture" language in pitch deck. Costs nothing technically (just modular code design). Provides narrative differentiation. Risk: VCs may see through quantum branding without substance. Upside: if quantum materializes in 2030+, Superpose already has the brand association. Worth testing in investor conversations.

37. **(NEW from eng cycle 12) Does IonQ/Ansys 12% quantum advantage for ECAD simulation hold up?** IonQ press release claims 12% speedup on ECAD simulation — but this was from SIMULATION of quantum circuits, NOT from actual quantum hardware. No peer review, no reproducibility. Pattern: every "quantum advantage" claim for enterprise applications has been debunked on closer inspection. Monitor for peer-reviewed replication.

38. **(NEW from eng cycle 12) Can a quantum startup be built around Multiverse Computing's CompactifAI model (tensor network AI compression)?** Multiverse proves the market exists (EUR 100M ARR). But they have $250M+ funding, 160 patents, 7-year head start, 100+ customers. The question is NOT "is this market real?" (yes) but "can a $3M startup compete?" (almost certainly no). Only viable if Superpose finds a vertical niche Multiverse ignores.

39. **(NEW from eng cycle 13) Can a $3M pre-seed survive in AI-for-chemistry by picking an extreme vertical niche?** PhaseTree (€3M pre-seed) targets materials discovery for batteries/energy. Rowan ($2.1M) competes on UX/accessibility (8000 users). QSimulate ($11M total) has 5 of top-20 pharma. The pattern: small teams can enter but must pick a niche so narrow that CuspAI/Orbital/Microsoft don't bother. Candidates: specific catalyst class (CO2 reduction, ammonia synthesis), specific materials property (thermal conductivity), specific industry vertical (coatings, adhesives). Must validate that the niche is large enough ($50M+ TAM) but boring enough for giants to ignore.

40. **(NEW from eng cycle 13) Is Delta-ML (correcting DFT to CCSD(T) accuracy) a viable narrow product?** Delta-ML achieves CCSD(T) accuracy from DFT with ~200 training points. Could be productized as "accuracy upgrade" for existing DFT users. Lower competition than full molecular simulation platforms. But: who pays for incremental DFT accuracy improvement? Must validate willingness-to-pay.

41. **(NEW from eng cycle 13) Does open-source commoditization kill all AI-for-chemistry startup moats?** IBM FM4M, Meta Open Molecules, MACE/NequIP (open-source), NVIDIA BioNeMo all free. Schrödinger's moat is 30-year physics engine (not ML). CuspAI/Orbital moat is proprietary training data. A $3M startup has no data, no physics engine, no brand. What moat can it build? Possibilities: domain-specific fine-tuning, vertical integration with lab equipment, workflow automation around open-source models (Rowan's approach).

42. **(NEW from eng cycle 17) Can Superpose recruit a physics co-founder with NV-diamond or quantum sensing expertise?** The EuQlid model (P10) is the ONE path that works at $3M. But it requires a co-founder with condensed matter physics / NV-diamond fabrication background (like Walsworth/Glenn from Harvard/Yale). Without this person, the quantum sensing path is not viable. Must identify potential co-founders from academic labs (Harvard LISE, MIT Lincoln Lab, U of Melbourne, Stuttgart) or industry (Bosch Quantum Sensing, Element Six, Thales).

43. **(NEW from eng cycle 17) What specific quantum sensing vertical is underserved by QuantumDiamonds/EuQlid/SandboxAQ?** EuQlid targets semiconductor + battery inspection. QuantumDiamonds targets chip inspection. SandboxAQ targets defense navigation. Q-CTRL targets defense + minerals. Infleqtion targets atomic clocks + defense. What's LEFT? Candidates: (a) battery cell quality control (growing market, less defense red tape), (b) biomedical diagnostics (MEG/MCG, longer sales cycle), (c) geoscience/mining (gravimetry for resource exploration), (d) structural health monitoring (bridges, pipelines, aerospace). Must validate TAM and competitive gap per vertical.

44. ~~**(NEW from eng cycle 17) Is "quantum-ready" positioning valuable to investors in 2026?**~~ **ANSWERED (2026-02-12).** NO. Post-Zapata (bankrupt Oct 2024, restructured Sep 2025 as Zapata Quantum with $3M bridge), post-Kerrisdale Capital D-Wave short thesis, investors are skeptical of quantum positioning without substance. SandboxAQ succeeds by selling CLASSICAL products that work, not "quantum-ready" promises. "Quantum-ready" = zero differentiation (any team can design modular software). KILLED as strategy (P12). See Findings 113-116.

---

## 4. Ideas Graveyard

**X18 (eng cycle 14):** CR QUBO compression — **KILLED** by Encoding (accuracy loss) + Advantage (<10% QPU edge) gates. Raw: `2026-02-12-eng-cr-compress-qpu-{claude,grok}.md`.\n\n**S1 (eng cycle 15):** Hierarchical decomposition — **KILLED** by Scale (subs trivial classical) + Advantage (no preserved quantum edge). Raw: `2026-02-13-eng-S1-hierarchical-decomp-{grok}.md` (Claude sub-agent failed to output).

**P9 (eng cycle 17):** QC Infrastructure Software at $3M — **KILLED** by Competition (5+ funded incumbents: Classiq $173M, Riverlane $75M, Q-CTRL $50M+) + open-source commoditization. Raw: `2026-02-12-eng-gate-qc-preseed-unicorn-gemini.md`.

**P11 (eng cycle 17):** Narrow Quantum Chemistry at $3M — **KILLED for Superpose** by Team Fit (needs PhD quantum chemists) + Competition (QC Ware $42M, CuspAI $130M, Orbital $200M) + Timeline (pharma 6-18 month sales cycle vs $3M runway). Raw: same.

**P12 (eng cycle 17):** Classical AI + "quantum-ready" positioning — **KILLED** by Advantage (zero differentiation, any team can claim modular design) + post-Zapata negative signal risk. Raw: same.

*This document is updated after each engineering research cycle. Raw outputs in `research/raw/` with `eng-` prefix. All searches logged in `research/ENGINEERING-INDEX.md`.*
