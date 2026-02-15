/**
 * Research Storyline page - vertical narrative of cycle progress.
 */

import React, { useMemo, useState } from 'react';
import { useCycleStore } from '../../stores/cycleStore';
import { api } from '../../services/api';
import type { Cycle, CycleDetail } from '../../types/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import AgentRawOutput from '@/components/ui/AgentRawOutput';
import MarkdownContent from '@/components/ui/MarkdownContent';
import {
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Bot,
  Search,
} from 'lucide-react';

type StoryFilter = 'all' | 'high_impact' | 'high_cost' | 'failures';
type CyclePanel = 'insights' | 'raw' | 'context';

const HistoryPage: React.FC = () => {
  const cycles = useCycleStore((s) => s.recentCycles);
  const [filter, setFilter] = useState<StoryFilter>('all');
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [details, setDetails] = useState<Record<number, CycleDetail>>({});
  const [loading, setLoading] = useState<Record<number, boolean>>({});
  const [panelByCycle, setPanelByCycle] = useState<Record<number, CyclePanel>>({});

  const avgCost = useMemo(() => {
    if (cycles.length === 0) return 0;
    return cycles.reduce((sum, c) => sum + c.total_cost_usd, 0) / cycles.length;
  }, [cycles]);

  const filteredCycles = useMemo(() => {
    switch (filter) {
      case 'high_impact':
        return cycles.filter((c) => c.directions_count >= 3);
      case 'high_cost':
        return cycles.filter((c) => c.total_cost_usd >= avgCost);
      case 'failures':
        return cycles.filter((c) => c.status === 'failed');
      default:
        return cycles;
    }
  }, [cycles, filter, avgCost]);

  const toggleExpand = async (cycle: Cycle) => {
    const isOpen = !!expanded[cycle.id];
    setExpanded((prev) => ({ ...prev, [cycle.id]: !isOpen }));

    if (!isOpen && !details[cycle.id] && !loading[cycle.id]) {
      setLoading((prev) => ({ ...prev, [cycle.id]: true }));
      try {
        const detail = await api.getCycle(cycle.id);
        setDetails((prev) => ({ ...prev, [cycle.id]: detail }));
      } finally {
        setLoading((prev) => ({ ...prev, [cycle.id]: false }));
      }
    }
  };

  const formatTimestamp = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '-';
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const chips = [
    { id: 'all' as const, label: 'All' },
    { id: 'high_impact' as const, label: 'High Impact' },
    { id: 'high_cost' as const, label: 'High Cost' },
    { id: 'failures' as const, label: 'Failures' },
  ];

  return (
    <div className="h-full overflow-auto p-6 md:p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold tracking-tight">Research Storyline</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Follow how each cycle advanced the investigation.
        </p>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {chips.map((chip) => (
          <Button
            key={chip.id}
            size="sm"
            variant={filter === chip.id ? 'default' : 'outline'}
            onClick={() => setFilter(chip.id)}
          >
            {chip.label}
          </Button>
        ))}
      </div>

      {filteredCycles.length === 0 ? (
        <div className="rounded-lg border bg-card p-10 text-center text-sm text-muted-foreground">
          No cycles match this filter.
        </div>
      ) : (
        <div className="relative pl-8">
          <div className="absolute left-3 top-1 bottom-1 w-px bg-border" />

          {filteredCycles.map((cycle, idx) => {
            const detail = details[cycle.id];
            const isOpen = !!expanded[cycle.id];
            const isLoading = !!loading[cycle.id];
            const directionCreated = detail?.directions_created ?? 0;
            const directionUpdated = detail?.directions_updated ?? 0;
            const consensus = detail?.consensus_directions ?? [];
            const panel = panelByCycle[cycle.id] ?? 'insights';
            const contextContent = detail?.research_context?.trim() ?? '';

            return (
              <article
                key={cycle.id}
                className="relative mb-5 opacity-0 animate-[fadeInUp_320ms_ease-out_forwards]"
                style={{ animationDelay: `${idx * 70}ms` }}
              >
                <div className="absolute -left-[22px] top-4 z-10 rounded-full border bg-background p-1">
                  {cycle.status === 'completed' ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-cyan-500" />
                  ) : cycle.status === 'failed' ? (
                    <XCircle className="h-3.5 w-3.5 text-destructive" />
                  ) : (
                    <Clock className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                  )}
                </div>

                <div className="rounded-2xl border bg-card p-4 shadow-sm transition-all hover:shadow-md">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => toggleExpand(cycle)}
                          className="text-sm font-semibold hover:underline"
                          aria-label={isOpen ? `Collapse cycle ${cycle.id}` : `Expand cycle ${cycle.id}`}
                        >
                          Cycle {cycle.id}
                        </button>
                        <Badge variant="outline" className="text-[10px] py-0">{formatTimestamp(cycle.started_at)}</Badge>
                      </div>
                      <MarkdownContent
                        content={cycle.target_claim || 'No target claim recorded'}
                        className="mt-2"
                      />
                    </div>
                    <button
                      onClick={() => toggleExpand(cycle)}
                      className="rounded p-1.5 hover:bg-muted"
                      aria-label={isOpen ? 'Collapse cycle' : 'Expand cycle'}
                    >
                      {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                    <Badge variant="secondary" className="font-normal text-muted-foreground">+{directionCreated || cycle.directions_count} directions</Badge>
                    <Badge variant="secondary" className="font-normal text-muted-foreground">~{directionUpdated} updates</Badge>
                    <Badge variant="outline" className="font-normal text-muted-foreground">Lead ${cycle.lead_llm_cost_usd.toFixed(3)}</Badge>
                    <Badge variant="outline" className="font-normal text-muted-foreground">Research ${cycle.research_agents_cost_usd.toFixed(3)}</Badge>
                    <Badge variant="outline" className="font-normal text-muted-foreground">{formatDuration(cycle.duration_seconds)}</Badge>
                  </div>

                  {isOpen && (
                    <div className="mt-4 space-y-4 border-t pt-4 animate-[fadeIn_220ms_ease-out]">
                      {isLoading ? (
                        <p className="text-xs text-muted-foreground">Loading cycle details...</p>
                      ) : detail ? (
                        <>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant={panel === 'insights' ? 'default' : 'outline'}
                              onClick={() => setPanelByCycle((prev) => ({ ...prev, [cycle.id]: 'insights' }))}
                            >
                              Insights
                            </Button>
                            <Button
                              size="sm"
                              variant={panel === 'raw' ? 'default' : 'outline'}
                              onClick={() => setPanelByCycle((prev) => ({ ...prev, [cycle.id]: 'raw' }))}
                            >
                              Agent Raw Output
                            </Button>
                            <Button
                              size="sm"
                              variant={panel === 'context' ? 'default' : 'outline'}
                              onClick={() => setPanelByCycle((prev) => ({ ...prev, [cycle.id]: 'context' }))}
                            >
                              Context Used
                            </Button>
                          </div>

                          {panel === 'insights' ? (
                            <>
                              {detail.selection_reasoning && (
                                <div>
                                  <p className="mb-1 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                    <Sparkles className="h-3 w-3" /> Lead Decision
                                  </p>
                                  <p className="text-sm leading-relaxed">{detail.selection_reasoning}</p>
                                </div>
                              )}

                              {detail.synthesis_reasoning && (
                                <div>
                                  <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Synthesis</p>
                                  <p className="line-clamp-5 text-sm leading-relaxed text-foreground">{detail.synthesis_reasoning}</p>
                                </div>
                              )}

                              {consensus.length > 0 && (
                                <div>
                                  <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Key Learnings</p>
                                  <ul className="space-y-1">
                                    {consensus.slice(0, 3).map((item, i) => (
                                      <li key={i} className="rounded-md bg-muted/60 px-2 py-1.5 text-sm">{item}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              <div className="grid grid-cols-1 gap-2 text-xs text-muted-foreground md:grid-cols-3">
                                <div className="rounded-md border p-2">
                                  <div className="flex items-center gap-1"><Bot className="h-3 w-3" /> Agents</div>
                                  <div className="mt-1 text-foreground">{detail.agent_count}</div>
                                </div>
                                <div className="rounded-md border p-2">
                                  <div className="flex items-center gap-1"><Search className="h-3 w-3" /> Searches</div>
                                  <div className="mt-1 text-foreground">
                                    {detail.agent_outputs.reduce((sum, agent) => sum + agent.searches_performed, 0)}
                                  </div>
                                </div>
                                <div className="rounded-md border p-2">
                                  <div>Tokens</div>
                                  <div className="mt-1 text-foreground tabular-nums">{detail.total_tokens.toLocaleString()}</div>
                                </div>
                              </div>
                            </>
                          ) : panel === 'raw' ? (
                            <div className="space-y-3">
                              {detail.agent_outputs.map((agent, i) => (
                                <div key={i} className="rounded-md border">
                                  <div className="border-b px-3 py-2">
                                    <p className="text-xs font-medium">{agent.agent_name}</p>
                                    <p className="mt-0.5 text-[11px] text-muted-foreground">
                                      ${agent.cost_usd.toFixed(4)} • {agent.searches_performed} searches • {agent.total_tokens.toLocaleString()} tokens
                                    </p>
                                  </div>
                                  <div className="max-h-[420px] overflow-auto p-3">
                                    <AgentRawOutput rawText={agent.raw_text} />
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : contextContent ? (
                            <div className="max-h-[520px] overflow-auto rounded-md border p-3">
                              <MarkdownContent content={contextContent} />
                            </div>
                          ) : (
                            <p className="text-xs text-muted-foreground">
                              Context snapshot is not available for this cycle.
                              Run a new cycle after this update to capture it.
                            </p>
                          )}
                        </>
                      ) : (
                        <p className="text-xs text-muted-foreground">Unable to load details for this cycle.</p>
                      )}
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default HistoryPage;
