import React from "react";
import type { ReviewOutput, MemoryMode } from "../types";
import MemoryBadge from "./MemoryBadge";
import { AlertTriangle, ShieldAlert, User, ThumbsUp, FileText, AlertCircle } from "lucide-react";

interface Props {
  review: ReviewOutput | null;
  mode: MemoryMode;
  error?: string;
  loading?: boolean;
}

const Section = ({
  icon,
  title,
  items,
  color,
}: {
  icon: React.ReactNode;
  title: string;
  items: string[];
  color: string;
}) => (
  <div className="mb-4">
    <div className={`flex items-center gap-2 mb-2 text-sm font-bold ${color}`}>
      {icon}
      {title}
    </div>
    {items.length === 0 ? (
      <p className="text-xs text-gray-600 pl-5">None</p>
    ) : (
      <ul className="space-y-1 pl-5">
        {items.map((item, i) => (
          <li key={i} className="text-xs text-gray-300 leading-relaxed list-disc list-outside">
            {item}
          </li>
        ))}
      </ul>
    )}
  </div>
);

export default function ReviewOutputPanel({ review, mode, error, loading }: Props) {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-gray-400" />
          <h3 className="text-sm font-bold text-gray-200">Review Output</h3>
        </div>
        <MemoryBadge mode={mode} />
      </div>

      {loading && (
        <div className="text-blue-400 text-sm text-center py-8">Generating review...</div>
      )}

      {error && !loading && (
        <div className="flex items-start gap-2 bg-red-950 border border-red-800 rounded p-3 mb-4">
          <AlertCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      {!review && !loading && !error && (
        <p className="text-gray-600 text-xs text-center py-8">Submit code to generate a review</p>
      )}

      {review && !loading && (
        <>
          <Section
            icon={<ShieldAlert size={14} />}
            title="Critical Issues"
            items={review.critical_issues}
            color="text-red-400"
          />
          <Section
            icon={<AlertTriangle size={14} />}
            title="Team Convention Violations"
            items={review.convention_violations}
            color="text-yellow-400"
          />
          <Section
            icon={<User size={14} />}
            title="Contributor-Specific Patterns"
            items={review.contributor_patterns}
            color="text-orange-400"
          />
          <Section
            icon={<ThumbsUp size={14} />}
            title="Positive Signals"
            items={review.positive_signals}
            color="text-green-400"
          />
          <div className="mt-4 pt-4 border-t border-gray-700">
            <p className="text-xs text-gray-400 font-bold mb-1">Summary</p>
            <p className="text-xs text-gray-300 leading-relaxed">{review.summary}</p>
          </div>
        </>
      )}
    </div>
  );
}
