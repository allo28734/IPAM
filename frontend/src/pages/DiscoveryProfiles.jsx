import React from 'react';

const DiscoveryProfiles = () => {
  const glassCardClass = "bg-bg-card backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-md transition-all hover:shadow-lg hover:border-white/20";
  return (
    <div className="flex-1 p-8">
      <header className="h-[var(--spacing-header)] bg-[#0f1115]/80 backdrop-blur-xl border-b border-white/10 flex items-center justify-between px-8 sticky top-0 z-30 -mt-8 -mx-8 mb-8">
        <h1 className="text-xl font-semibold">Discovery Profiles</h1>
      </header>
      <div className={glassCardClass}>
        <p>Discovery Profiles management interface coming soon.</p>
      </div>
    </div>
  );
};

export default DiscoveryProfiles;
