import React from "react";
import type { ReviewOutput } from "../types";
import ReviewOutputPanel from "./ReviewOutputPanel";

interface Props {
  withoutReview: ReviewOutput;
  withReview: ReviewOutput;
}

export default function ComparisonView({ withoutReview, withReview }: Props) {
  return (
    <div className="w-full">
      <div className="text-center mb-6">
        <h2 className="text-lg font-bold text-gray-100">The Delta</h2>
        <p className="text-sm text-gray-400 mt-1">
          Same code. Same contributor. Completely different review quality.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ReviewOutputPanel review={withoutReview} mode="without" />
        <ReviewOutputPanel review={withReview} mode="with" />
      </div>
      <p className="text-center text-sm text-gray-400 mt-6 italic">
        "This is what code review looks like when your AI reviewer actually remembers your codebase."
      </p>
    </div>
  );
}
