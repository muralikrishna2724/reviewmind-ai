import React from "react";
import { Code2 } from "lucide-react";

interface Props {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
}

export default function CodeInputArea({ value, onChange, readOnly = false }: Props) {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-700 bg-gray-800">
        <Code2 size={14} className="text-gray-400" />
        <span className="text-xs text-gray-400 font-mono">PR #5 — routes/orders.py</span>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        readOnly={readOnly}
        className="w-full bg-gray-900 text-green-300 font-mono text-sm p-4 resize-none outline-none min-h-[160px] leading-relaxed"
        placeholder="Paste code or PR diff here..."
        spellCheck={false}
      />
    </div>
  );
}
