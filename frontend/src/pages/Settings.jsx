import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

const NICHES = [
  { id: "nature_ambient", label: "Nature Ambient", desc: "Relaxing nature sounds and scenery" },
  { id: "cozy_indoor", label: "Cozy Indoor", desc: "Warm indoor atmospheres and ambience" },
  { id: "ocean_beach", label: "Ocean Beach", desc: "Waves, sand, and coastal vibes" },
  { id: "forest_mountain", label: "Forest Mountain", desc: "Serene forests and mountain landscapes" },
  { id: "japanese_zen", label: "Japanese Zen", desc: "Minimalist Japanese-inspired calm" },
  { id: "winter_snow", label: "Winter Snow", desc: "Peaceful winter scenes and snowfall" },
  { id: "custom", label: "Custom", desc: "Define your own niche" },
];

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "tr", label: "Turkish" },
  { code: "de", label: "German" },
  { code: "es", label: "Spanish" },
  { code: "ja", label: "Japanese" },
];

const KEY_STATUSES = {
  untested: { icon: "⬜", label: "Not tested", color: "text-gray-400" },
  valid: { icon: "✅", label: "Valid", color: "text-green-400" },
  invalid: { icon: "❌", label: "Invalid", color: "text-red-400" },
  unset: { icon: "⬜", label: "Not set", color: "text-gray-500" },
  testing: { icon: "🔄", label: "Testing...", color: "text-yellow-400" },
};

const API_KEY_FIELDS = [
  { key: "anthropic_api_key", label: "Anthropic API Key", testFn: () => api.testAnthropicKey() },
  { key: "openai_api_key", label: "OpenAI API Key", testFn: () => api.testOpenAIKey() },
  { key: "fal_api_key", label: "fal.ai Key", testFn: () => api.testFalKey() },
  { key: "apiframe_api_key", label: "Apiframe Key", testFn: () => api.testApiframeKey() },
];

export default function Settings() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("content");

  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.getSettings().then((r) => r.data),
  });

  const { data: a } = useQuery({
    queryKey: ["youtube-stats"],
    queryFn: () => api.getYouTubeStats().then((r) => r.data),
    retry: false,
    refetchOnMount: true,
    staleTime: 0,
  });
  const isConnected = a?.connected || a?.authenticated || !!a?.channel_name;

  const { data: dashStats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => api.getDashboardStats().then((r) => r.data),
    enabled: activeTab === "budget",
  });

  const [form, setForm] = useState(null);
  const [keyStatuses, setKeyStatuses] = useState({});
  const [keyValues, setKeyValues] = useState({});

  if (settings && form === null) {
    setForm({
      niche: settings.niche_theme ?? settings.niche ?? "nature_ambient",
      custom_niche: settings.custom_niche_description ?? settings.custom_niche ?? "",
      language: settings.language ?? "en",
      shorts_duration: settings.shorts_duration_seconds ?? settings.shorts_duration ?? 45,
      daily_budget: settings.daily_budget_usd ?? settings.daily_budget ?? 5,
      manual_override: settings.manual_override ?? false,
    });
    const initialKeys = {};
    API_KEY_FIELDS.forEach(({ key }) => {
      initialKeys[key] = settings[key] ? "••••••••" : "";
    });
    setKeyValues(initialKeys);
  }

  const updateSettings = useMutation({
    mutationFn: (data) => api.updateSettings(data).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  });

  const fv = form ?? {
    niche: "nature_ambient",
    custom_niche: "",
    language: "en",
    shorts_duration: 45,
    daily_budget: 5,
    manual_override: false,
  };

  const handleSave = () => {
    const payload = {
      niche_theme: fv.niche,
      custom_niche_description: fv.custom_niche,
      language: fv.language,
      shorts_duration_seconds: fv.shorts_duration,
      daily_budget_usd: fv.daily_budget,
      manual_override: fv.manual_override,
    };
    API_KEY_FIELDS.forEach(({ key }) => {
      const val = keyValues[key];
      if (val && !val.startsWith("•")) {
        payload[key] = val;
      }
    });
    updateSettings.mutate(payload);
  };

  const handleTestKey = async (field) => {
    setKeyStatuses((s) => ({ ...s, [field.key]: "testing" }));
    try {
      const res = await field.testFn();
      const valid = res?.data?.valid ?? true;
      setKeyStatuses((s) => ({ ...s, [field.key]: valid ? "valid" : "invalid" }));
    } catch {
      setKeyStatuses((s) => ({ ...s, [field.key]: "invalid" }));
    }
  };

  const handleConnect = async () => {
    try {
      const res = await api.login();
      const url = res?.data?.auth_url ?? res?.request?.responseURL;
      if (url) window.location.href = url;
    } catch (e) {
      // If login itself redirects via axios interceptor, nothing to do
    }
  };

  const TABS = [
    { id: "content", label: "Content" },
    { id: "api_keys", label: "API Keys" },
    { id: "budget", label: "Budget" },
    { id: "youtube", label: "YouTube" },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">Manage your TubeAuto configuration.</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-gray-900 rounded-xl border border-gray-800 p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === tab.id
                ? "bg-green-600 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab: Content */}
      {activeTab === "content" && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-6">
          {/* Auto-optimize toggle */}
          <div className="flex items-start justify-between gap-4 pb-4 border-b border-gray-800">
            <div>
              <p className="text-sm font-semibold text-white">
                🤖 Auto-optimize strategy
              </p>
              <p className="text-xs text-gray-400 mt-1">
                When enabled, TubeAuto automatically adjusts schedule, niche, and
                duration based on performance. Runs daily at 05:00 UTC.
              </p>
              {!fv.manual_override && (
                <p className="text-xs text-yellow-400 mt-1">
                  ⚠️ Niche, schedule, and duration fields are read-only while
                  auto-optimization is active.
                </p>
              )}
            </div>
            <button
              onClick={() =>
                setForm((f) => ({ ...f, manual_override: !f.manual_override }))
              }
              className={`relative flex-shrink-0 w-11 h-6 rounded-full transition-colors focus:outline-none ${
                !fv.manual_override ? "bg-green-600" : "bg-gray-600"
              }`}
              role="switch"
              aria-checked={!fv.manual_override}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                  !fv.manual_override ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* Niche selector */}
          <div>
            <label className="block text-sm font-semibold text-gray-300 mb-3">Niche</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {NICHES.map((niche) => (
                <button
                  key={niche.id}
                  onClick={() => setForm((f) => ({ ...f, niche: niche.id }))}
                  className={`text-left p-3 rounded-xl border transition-colors ${
                    fv.niche === niche.id
                      ? "border-green-500 bg-green-950/30"
                      : "border-gray-700 bg-gray-800/40 hover:border-gray-600"
                  }`}
                >
                  <div
                    className={`text-sm font-medium mb-1 ${
                      fv.niche === niche.id ? "text-green-400" : "text-white"
                    }`}
                  >
                    {niche.label}
                  </div>
                  <div className="text-xs text-gray-500">{niche.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Custom niche textarea */}
          {fv.niche === "custom" && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Custom niche description
              </label>
              <textarea
                rows={3}
                value={fv.custom_niche}
                onChange={(e) => setForm((f) => ({ ...f, custom_niche: e.target.value }))}
                placeholder="Describe your niche..."
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500 resize-none"
              />
            </div>
          )}

          {/* Language */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Language</label>
            <div className="flex flex-wrap gap-2">
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => setForm((f) => ({ ...f, language: lang.code }))}
                  className={`px-4 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                    fv.language === lang.code
                      ? "border-green-500 bg-green-950/30 text-green-400"
                      : "border-gray-700 text-gray-400 hover:border-gray-600"
                  }`}
                >
                  {lang.label}
                </button>
              ))}
            </div>
          </div>

          {/* Shorts duration */}
          <div>
            <div className="flex justify-between mb-2">
              <label className="text-sm font-medium text-gray-300">Shorts duration</label>
              <span className="text-sm font-semibold text-green-400">{fv.shorts_duration}s</span>
            </div>
            <input
              type="range"
              min={30}
              max={60}
              value={fv.shorts_duration}
              onChange={(e) =>
                setForm((f) => ({ ...f, shorts_duration: Number(e.target.value) }))
              }
              className="w-full accent-green-500"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>30s</span>
              <span>45s</span>
              <span>60s</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab: API Keys */}
      {activeTab === "api_keys" && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-4">
          {API_KEY_FIELDS.map((field) => {
            const status = keyStatuses[field.key];
            const isSet = settings?.[field.key];
            const statusKey = status ?? (isSet ? "untested" : "unset");
            const statusInfo = KEY_STATUSES[statusKey];

            return (
              <div key={field.key}>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-sm font-medium text-gray-300">{field.label}</label>
                  <span className={`text-xs ${statusInfo.color}`}>
                    {statusInfo.icon} {statusInfo.label}
                  </span>
                </div>
                <div className="flex gap-2">
                  <input
                    type="password"
                    value={keyValues[field.key] ?? ""}
                    onChange={(e) =>
                      setKeyValues((kv) => ({ ...kv, [field.key]: e.target.value }))
                    }
                    placeholder={isSet ? "Leave blank to keep existing" : "Enter API key"}
                    className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-green-500"
                  />
                  <button
                    onClick={() => handleTestKey(field)}
                    disabled={statusKey === "testing"}
                    className="px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white text-sm rounded-lg transition-colors whitespace-nowrap"
                  >
                    Test
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tab: Budget */}
      {activeTab === "budget" && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-6">
          {/* Daily budget slider */}
          <div>
            <div className="flex justify-between mb-2">
              <label className="text-sm font-medium text-gray-300">Daily budget</label>
              <span className="text-sm font-semibold text-green-400">${fv.daily_budget}</span>
            </div>
            <input
              type="range"
              min={1}
              max={20}
              value={fv.daily_budget}
              onChange={(e) =>
                setForm((f) => ({ ...f, daily_budget: Number(e.target.value) }))
              }
              className="w-full accent-green-500"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>$1</span>
              <span>$10</span>
              <span>$20</span>
            </div>
          </div>

          {/* Today spend vs budget */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-400">Today's spend</span>
              <span className="text-white">
                ${dashStats?.today_spend?.toFixed(2) ?? "0.00"} / ${fv.daily_budget}
              </span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full transition-all"
                style={{
                  width: `${Math.min(
                    100,
                    (((dashStats?.today_spend ?? 0) / fv.daily_budget) * 100)
                  )}%`,
                }}
              />
            </div>
          </div>

          {/* Total lifetime spend */}
          <div className="p-4 bg-gray-800 rounded-xl">
            <div className="text-sm text-gray-400 mb-1">Total lifetime spend</div>
            <div className="text-2xl font-bold text-white">
              ${dashStats?.total_spend?.toFixed(2) ?? "0.00"}
            </div>
          </div>

          {/* Cost estimates */}
          <div>
            <div className="text-sm font-medium text-gray-300 mb-3">Estimated cost per video</div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Short video (60s)</span>
                <span className="text-white">~$0.08</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Long video (30 min)</span>
                <span className="text-white">~$0.45</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Long video (60 min)</span>
                <span className="text-white">~$0.85</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: YouTube */}
      {activeTab === "youtube" && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-6">
          {isConnected ? (
            <>
              {/* Connected state */}
              <div className="flex items-center gap-4">
                {(a?.channel_avatar || a?.thumbnail) && (
                  <img
                    src={a.channel_avatar || a.thumbnail}
                    alt="Channel avatar"
                    className="w-16 h-16 rounded-full"
                  />
                )}
                <div>
                  <div className="text-lg font-semibold text-white">
                    {a?.channel_name ?? "Your Channel"}
                  </div>
                  <div className="text-sm text-gray-400">
                    {a?.subscriber_count != null
                      ? `${a.subscriber_count.toLocaleString()} subscribers`
                      : ""}
                  </div>
                  <div className="mt-1 flex items-center gap-1.5">
                    <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
                    <span className="text-sm text-green-400">Connected</span>
                  </div>
                </div>
              </div>

              {/* OAuth scopes */}
              {a?.scopes?.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-gray-300 mb-2">Granted permissions</div>
                  <ul className="space-y-1">
                    {a.scopes.map((scope) => (
                      <li key={scope} className="text-xs text-gray-400 font-mono bg-gray-800 px-2 py-1 rounded">
                        {scope}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Disconnect */}
              <button
                onClick={() => api.logout().then(() => queryClient.invalidateQueries())}
                className="px-4 py-2 bg-red-900/40 hover:bg-red-800/60 border border-red-800 text-red-400 text-sm font-medium rounded-lg transition-colors"
              >
                Disconnect Channel
              </button>
            </>
          ) : (
            <>
              {/* Not connected state */}
              <div className="text-center py-6">
                <div className="text-5xl mb-4">&#x1F4FA;</div>
                <div className="text-lg font-semibold text-white mb-2">No channel connected</div>
                <p className="text-sm text-gray-400 mb-6 max-w-xs mx-auto">
                  Connect your YouTube channel to start automating uploads.
                </p>
                <button
                  onClick={handleConnect}
                  className="px-6 py-2.5 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  Connect with Google
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Save button (not shown on youtube tab) */}
      {activeTab !== "youtube" && (
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={updateSettings.isLoading}
            className="px-5 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {updateSettings.isLoading ? "Saving..." : "Save"}
          </button>
          {updateSettings.isSuccess && (
            <span className="text-green-400 text-sm">Saved successfully.</span>
          )}
          {updateSettings.isError && (
            <span className="text-red-400 text-sm">Failed to save settings.</span>
          )}
        </div>
      )}
    </div>
  );
}
