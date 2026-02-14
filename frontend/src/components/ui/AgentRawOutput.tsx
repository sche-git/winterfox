import React, { useMemo } from 'react';
import MarkdownContent from './MarkdownContent';

interface AgentRawOutputProps {
  rawText: string;
}

function splitTrailingJson(rawText: string): { narrative: string; payload: unknown | null } {
  const trimmed = rawText.trim();
  if (!trimmed) return { narrative: '', payload: null };

  // First: json code fence at end.
  const fenceMatch = trimmed.match(/```json\s*([\s\S]*?)\s*```\s*$/i);
  if (fenceMatch) {
    try {
      const parsed = JSON.parse(fenceMatch[1]);
      const narrative = trimmed.slice(0, fenceMatch.index ?? 0).trim();
      return { narrative, payload: parsed };
    } catch {
      // Ignore; fall through.
    }
  }

  // Heuristic: parse a trailing JSON object/array from the end.
  const startCandidates: number[] = [];
  for (let i = 0; i < trimmed.length; i++) {
    const ch = trimmed[i];
    if (ch === '{' || ch === '[') startCandidates.push(i);
  }

  for (let i = startCandidates.length - 1; i >= 0; i--) {
    const start = startCandidates[i];
    const tail = trimmed.slice(start).trim();
    if (!tail) continue;

    try {
      const parsed = JSON.parse(tail);
      const narrative = trimmed.slice(0, start).trim();
      return { narrative, payload: parsed };
    } catch {
      // Keep scanning earlier candidates.
    }
  }

  return { narrative: trimmed, payload: null };
}

function looksLikeSearchPayload(payload: unknown): payload is Array<Record<string, unknown>> {
  if (!Array.isArray(payload) || payload.length === 0) return false;
  const first = payload[0];
  if (!first || typeof first !== 'object') return false;

  const rec = first as Record<string, unknown>;
  return ['url', 'title', 'snippet', 'description', 'content'].some((key) => key in rec);
}

const AgentRawOutput: React.FC<AgentRawOutputProps> = ({ rawText }) => {
  const { narrative, payload } = useMemo(() => splitTrailingJson(rawText), [rawText]);

  if (!rawText?.trim()) {
    return <p className="text-xs text-muted-foreground">No raw output available.</p>;
  }

  return (
    <div className="space-y-3">
      {narrative && <MarkdownContent content={narrative} />}

      {payload !== null && (
        <div className="rounded-md border bg-muted/30 p-3">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Parsed Tool/Search Payload
          </p>

          {looksLikeSearchPayload(payload) ? (
            <div className="space-y-2">
              {payload.slice(0, 12).map((item, i) => {
                const title = String(item.title ?? item.url ?? `Result ${i + 1}`);
                const url = item.url ? String(item.url) : null;
                const snippet = String(item.snippet ?? item.description ?? item.content ?? '').trim();

                return (
                  <div key={i} className="rounded-md border bg-background p-2.5">
                    <div className="text-xs font-medium">{title}</div>
                    {url && (
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-1 block truncate text-[11px] text-muted-foreground underline"
                      >
                        {url}
                      </a>
                    )}
                    {snippet && (
                      <p className="mt-1 text-xs text-muted-foreground line-clamp-3">{snippet}</p>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <pre className="max-h-72 overflow-auto rounded-md bg-background p-2 text-[11px]">
              {JSON.stringify(payload, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};

export default AgentRawOutput;
