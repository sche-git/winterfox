# Example: Legal Tech SaaS Market Research

Complete research configuration for analyzing the legal tech SaaS market opportunity.

## Project Goal

Build a legal tech SaaS product targeting mid-market general counsels (companies with 100-1000 employees).

## Research Focus

- Market size and growth (TAM/SAM/SOM)
- Competition landscape (Harvey AI, Thomson Reuters, etc.)
- Buyer personas (pain points, budget, decision criteria)
- Pricing strategies (freemium, subscription tiers)
- Go-to-market channels (content, partnerships, sales)

## Quick Start

```bash
# 1. Create project directory
mkdir legal-tech-research
cd legal-tech-research

# 2. Copy this configuration
cp examples/market-research/winterfox.toml .

# 3. Set API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export TAVILY_API_KEY="tvly-..."

# 4. Run research
winterfox cycle -n 10

# 5. Export results
winterfox export report.md
```

## Expected Results

After 10-15 cycles (~$1-2 cost), you should have:

- **Market Size**: TAM, SAM, SOM with sources
- **Growth Rate**: CAGR and projections
- **Competition**: 5-10 competitors with positioning
- **Buyer Personas**: 2-3 detailed personas
- **Pain Points**: Top 5-10 validated pain points
- **Pricing**: Market pricing ranges and strategies
- **GTM**: Recommended channels and tactics

## Cost Estimate

- **Claude Opus 4.6**: ~$0.10 per cycle
- **Tavily Search**: ~$0.025 per cycle (25 searches)
- **Total**: ~$0.125 per cycle → **$1.25 for 10 cycles**

Add Kimi 2.5 for consensus: +$0.001 per cycle (negligible)

## Time Estimate

- **Single cycle**: 30-60 seconds
- **10 cycles**: 5-10 minutes
- **Until 0.8 confidence**: 20-30 cycles (~30-45 minutes)

## Sample Output Structure

```
Legal Tech SaaS Market Research
├── Market Opportunity (conf: 0.82)
│   ├── Legal Tech TAM (conf: 0.88)
│   │   ├── Market Size $50B by 2025 (conf: 0.92)
│   │   ├── Growth Rate 15% CAGR (conf: 0.85)
│   │   └── Geographic Breakdown (conf: 0.79)
│   ├── Mid-Market Segment (conf: 0.83)
│   │   ├── Segment Size $12B (conf: 0.86)
│   │   └── Fastest Growing at 18% (conf: 0.81)
│   └── Adoption Drivers (conf: 0.76)
├── Competition Landscape (conf: 0.81)
│   ├── Harvey AI (conf: 0.89)
│   │   ├── Enterprise Focus (conf: 0.91)
│   │   ├── Pricing $10k+/year (conf: 0.84)
│   │   └── Series C $80M (conf: 0.93)
│   ├── Thomson Reuters (conf: 0.86)
│   │   └── Westlaw Edge (conf: 0.88)
│   ├── LexisNexis (conf: 0.82)
│   └── CaseText (conf: 0.79)
├── Buyer Personas (conf: 0.74)
│   ├── Mid-Market GC Profile (conf: 0.78)
│   │   ├── Budget $50k-200k/year (conf: 0.81)
│   │   ├── Team Size 1-3 lawyers (conf: 0.84)
│   │   └── Pain Points (conf: 0.76)
│   └── Decision Process (conf: 0.71)
└── Pricing Strategy (conf: 0.68)
    ├── Freemium Adoption (conf: 0.72)
    ├── Tier Structure (conf: 0.69)
    └── ARR Benchmarks (conf: 0.65)
```

## Tips for This Project

### 1. Start Broad, Then Narrow

First 5 cycles: Let winterfox explore broadly
Next 5-10 cycles: Focus on specific areas with low confidence

```bash
# After initial exploration
winterfox cycle --focus "buyer personas" -n 5
winterfox cycle --focus "pricing strategy" -n 5
```

### 2. Use Interactive Mode for Control

```bash
winterfox interactive

# After each cycle, decide:
# - Continue broad research
# - Focus on specific area
# - Stop when satisfied
```

### 3. Monitor Confidence Trends

```bash
# Check after every 3-5 cycles
winterfox status

# Stop when:
# - Average confidence > 0.75
# - No low confidence areas (<0.5)
# - Cost budget reached
```

### 4. Export at Milestones

```bash
# Export after 5, 10, 15 cycles to track progress
winterfox export report-cycle5.md
winterfox export report-cycle10.md
winterfox export report-cycle15.md
```

## Customization

### For Faster/Cheaper Research

```toml
[orchestrator]
max_searches_per_agent = 15  # Reduce from 25
confidence_discount = 0.75  # Less skeptical

# Use only Kimi (100x cheaper)
[[agents]]
provider = "moonshot"
model = "kimi-2.5"
api_key_env = "MOONSHOT_API_KEY"
```

Cost: ~$0.01 per cycle → **$0.10 for 10 cycles**

### For Higher Quality

```toml
[orchestrator]
max_searches_per_agent = 40  # More thorough
confidence_discount = 0.6  # More skeptical

# Add 3rd agent
[[agents]]
provider = "openai"
model = "gpt-4o"
api_key_env = "OPENAI_API_KEY"
```

Cost: ~$0.20 per cycle → **$2.00 for 10 cycles**

### For Different Focus

Edit the `north_star` to emphasize different aspects:

```toml
# Focus on competition
north_star = """
Analyze the competitive landscape for legal tech SaaS.
Detailed competitive intelligence on top 10 players.
Focus on: features, pricing, positioning, strengths, weaknesses.
"""

# Focus on pricing
north_star = """
Determine optimal pricing strategy for legal tech SaaS.
Focus on: market pricing, willingness to pay, pricing models,
tier structures, discounting strategies.
"""
```

## Real-World Usage Notes

This example is based on actual market research methodology. After running this research:

1. **Validate with experts**: Interview 5-10 GCs to validate findings
2. **Build financial model**: Use TAM/SAM/SOM for projections
3. **Create positioning**: Use competitive analysis for differentiation
4. **Design product**: Use pain points to prioritize features
5. **Plan GTM**: Use buyer personas for channel selection

## See Also

- [Main README](../../README.md)
- [Getting Started Guide](../docs/GETTING_STARTED.md)
- [Configuration Reference](../docs/CONFIGURATION.md)
