'use client';

import { useState } from "react";
import Link from "next/link";

const linuxCommands = [
  'cat',
  'ls',
  'mv',
  'cp',
  'mkdir',
  'rm',
  'rmdir',
  'pwd',
  'touch',
  'echo',
  'find',
  'grep',
];

export default function CommandsPage() {
  const [monitoring, setMonitoring] = useState<Record<string, boolean>>(
    linuxCommands.reduce((acc, cmd) => ({ ...acc, [cmd]: false }), {})
  );

  const toggleMonitoring = (command: string) => {
    setMonitoring((prev) => ({
      ...prev,
      [command]: !prev[command],
    }));
  };

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-gray-50 via-white to-gray-100 dark:from-gray-950 dark:via-black dark:to-gray-900">
      {/* Header */}
      <header className="border-b border-gray-200/50 dark:border-gray-800/50 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <div className="flex items-center justify-between">
            <Link
              href="/"
              className="text-xl font-semibold bg-gradient-to-r from-blue-600 to-violet-600 bg-clip-text text-transparent dark:from-blue-400 dark:to-violet-400 hover:opacity-80 transition-opacity"
            >
              Agent Guardian
            </Link>
            <Link
              href="/commands"
              className="rounded-lg bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-2 text-sm font-medium text-white shadow-md transition-all hover:shadow-lg hover:shadow-blue-500/50"
            >
              Commands
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex flex-1 flex-col px-6 py-12">
        <div className="mx-auto w-full max-w-4xl space-y-8">
          {/* Title */}
          <div className="space-y-3">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-gray-50">
              Linux Commands Monitoring
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-400">
              Enable or disable monitoring for each Linux command
            </p>
          </div>

          {/* Commands List */}
          <div className="space-y-4">
            {linuxCommands.map((command) => (
              <div
                key={command}
                className="group relative rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition-all hover:border-blue-300 hover:shadow-md dark:border-gray-800 dark:bg-gray-900 dark:hover:border-blue-700"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 text-white font-mono font-semibold text-sm">
                      {command}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50 font-mono">
                        {command}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {monitoring[command] ? 'Monitoring enabled' : 'Monitoring disabled'}
                      </p>
                    </div>
                  </div>

                  {/* Toggle Switch */}
                  <button
                    onClick={() => toggleMonitoring(command)}
                    className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                      monitoring[command]
                        ? 'bg-gradient-to-r from-blue-600 to-violet-600'
                        : 'bg-gray-300 dark:bg-gray-700'
                    }`}
                    role="switch"
                    aria-checked={monitoring[command]}
                    aria-label={`Toggle monitoring for ${command}`}
                  >
                    <span
                      className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                        monitoring[command] ? 'translate-x-8' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                  Monitoring Summary
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {Object.values(monitoring).filter(Boolean).length} of {linuxCommands.length} commands being monitored
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-50">
                  {Object.values(monitoring).filter(Boolean).length}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Active
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200/50 px-6 py-4 text-center text-sm text-gray-500 dark:border-gray-800/50 dark:text-gray-400">
        Agent Guardian can make mistakes. Consider checking important information.
      </footer>
    </div>
  );
}

