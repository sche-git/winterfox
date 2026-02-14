/**
 * Cycle detail sheet with tabs: Summary, Synthesis, Agents, Searches.
 * Includes strategy display and finding type badges.
 */

import React, { useEffect } from 'react';
import { useCycleStore } from '../../stores/cycleStore';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import MarkdownContent from '@/components/ui/MarkdownContent';
import AgentRawOutput from '@/components/ui/AgentRawOutput';
import { getStrategyConfig, getFindingTypeConfig } from '@/lib/nodeTypes';
import type { AgentOutputSummary } from '../../types/api';
import {
  X,
  CheckCircle2,
  XCircle,
  Bot,
  Search,
  ChevronDown,
  MessageSquare,
} from 'lucide-react';

interface CycleDetailSheetProps {
  cycleId: number;
  onClose: () => void;
}

const CycleDetailSheet: React.FC<CycleDetailSheetProps> = ({ cycleId, onClose }) => {
  const detail = useCycleStore((s) => s.selectedCycleDetail);
  const loading = useCycleStore((s) => s.cycleDetailLoading);
  const loadCycleDetail = useCycleStore((s) => s.loadCycleDetail);

  useEffect(() => {
    loadCycleDetail(cycleId);
  }, [cycleId]);

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="flex h-full flex-col border-l bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-6 py-4 shrink-0">
        <div>
          <h3 className="text-base font-semibold">Cycle #{cycleId}</h3>
          {detail && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              {formatDuration(detail.duration_seconds)} &middot; ${detail.total_cost_usd.toFixed(4)}
              {detail.agent_count > 0 && ` \u00b7 ${detail.agent_count} agents`}
            </p>
          )}
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 hover:bg-muted"
        >
          <X className="h-4 w-4 text-muted-foreground" />
        </button>
      </div>

      {loading ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      ) : !detail ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-muted-foreground">Cycle not found</p>
        </div>
      ) : (
        <Tabs defaultValue="summary" className="flex min-h-0 flex-1 flex-col">
          <div className="border-b px-6 pt-2 shrink-0">
            <TabsList className="h-9">
              <TabsTrigger value="summary" className="text-xs">Summary</TabsTrigger>
              <TabsTrigger value="synthesis" className="text-xs">Synthesis</TabsTrigger>
              <TabsTrigger value="agents" className="text-xs">Agents</TabsTrigger>
              <TabsTrigger value="searches" className="text-xs">Searches</TabsTrigger>
              <TabsTrigger value="raw" className="text-xs">Raw Output</TabsTrigger>
            </TabsList>
          </div>

          {/* Summary Tab */}
          <TabsContent value="summary" className="m-0 overflow-auto flex-1">
            <div className="p-6 space-y-5">
              {/* Target */}
              {detail.target_claim && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Focus
                  </p>
                  <p className="mt-1.5 text-sm leading-relaxed">{detail.target_claim}</p>
                </div>
              )}

              {/* Strategy */}
              {detail.selection_strategy && (() => {
                const stratConfig = getStrategyConfig(detail.selection_strategy);
                return (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Strategy
                    </p>
                    <div className="mt-1.5 flex items-start gap-2">
                      <Badge variant="outline" className="text-[11px] shrink-0">
                        {stratConfig?.label ?? detail.selection_strategy}
                      </Badge>
                      {detail.selection_reasoning && (
                        <span className="text-sm text-muted-foreground leading-relaxed">
                          {detail.selection_reasoning}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* Status */}
              <div className="flex items-center gap-2">
                {detail.success ? (
                  <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <XCircle className="h-4 w-4 text-destructive" />
                )}
                <span className="text-sm">
                  {detail.success ? 'Completed successfully' : `Failed: ${detail.error_message}`}
                </span>
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <div className="text-xl font-semibold tabular-nums">{detail.directions_created}</div>
                  <div className="text-xs text-muted-foreground">Created</div>
                </div>
                <div>
                  <div className="text-xl font-semibold tabular-nums">{detail.directions_updated}</div>
                  <div className="text-xs text-muted-foreground">Updated</div>
                </div>
                <div>
                  <div className="text-xl font-semibold tabular-nums">{detail.directions_skipped}</div>
                  <div className="text-xs text-muted-foreground">Skipped</div>
                </div>
              </div>

              {/* Consensus findings */}
              {detail.consensus_directions.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Consensus ({detail.consensus_directions.length})
                  </p>
                  <div className="mt-2 space-y-2">
                    {detail.consensus_directions.map((claim, i) => (
                      <div key={i} className="rounded border p-2.5">
                        <p className="text-sm leading-relaxed">{claim}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Contradictions */}
              {detail.contradictions.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Contradictions ({detail.contradictions.length})
                  </p>
                  <div className="mt-2 space-y-2">
                    {detail.contradictions.map((c, i) => (
                      <div key={i} className="rounded border border-destructive/20 bg-destructive/5 p-2.5">
                        <p className="text-sm">{c.description || `${c.claim_a} vs ${c.claim_b}`}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Token usage */}
              {detail.total_tokens > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Token Usage
                  </p>
                  <div className="mt-2 text-sm tabular-nums text-muted-foreground">
                    {detail.total_tokens.toLocaleString()} tokens total
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Synthesis Tab */}
          <TabsContent value="synthesis" className="m-0 overflow-auto flex-1">
            <div className="p-6">
              {detail.synthesis_reasoning ? (
                <MarkdownContent content={detail.synthesis_reasoning} />
              ) : (
                <div className="text-center py-8">
                  <MessageSquare className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-3 text-sm text-muted-foreground">
                    No synthesis reasoning available.
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Synthesis is generated when multiple agents are used.
                  </p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Agents Tab */}
          <TabsContent value="agents" className="m-0 overflow-auto flex-1">
            <div className="p-6 space-y-4">
              {detail.agent_outputs.map((agent, i) => (
                <AgentSection key={i} agent={agent} />
              ))}
            </div>
          </TabsContent>

          {/* Searches Tab */}
          <TabsContent value="searches" className="m-0 overflow-auto flex-1">
            <div className="p-6 space-y-3">
              {detail.agent_outputs.flatMap((agent) =>
                agent.searches.map((s, i) => (
                  <div key={`${agent.agent_name}-${i}`} className="rounded border p-3">
                    <div className="flex items-center gap-2">
                      <Search className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-sm font-medium">{s.query}</span>
                    </div>
                    <div className="mt-1.5 flex items-center gap-3 text-xs text-muted-foreground">
                      {s.engine && <span>{s.engine}</span>}
                      <span>{s.results_count} results</span>
                      <span className="text-muted-foreground/60">{agent.agent_name}</span>
                    </div>
                  </div>
                ))
              )}
              {detail.agent_outputs.every((a) => a.searches.length === 0) && (
                <div className="text-center py-8">
                  <Search className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-3 text-sm text-muted-foreground">
                    No search records available
                  </p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Raw Output Tab */}
          <TabsContent value="raw" className="m-0 overflow-auto flex-1">
            <div className="p-6 space-y-4">
              {detail.agent_outputs.some((a) => a.raw_text) ? (
                detail.agent_outputs.map((agent, i) => (
                  <div key={i} className="rounded-md border">
                    <div className="flex items-center gap-2 border-b px-4 py-2.5">
                      <Bot className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">{agent.agent_name}</span>
                      {agent.role === 'primary' && (
                        <Badge variant="outline" className="text-[10px] py-0">primary</Badge>
                      )}
                    </div>
                    {agent.raw_text ? (
                      <div className="max-h-[600px] overflow-auto p-4">
                        <AgentRawOutput rawText={agent.raw_text} />
                      </div>
                    ) : (
                      <p className="p-4 text-xs text-muted-foreground">
                        No raw output available for this agent.
                      </p>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center py-8">
                  <MessageSquare className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-3 text-sm text-muted-foreground">
                    No raw output recorded
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Raw output is available for cycles run after this feature was added.
                  </p>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
};

/** Individual agent collapsible section */
function AgentSection({ agent }: { agent: AgentOutputSummary }) {
  const [open, setOpen] = React.useState(false);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex w-full items-center justify-between rounded-md border p-3 text-left hover:bg-muted/50">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-muted-foreground" />
          <div>
            <span className="text-sm font-medium">{agent.agent_name}</span>
            {agent.role === 'primary' && (
              <Badge variant="outline" className="ml-2 text-[10px] py-0">primary</Badge>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs tabular-nums text-muted-foreground">
            {agent.findings_count} directions, {agent.searches_performed} searches
          </span>
          <ChevronDown className={`h-3.5 w-3.5 text-muted-foreground transition-transform ${open ? 'rotate-180' : ''}`} />
        </div>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="mt-2 space-y-3 pl-6">
          {/* Agent metrics */}
          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            <span className="tabular-nums">${agent.cost_usd.toFixed(4)}</span>
            <span className="tabular-nums">{agent.duration_seconds.toFixed(1)}s</span>
            <span className="tabular-nums">{agent.total_tokens.toLocaleString()} tokens</span>
            {agent.model && <span>{agent.model}</span>}
          </div>

          {/* Self-critique - rendered as markdown */}
          {agent.self_critique && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Self-Critique</p>
              <div className="mt-1 rounded bg-muted p-3">
                <MarkdownContent content={agent.self_critique} />
              </div>
            </div>
          )}

          {/* Extracted directions */}
          {agent.findings.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Directions ({agent.findings.length})
              </p>
              <div className="mt-1.5 space-y-2">
                {agent.findings.map((f, i) => {
                  const ftConfig = getFindingTypeConfig(f.finding_type);
                  return (
                    <div key={i} className="rounded border p-2.5">
                      <div className="flex items-start gap-2">
                        <p className="flex-1 text-sm leading-relaxed">{f.claim}</p>
                        {ftConfig && (
                          <Badge variant="outline" className="text-[10px] py-0 shrink-0">
                            {ftConfig.label}
                          </Badge>
                        )}
                      </div>
                      <div className="mt-1.5 flex items-center gap-2">
                        <span className="text-xs tabular-nums text-muted-foreground">
                          {(f.confidence * 100).toFixed(0)}% confidence
                        </span>
                        {f.evidence.length > 0 && (
                          <span className="text-xs text-muted-foreground">
                            {f.evidence.length} evidence
                          </span>
                        )}
                        {f.tags.length > 0 && f.tags.map((t) => (
                          <Badge key={t} variant="secondary" className="text-[10px] py-0">{t}</Badge>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export default CycleDetailSheet;
