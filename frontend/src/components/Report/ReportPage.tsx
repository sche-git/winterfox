/**
 * Report page - Generate and display LLM-synthesized research reports.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  Copy,
  Check,
  Download,
  FileText,
  GitFork,
  Hash,
  Loader2,
  RefreshCw,
  Target,
  TrendingUp,
  Zap,
} from 'lucide-react';
import { api } from '../../services/api';
import { useGraphStore } from '../../stores/graphStore';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import MarkdownContent from '@/components/ui/MarkdownContent';
import type { Report } from '../../types/api';

type PageState = 'idle' | 'loading' | 'ready' | 'generating' | 'empty' | 'error';

const GENERATING_MESSAGES = [
  'Analyzing knowledge graph...',
  'Identifying key themes...',
  'Writing executive summary...',
  'Finalizing report...',
];

function stripFrontmatter(markdown: string): string {
  return markdown.replace(/^---[\s\S]*?---\n*/, '');
}

function formatElapsed(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

const ReportPage: React.FC = () => {
  const [state, setState] = useState<PageState>('idle');
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string>('');
  const [elapsed, setElapsed] = useState(0);
  const [copied, setCopied] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const summary = useGraphStore((s) => s.summary);

  // Load latest report on mount
  useEffect(() => {
    setState('loading');
    api.getLatestReport()
      .then((data) => {
        if (data) {
          setReport(data);
          setState('ready');
        } else {
          setState('empty');
        }
      })
      .catch((err) => {
        setError(err.message || 'Failed to load report');
        setState('error');
      });
  }, []);

  // Elapsed timer during generation
  useEffect(() => {
    if (state !== 'generating') return;

    setElapsed(0);
    const interval = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [state]);

  const handleGenerate = useCallback(async () => {
    setState('generating');
    setError('');

    try {
      const data = await api.generateReport();
      setReport(data);
      setState('ready');
    } catch (err: any) {
      if (err.response?.status === 409) {
        setError('Report generation already in progress');
      } else {
        setError(err.response?.data?.detail || err.message || 'Generation failed');
      }
      setState('error');
    }
  }, []);

  const handleCopy = useCallback(() => {
    if (!report) return;
    navigator.clipboard.writeText(report.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [report]);

  const handleDownload = useCallback(() => {
    if (!report) return;
    const blob = new Blob([report.markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'research-report.md';
    a.click();
    URL.revokeObjectURL(url);
  }, [report]);

  // Extract headings for TOC
  const headings = useMemo(() => {
    if (!report) return [];
    const content = stripFrontmatter(report.markdown);
    const matches = [...content.matchAll(/^(#{2,3})\s+(.+)$/gm)];
    return matches.map((m) => ({
      level: m[1].length as 2 | 3,
      text: m[2].replace(/\*\*/g, ''),
    }));
  }, [report]);

  const scrollToHeading = useCallback((text: string) => {
    if (!contentRef.current) return;
    const headingEls = contentRef.current.querySelectorAll('h2, h3');
    for (const el of headingEls) {
      if (el.textContent?.trim() === text.trim()) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        break;
      }
    }
  }, []);

  // Check if report is stale (new research since generation)
  const isStale = useMemo(() => {
    if (!report?.generated_at || !summary?.last_cycle_at) return false;
    return new Date(summary.last_cycle_at) > new Date(report.generated_at);
  }, [report?.generated_at, summary?.last_cycle_at]);

  // Loading state
  if (state === 'idle' || state === 'loading') {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Empty state
  if (state === 'empty') {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Card className="max-w-md text-center">
          <CardContent className="p-8">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-semibold">No report generated yet</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Generate a narrative research report synthesized from your knowledge graph.
              This uses the primary LLM and typically takes 30-60 seconds.
            </p>
            <Button onClick={handleGenerate} className="mt-6">
              Generate Report
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Generating state
  if (state === 'generating') {
    const messageIndex = Math.min(
      Math.floor(elapsed / 15),
      GENERATING_MESSAGES.length - 1,
    );

    return (
      <div className="flex h-full items-center justify-center p-8">
        <Card className="max-w-md text-center">
          <CardContent className="p-8">
            <Loader2 className="mx-auto h-12 w-12 animate-spin text-muted-foreground" />
            <h3 className="mt-4 text-lg font-semibold">Generating Report</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {GENERATING_MESSAGES[messageIndex]}
            </p>
            <p className="mt-3 text-2xl font-semibold tabular-nums text-muted-foreground">
              {formatElapsed(elapsed)}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state
  if (state === 'error') {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Card className="max-w-md text-center">
          <CardContent className="p-8">
            <AlertTriangle className="mx-auto h-12 w-12 text-destructive" />
            <h3 className="mt-4 text-lg font-semibold">Generation Failed</h3>
            <p className="mt-2 text-sm text-muted-foreground">{error}</p>
            <Button onClick={handleGenerate} className="mt-6">
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Ready state — report loaded
  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Research Report</h2>
          {report?.generated_at && (
            <p className="mt-1 text-sm text-muted-foreground">
              Generated {new Date(report.generated_at).toLocaleString()}
            </p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={handleGenerate}>
          <RefreshCw className="mr-2 h-3.5 w-3.5" />
          Regenerate
        </Button>
      </div>

      {/* Staleness banner */}
      {isStale && (
        <div className="mb-6 flex items-center justify-between rounded-md border border-amber-500/20 bg-amber-500/10 px-4 py-3">
          <p className="text-sm text-amber-700 dark:text-amber-400">
            New research data available since this report was generated.
          </p>
          <Button variant="outline" size="sm" onClick={handleGenerate} className="ml-4 shrink-0">
            Regenerate
          </Button>
        </div>
      )}

      {/* Content + Sidebar */}
      <div className="flex gap-8">
        {/* Report content */}
        <div ref={contentRef} className="min-w-0 flex-1 max-w-3xl">
          <Card>
            <CardContent className="p-6">
              <MarkdownContent content={stripFrontmatter(report?.markdown ?? '')} />
            </CardContent>
          </Card>
        </div>

        {/* Right sidebar */}
        <div className="hidden w-56 shrink-0 lg:block">
          <div className="sticky top-8 space-y-4">
            {/* Metadata */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Metadata
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2">
                  <GitFork className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">Nodes</span>
                  <span className="ml-auto text-sm font-medium tabular-nums">
                    {report?.node_count ?? 0}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Target className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">Cycles</span>
                  <span className="ml-auto text-sm font-medium tabular-nums">
                    {report?.cycle_count ?? 0}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">Confidence</span>
                  <span className="ml-auto text-sm font-medium tabular-nums">
                    {report ? `${(report.avg_confidence * 100).toFixed(0)}%` : '0%'}
                  </span>
                </div>
                {report && report.cost_usd > 0 && (
                  <div className="flex items-center gap-2">
                    <Zap className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Cost</span>
                    <span className="ml-auto text-sm font-medium tabular-nums">
                      ${report.cost_usd.toFixed(3)}
                    </span>
                  </div>
                )}
                {report && report.total_tokens > 0 && (
                  <div className="flex items-center gap-2">
                    <Hash className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Tokens</span>
                    <span className="ml-auto text-sm font-medium tabular-nums">
                      {report.total_tokens.toLocaleString()}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Actions */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-start"
                  onClick={handleCopy}
                >
                  {copied ? (
                    <Check className="mr-2 h-3.5 w-3.5" />
                  ) : (
                    <Copy className="mr-2 h-3.5 w-3.5" />
                  )}
                  {copied ? 'Copied!' : 'Copy Markdown'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-start"
                  onClick={handleDownload}
                >
                  <Download className="mr-2 h-3.5 w-3.5" />
                  Download .md
                </Button>
              </CardContent>
            </Card>

            {/* Table of Contents */}
            {headings.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Contents
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <nav className="space-y-1">
                    {headings.map((h, i) => (
                      <button
                        key={i}
                        onClick={() => scrollToHeading(h.text)}
                        className={`block w-full truncate text-left text-xs hover:text-foreground transition-colors ${
                          h.level === 3
                            ? 'pl-3 text-muted-foreground'
                            : 'font-medium text-muted-foreground'
                        }`}
                      >
                        {h.text}
                      </button>
                    ))}
                  </nav>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportPage;
