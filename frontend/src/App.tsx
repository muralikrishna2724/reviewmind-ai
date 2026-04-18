import React, { useState } from "react";
import type { MemoryEntry, ReviewResponse } from "./types";
import { submitReview } from "./api";
import DemoProgressBar from "./components/DemoProgressBar";
import MemoryPanel from "./components/MemoryPanel";
import CodeInputArea from "./components/CodeInputArea";
import ReviewOutputPanel from "./components/ReviewOutputPanel";
import InjectMemoryButton from "./components/InjectMemoryButton";
import ComparisonView from "./components/ComparisonView";
import { Play, ChevronRight } from "lucide-react";

const DEFAULT_CODE = `async def get_user_orders(user_id: int, filters=[]):
    result = await db.query(Order).filter(Order.user_id == user_id).all()
    return result`;

const DEFAULT_CONTRIBUTOR = "Arjun Mehta";

type Step = 1 | 2 | 3 | 4 | 5;

export default function App() {
  const [step, setStep] = useState<Step>(1);
  const [code, setCode] = useState(DEFAULT_CODE);
  const [contributor] = useState(DEFAULT_CONTRIBUTOR);
  const [memoryEntries, setMemoryEntries] = useState<MemoryEntry[]>([]);
  const [memoryLoading, setMemoryLoading] = useState(false);
  const [reviewWithout, setReviewWithout] = useState<ReviewResponse | null>(null);
  const [reviewWith, setReviewWith] = useState<ReviewResponse | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState<string | undefined>();

  const advance = () => setStep((s) => Math.min(s + 1, 5) as Step);

  const handleReview1 = async () => {
    setReviewLoading(true);
    setReviewError(undefined);
    try {
      const result = await submitReview(code, contributor);
      setReviewWithout(result);
      setStep(2);
    } catch (e: unknown) {
      setReviewError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setReviewLoading(false);
    }
  };

  const handleMemoryInjected = (entries: MemoryEntry[]) => {
    setMemoryEntries(entries);
    setStep(4);
  };

  const handleReview5 = async () => {
    setReviewLoading(true);
    setReviewError(undefined);
    try {
      const result = await submitReview(code, contributor);
      setReviewWith(result);
      setStep(5);
    } catch (e: unknown) {
      setReviewError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setReviewLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">ReviewMind AI</h1>
        <p className="text-sm text-gray-400 mt-1">
          Persistent memory-powered code review · Crestline Software · Orion API
        </p>
      </div>

      {/* Progress */}
      <DemoProgressBar currentStep={step} />

      {/* Step 1: Setup */}
      {step === 1 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
              <h2 className="text-sm font-bold text-gray-200 mb-2">The Scenario</h2>
              <p className="text-xs text-gray-400 leading-relaxed">
                Sprint 14 at Crestline Software. <strong className="text-gray-200">Arjun Mehta</strong> has just opened PR #5 on the Orion API.
                Your team has reviewed 4 PRs this sprint. Does your reviewer remember what was flagged before?
              </p>
            </div>
            <CodeInputArea value={code} onChange={setCode} />
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500">Contributor: <span className="text-gray-300 font-mono">{contributor}</span></span>
            </div>
            <button
              onClick={handleReview1}
              disabled={reviewLoading}
              className="flex items-center gap-2 px-5 py-2.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white text-sm font-bold rounded-lg transition-colors"
            >
              <Play size={14} />
              Review Without Memory
            </button>
            {reviewError && <p className="text-xs text-red-400">{reviewError}</p>}
          </div>
          <div>
            <MemoryPanel entries={memoryEntries} loading={memoryLoading} />
          </div>
        </div>
      )}

      {/* Step 2: Review 1 — Without Memory */}
      {step === 2 && reviewWithout && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <CodeInputArea value={code} onChange={setCode} readOnly />
            <ReviewOutputPanel
              review={reviewWithout.review}
              mode="without"
              loading={reviewLoading}
              error={reviewError}
            />
            <button
              onClick={() => setStep(3)}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-700 hover:bg-blue-600 text-white text-sm font-bold rounded-lg transition-colors"
            >
              <ChevronRight size={14} />
              Next: Inject Memory
            </button>
          </div>
          <div>
            <MemoryPanel entries={memoryEntries} loading={memoryLoading} />
          </div>
        </div>
      )}

      {/* Step 3: Memory Injection */}
      {step === 3 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-gray-900 border border-blue-800 rounded-lg p-4">
              <h2 className="text-sm font-bold text-blue-300 mb-2">Load Team Memory</h2>
              <p className="text-xs text-gray-400 leading-relaxed mb-4">
                Inject the review history from PRs #1–4 into Hindsight. Watch the memory panel populate with
                team conventions, recurring mistakes, and architectural decisions.
              </p>
              <InjectMemoryButton
                onSuccess={handleMemoryInjected}
                onLoadingChange={setMemoryLoading}
              />
            </div>
          </div>
          <div>
            <MemoryPanel entries={memoryEntries} loading={memoryLoading} />
          </div>
        </div>
      )}

      {/* Step 4: Review 5 — With Memory */}
      {step === 4 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <CodeInputArea value={code} onChange={setCode} readOnly />
            {reviewWith ? (
              <ReviewOutputPanel
                review={reviewWith.review}
                mode="with"
                loading={reviewLoading}
                error={reviewError}
              />
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-gray-400">Same code. Now with full team memory loaded.</p>
                <button
                  onClick={handleReview5}
                  disabled={reviewLoading}
                  className="flex items-center gap-2 px-5 py-2.5 bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white text-sm font-bold rounded-lg transition-colors"
                >
                  <Play size={14} />
                  {reviewLoading ? "Reviewing..." : "Review With Memory"}
                </button>
                {reviewError && <p className="text-xs text-red-400">{reviewError}</p>}
              </div>
            )}
            {reviewWith && (
              <button
                onClick={advance}
                className="flex items-center gap-2 px-5 py-2.5 bg-purple-700 hover:bg-purple-600 text-white text-sm font-bold rounded-lg transition-colors"
              >
                <ChevronRight size={14} />
                See The Delta
              </button>
            )}
          </div>
          <div>
            <MemoryPanel entries={memoryEntries} loading={memoryLoading} />
          </div>
        </div>
      )}

      {/* Step 5: The Close — Side-by-side comparison */}
      {step === 5 && reviewWithout && reviewWith && (
        <ComparisonView
          withoutReview={reviewWithout.review}
          withReview={reviewWith.review}
        />
      )}
    </div>
  );
}
