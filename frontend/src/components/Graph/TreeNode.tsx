/**
 * Single tree node with indentation lines, expand/collapse, type indicators,
 * and click-to-select.
 */

import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Circle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getNodeTypeConfig, parseClaimType } from '@/lib/nodeTypes';
import type { NodeTreeItem } from '../../types/api';

interface TreeNodeProps {
  node: NodeTreeItem;
  depth: number;
  selectedId: string | null;
  onSelect: (nodeId: string) => void;
  isLast: boolean;
  /** Tracks which ancestor depths have a continuing vertical line */
  lineFlags: boolean[];
}

const TreeNode: React.FC<TreeNodeProps> = ({
  node,
  depth,
  selectedId,
  onSelect,
  isLast,
  lineFlags,
}) => {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children.length > 0;
  const isSelected = selectedId === node.id;
  const confidencePct = Math.round(node.confidence * 100);
  const importancePct = Math.round(node.importance * 100);
  const parsed = parseClaimType(node.claim, node.node_type);
  const typeConfig = getNodeTypeConfig(parsed.nodeType);

  const handleRowClick = () => {
    onSelect(node.id);
  };

  const handleChevronClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };

  return (
    <div>
      {/* Node row */}
      <div
        onClick={handleRowClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && handleRowClick()}
        className={cn(
          'group flex cursor-pointer items-center overflow-hidden pr-3 py-[3px] transition-colors hover:bg-muted/60',
          isSelected && 'bg-secondary'
        )}
      >
        {/* Tree connector lines */}
        <div className="flex shrink-0 items-center self-stretch" style={{ width: `${depth * 20 + 8}px` }}>
          {/* Vertical lines from ancestors */}
          {Array.from({ length: depth }).map((_, i) => (
            <div key={i} className="relative h-full w-5 shrink-0">
              {lineFlags[i] && (
                <div className="absolute left-[9px] top-0 h-full w-px bg-border" />
              )}
            </div>
          ))}
        </div>

        {/* Branch connector for this node */}
        {depth > 0 && (
          <div className="relative -ml-5 flex h-6 w-5 shrink-0 items-center">
            {/* Vertical line (extends up, and down if not last) */}
            <div className={cn(
              'absolute left-[9px] w-px bg-border',
              isLast ? 'top-0 h-3' : 'top-0 h-full'
            )} />
            {/* Horizontal line */}
            <div className="absolute left-[9px] top-3 h-px w-[10px] bg-border" />
          </div>
        )}

        {/* Expand/collapse or leaf indicator */}
        <div
          onClick={hasChildren ? handleChevronClick : undefined}
          className={cn(
            'flex h-5 w-5 shrink-0 items-center justify-center rounded',
            hasChildren && 'hover:bg-muted cursor-pointer'
          )}
        >
          {hasChildren ? (
            expanded ? (
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
            )
          ) : (
            <Circle className="h-1.5 w-1.5 fill-muted-foreground text-muted-foreground" />
          )}
        </div>

        {/* Node type indicator */}
        {typeConfig ? (
          <div className={cn('ml-0.5 flex h-4 w-4 shrink-0 items-center justify-center', typeConfig.color)} title={typeConfig.label}>
            <typeConfig.icon className="h-3 w-3" />
          </div>
        ) : null}

        {/* Confidence + Importance mini bars (left of text) */}
        <div className="ml-1 flex shrink-0 flex-col gap-0.5" title={`Conf ${confidencePct}%  Imp ${importancePct}%`}>
          <div className="h-[3px] w-6 overflow-hidden rounded-full bg-border">
            <div
              className={cn('h-full rounded-full', typeConfig ? typeConfig.barColor : 'bg-foreground/50')}
              style={{ width: `${confidencePct}%` }}
            />
          </div>
          <div className="h-[3px] w-6 overflow-hidden rounded-full bg-border">
            <div className="h-full rounded-full bg-foreground/30" style={{ width: `${importancePct}%` }} />
          </div>
        </div>

        {/* Claim text */}
        <span className="ml-1.5 min-w-0 flex-1 truncate text-xs">
          {parsed.claim}
        </span>

        {/* Confidence percentage */}
        <span className={cn(
          'ml-1 shrink-0 w-7 text-right tabular-nums text-[10px]',
          typeConfig ? typeConfig.color : 'text-muted-foreground'
        )}>
          {confidencePct}%
        </span>
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div>
          {node.children.map((child, i) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              isLast={i === node.children.length - 1}
              lineFlags={[...lineFlags, !isLast]}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default TreeNode;
