import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LogsService } from '../../core/services/logs.service';
import { ActivityLogEntry } from '../../core/models';

@Component({
  selector: 'app-activity-logs',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 lg:p-8 max-w-5xl mx-auto">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-white mb-1">Activity Logs</h1>
          <p class="text-ink-400 text-sm">Application and API error logs</p>
        </div>
        <button class="btn-secondary" (click)="loadLogs()">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          Refresh
        </button>
      </div>

      <!-- Filter -->
      <div class="card mb-6">
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex-1 min-w-[200px]">
            <label class="label">Log Level</label>
            <select class="input" [(ngModel)]="levelFilter" (ngModelChange)="loadLogs()">
              <option value="">All Levels</option>
              <option value="INFO">Info</option>
              <option value="WARNING">Warning</option>
              <option value="ERROR">Error</option>
              <option value="DEBUG">Debug</option>
            </select>
          </div>
          <div>
            <label class="label">Lines</label>
            <select class="input" [(ngModel)]="lineCount" (ngModelChange)="loadLogs()">
              <option [ngValue]="100">100</option>
              <option [ngValue]="200">200</option>
              <option [ngValue]="500">500</option>
              <option [ngValue]="1000">1000</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Logs -->
      @if (loading()) {
        <div class="flex items-center gap-3 text-ink-400 py-12">
          <svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8"/>
          </svg>
          Loading logs...
        </div>
      } @else if (entries().length === 0) {
        <div class="text-center py-16 text-ink-400">
          <svg class="w-12 h-12 mx-auto mb-3 opacity-40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
          </svg>
          <p>No log entries found.</p>
        </div>
      } @else {
        <div class="card">
          <div class="space-y-1 max-h-[600px] overflow-y-auto font-mono text-xs">
            @for (entry of entries(); track $index) {
              <div class="flex gap-3 py-1 border-b border-ink-800/50 last:border-0">
                <span class="text-ink-500 whitespace-nowrap flex-shrink-0">{{ entry.timestamp || '—' }}</span>
                <span class="flex-shrink-0 font-semibold w-16"
                      [class.text-teal-400]="entry.level === 'INFO'"
                      [class.text-amber-400]="entry.level === 'WARNING'"
                      [class.text-red-400]="entry.level === 'ERROR'"
                      [class.text-blue-400]="entry.level === 'DEBUG'">
                  {{ entry.level || 'INFO' }}
                </span>
                <span class="text-ink-200 break-all">{{ entry.message }}</span>
              </div>
            }
          </div>
          <p class="text-xs text-ink-500 mt-3 text-center">{{ entries().length }} entries</p>
        </div>
      }
    </div>
  `,
})
export class ActivityLogs implements OnInit {
  private logsService = inject(LogsService);

  entries = signal<ActivityLogEntry[]>([]);
  loading = signal(true);
  levelFilter = '';
  lineCount = 200;

  ngOnInit() {
    this.loadLogs();
  }

  loadLogs() {
    this.loading.set(true);
    this.logsService.getLogs(this.lineCount, this.levelFilter).subscribe({
      next: (res) => {
        this.entries.set(res.entries);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load logs', err);
        this.loading.set(false);
      },
    });
  }
}
