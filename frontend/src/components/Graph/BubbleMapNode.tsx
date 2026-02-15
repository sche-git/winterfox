import React from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';
import { parseClaimType } from '@/lib/nodeTypes';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type NodeStatus = 'active' | 'archived' | 'merged';

type BubbleNodeData = {
  id: string;
  claim: string;
  description: string | null;
  confidence: number;
  importance: number;
  nodeType: string | null;
  status: NodeStatus | null;
  matched: boolean;
  selected: boolean;
  focused: boolean;
  dimmed: boolean;
  onSelect: (id: string) => void;
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

const METRIC_HEIGHT = 34;
const STATUS_LABEL: Record<NodeStatus, string> = {
  active: 'Active',
  archived: 'Completed',
  merged: 'Merged',
};
const STATUS_CLASS: Record<NodeStatus, string> = {
  active: 'border-emerald-300 bg-emerald-50 text-emerald-700',
  archived: 'border-amber-300 bg-amber-50 text-amber-700',
  merged: 'border-slate-300 bg-slate-100 text-slate-700',
};

const BubbleMapNode: React.FC<NodeProps<BubbleNodeData>> = ({ data }) => {
  const parsed = parseClaimType(data.claim, data.nodeType);
  const width = 286;
  const confidencePct = clamp(Math.round(data.confidence * 100), 0, 100);
  const importancePct = clamp(Math.round(data.importance * 100), 0, 100);
  const confidenceHeight = Math.max(5, (confidencePct / 100) * METRIC_HEIGHT);
  const importanceHeight = Math.max(5, (importancePct / 100) * METRIC_HEIGHT);
  const label = parsed.claim.length > 120 ? `${parsed.claim.slice(0, 120)}...` : parsed.claim;
  const description = (data.description || '').trim();
  // Preserve single newlines as markdown line breaks.
  const markdownDescription = description.replace(/\n/g, '  \n');

  return (
    <div className={`relative w-[286px] ${data.dimmed ? 'opacity-30' : 'opacity-100'}`}>
      <Handle
        type="target"
        position={Position.Left}
        className="h-px w-px border-none bg-transparent"
        style={{ left: 0, top: '50%' }}
      />
      <button
        type="button"
        onClick={() => data.onSelect(data.id)}
        className="group relative block w-full rounded-xl text-left transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        aria-label={`Open node: ${parsed.claim}`}
      >
        <div
          className={`relative rounded-xl border px-3 py-2.5 shadow-sm transition-all ${
            data.selected
              ? 'border-cyan-500 bg-card shadow-[0_0_0_1px_rgba(6,182,212,0.35)]'
              : data.matched
                ? 'border-amber-500 bg-card shadow-[0_0_0_1px_rgba(245,158,11,0.38)]'
                : data.focused
                  ? 'border-slate-400 bg-card'
                  : 'border-border bg-card group-hover:border-slate-400'
          }`}
          style={{ width: `${width}px` }}
        >
          <div className="flex items-start gap-2.5">
            <div className="mt-0.5 flex shrink-0 items-start gap-1.5">
              <div className="flex flex-col items-center gap-1">
                <div className="h-[34px] w-1.5 rounded bg-muted">
                  <div
                    className="w-full rounded bg-cyan-500"
                    style={{ height: `${confidenceHeight}px`, marginTop: `${METRIC_HEIGHT - confidenceHeight}px` }}
                  />
                </div>
                <span className="text-[10px] tabular-nums text-muted-foreground">{confidencePct}%</span>
              </div>
              <div className="flex flex-col items-center gap-1">
                <div className="h-[34px] w-1.5 rounded bg-muted">
                  <div
                    className="w-full rounded bg-slate-600"
                    style={{ height: `${importanceHeight}px`, marginTop: `${METRIC_HEIGHT - importanceHeight}px` }}
                  />
                </div>
                <span className="text-[10px] tabular-nums text-muted-foreground">{importancePct}%</span>
              </div>
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <p className="min-w-0 flex-1 truncate text-xs font-semibold leading-snug text-foreground">{label}</p>
                {data.status && (
                  <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${STATUS_CLASS[data.status]}`}>
                    {STATUS_LABEL[data.status]}
                  </span>
                )}
              </div>
              {markdownDescription && (
                <div className="mt-1 max-h-[84px] overflow-hidden text-left text-[11px] leading-snug text-muted-foreground">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ children }) => <p className="mb-1">{children}</p>,
                      strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                      em: ({ children }) => <em className="italic">{children}</em>,
                      code: ({ children }) => (
                        <code className="rounded bg-muted px-1 py-0.5 text-[10px] text-foreground">{children}</code>
                      ),
                      ul: ({ children }) => <ul className="mb-1 ml-4 list-disc">{children}</ul>,
                      ol: ({ children }) => <ol className="mb-1 ml-4 list-decimal">{children}</ol>,
                    }}
                  >
                    {markdownDescription}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        </div>
      </button>
      <Handle
        type="source"
        position={Position.Right}
        className="h-px w-px border-none bg-transparent"
        style={{ right: 0, top: '50%' }}
      />
    </div>
  );
};

export default BubbleMapNode;
