import React from "react";
import type { MemoryMode } from "../types";
import { Brain, BrainCircuit } from "lucide-react";

interface Props {
  mode: MemoryMode;
}

export default function MemoryBadge({ mode }: Props) {
  if (mode === "with") {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-green-900 text-green-300 border border-green-600">
        <Brain size={12} />
        WITH MEMORY
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-gray-800 text-gray-400 border border-gray-600">
      <BrainCircuit size={12} />
      WITHOUT MEMORY
    </span>
  );
}
