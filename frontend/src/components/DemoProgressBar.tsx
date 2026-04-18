import React from "react";
import { Check } from "lucide-react";

const STEPS = [
  { n: 1, label: "Setup" },
  { n: 2, label: "Review 1" },
  { n: 3, label: "Inject Memory" },
  { n: 4, label: "Review 5" },
  { n: 5, label: "The Close" },
];

interface Props {
  currentStep: 1 | 2 | 3 | 4 | 5;
}

export default function DemoProgressBar({ currentStep }: Props) {
  return (
    <div className="flex items-center gap-0 w-full mb-8">
      {STEPS.map((step, idx) => {
        const done = step.n < currentStep;
        const active = step.n === currentStep;
        return (
          <React.Fragment key={step.n}>
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors
                  ${done ? "bg-green-500 border-green-500 text-white" : ""}
                  ${active ? "bg-blue-600 border-blue-400 text-white" : ""}
                  ${!done && !active ? "bg-gray-800 border-gray-600 text-gray-400" : ""}
                `}
              >
                {done ? <Check size={14} /> : step.n}
              </div>
              <span className={`text-xs mt-1 whitespace-nowrap ${active ? "text-blue-400" : done ? "text-green-400" : "text-gray-500"}`}>
                {step.label}
              </span>
            </div>
            {idx < STEPS.length - 1 && (
              <div className={`flex-1 h-0.5 mx-1 mb-5 ${done ? "bg-green-500" : "bg-gray-700"}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
