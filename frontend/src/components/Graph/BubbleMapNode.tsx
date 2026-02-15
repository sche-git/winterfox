import React from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';
import { parseClaimType } from '@/lib/nodeTypes';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type BubbleNodeData = {
  id: string;
  claim: string;
  confidence: number;
  importance: number;
  nodeType: string | null;
  selected: boolean;
  focused: boolean;
  dimmed: boolean;
  onSelect: (id: string) => void;
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

const METRIC_HEIGHT = 34;

const BubbleMapNode: React.FC<NodeProps<BubbleNodeData>> = ({ data }) => {
  const parsed = parseClaimType(data.claim, data.nodeType);
  const width = 286;
  const confidencePct = clamp(Math.round(data.confidence * 100), 0, 100);
  const importancePct = clamp(Math.round(data.importance * 100), 0, 100);
  const confidenceHeight = Math.max(5, (confidencePct / 100) * METRIC_HEIGHT);
  const importanceHeight = Math.max(5, (importancePct / 100) * METRIC_HEIGHT);
  const label = parsed.claim.length > 170 ? `${parsed.claim.slice(0, 170)}...` : parsed.claim;
  const containsMarkdown = /[#*_`~\[\]\(\)\-|>]/.test(label);

  return (
    <div className={`relative ${data.dimmed ? 'opacity-30' : 'opacity-100'} max-w-[286px]`}>
      <Handle type="target" position={Position.Left} className="h-2 w-2 border-none bg-transparent" />
      <button
        type="button"
        onClick={() => data.onSelect(data.id)}
        className="group relative rounded-xl text-left transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        aria-label={`Open node: ${parsed.claim}`}
      >
        <div
          className={`relative rounded-xl border bg-card px-3 py-2.5 shadow-sm transition-all ${
            data.selected
              ? 'border-cyan-500 shadow-[0_0_0_1px_rgba(6,182,212,0.35)]'
              : data.focused
                ? 'border-slate-400'
                : 'border-border group-hover:border-slate-400'
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
              {containsMarkdown ? (
                <div className="max-h-[78px] overflow-hidden text-left text-xs leading-snug text-foreground">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ children }) => <p className="mb-1">{children}</p>,
                      strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                      em: ({ children }) => <em className="italic">{children}</em>,
                      code: ({ children }) => (
                        <code className="rounded bg-muted px-1 py-0.5 text-[10px]">{children}</code>
                      ),
                      ul: ({ children }) => <ul className="ml-4 list-disc">{children}</ul>,
                      ol: ({ children }) => <ol className="ml-4 list-decimal">{children}</ol>,
                    }}
                  >
                    {label}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="line-clamp-3 text-xs leading-snug text-foreground">{label}</p>
              )}

            </div>
          </div>
        </div>
      </button>
      <Handle type="source" position={Position.Right} className="h-2 w-2 border-none bg-transparent" />
    </div>
  );
};

export default BubbleMapNode;
