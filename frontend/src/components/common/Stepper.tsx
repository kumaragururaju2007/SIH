import React from 'react';
import { Check } from 'lucide-react';

export interface StepItem {
  id: number;
  label: string;
  description?: string;
}

interface StepperProps {
  steps: StepItem[];
  activeStep: number;
  onStepClick?: (stepId: number) => void;
  className?: string;
}

export const Stepper: React.FC<StepperProps> = ({
  steps,
  activeStep,
  onStepClick,
  className = '',
}) => {
  return (
    <nav aria-label="Progress Stepper" className={`flex flex-col gap-2 ${className}`}>
      {steps.map((step, idx) => {
        const isCompleted = step.id < activeStep;
        const isActive = step.id === activeStep;
        const isClickable = !!onStepClick;

        return (
          <button
            key={step.id}
            type="button"
            onClick={() => isClickable && onStepClick?.(step.id)}
            disabled={!isClickable}
            aria-current={isActive ? 'step' : undefined}
            className={`w-full flex items-start gap-3 p-3 rounded-lg text-left transition-all ${
              isActive
                ? 'bg-primary text-white shadow-sm ring-1 ring-primary'
                : isCompleted
                ? 'bg-surface hover:bg-stone-100 text-stone-800 border border-stoneBorder'
                : 'bg-transparent text-stone-500 hover:bg-stone-100/50'
            }`}
          >
            {/* Step Number Circle */}
            <div
              className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold font-mono transition-colors ${
                isActive
                  ? 'bg-accent text-white'
                  : isCompleted
                  ? 'bg-status-verified text-white'
                  : 'bg-stone-200 text-stone-600'
              }`}
            >
              {isCompleted ? <Check className="w-3.5 h-3.5 stroke-[3]" /> : step.id}
            </div>

            <div className="flex-1 min-w-0">
              <div
                className={`text-xs font-semibold uppercase tracking-wider ${
                  isActive ? 'text-white' : 'text-stone-800'
                }`}
              >
                {step.label}
              </div>
              {step.description && (
                <div
                  className={`text-[11px] truncate mt-0.5 ${
                    isActive ? 'text-stone-200' : 'text-stone-500'
                  }`}
                >
                  {step.description}
                </div>
              )}
            </div>
          </button>
        );
      })}
    </nav>
  );
};
