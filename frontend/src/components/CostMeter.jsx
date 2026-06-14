import React from "react";

function getBarColor(pct) {
  if (pct > 95) return "bg-red-500";
  if (pct > 80) return "bg-yellow-400";
  return "bg-green-500";
}

export default function CostMeter({ spent = 0, budget = 1 }) {
  const safeBudget = budget > 0 ? budget : 1;
  const rawPct = (spent / safeBudget) * 100;
  const pct = Math.min(rawPct, 100);
  const barColor = getBarColor(pct);

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
      <h2 className="text-gray-100 font-semibold text-base mb-3">Today's Budget</h2>

      {/* Progress bar */}
      <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden mb-2">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Spent / Budget */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-300">
          <span className="font-semibold text-gray-100">
            ${Number(spent).toFixed(2)}
          </span>
          {" / "}
          <span className="text-gray-400">${Number(safeBudget).toFixed(2)}</span>
          <span className="text-gray-500 ml-1">spent today</span>
        </span>
        <span
          className={`text-xs font-medium ${
            pct > 95
              ? "text-red-400"
              : pct > 80
              ? "text-yellow-400"
              : "text-green-400"
          }`}
        >
          {pct.toFixed(1)}% used
        </span>
      </div>
    </div>
  );
}
