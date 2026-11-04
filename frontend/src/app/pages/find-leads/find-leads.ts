import { Component, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { GenerationService } from '../../core/services/generation.service';
import { SettingsService } from '../../core/services/settings.service';
import { GenerationStatus } from '../../core/models';

@Component({
  selector: 'app-find-leads',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 lg:p-8 max-w-4xl mx-auto">
      <h1 class="text-2xl font-bold text-white mb-1">Find Leads</h1>
      <p class="text-ink-400 text-sm mb-6">Describe the businesses you want to find in natural language</p>

      <!-- API key warning -->
      @if (!hasKey()) {
        <div class="card mb-6 border-amber-500/30 bg-amber-500/5">
          <div class="flex items-center gap-3">
            <svg class="w-5 h-5 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <div>
              <p class="text-amber-300 text-sm font-medium">No API key configured</p>
              <p class="text-amber-300/70 text-xs">You need a Google AI Studio API key to generate leads. Go to API Settings to add one.</p>
            </div>
          </div>
        </div>
      }

      <!-- Prompt input -->
      <div class="card mb-6">
        <label class="label" for="prompt">Lead Generation Prompt</label>
        <textarea
          id="prompt"
          class="input min-h-[140px] resize-y"
          placeholder="Find 50 digital marketing agencies in Karachi, Pakistan. Extract: company name, owner name, website, public business email, phone number, city, business description. Only collect publicly available business information."
          [(ngModel)]="prompt"
          [disabled]="isRunning()"
          (keydown.ctrl.enter)="onGenerate()"></textarea>

        <div class="flex items-center justify-between mt-3">
          <p class="text-xs text-ink-500">Ctrl+Enter to submit</p>
          <div class="flex items-center gap-3">
            @if (isRunning()) {
              <button class="btn-danger" (click)="onCancel()">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
                Cancel
              </button>
            } @else {
              <button class="btn-primary" (click)="onGenerate()" [disabled]="!prompt.trim() || !hasKey()">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
                Generate Leads
              </button>
            }
          </div>
        </div>
      </div>

      <!-- Example prompts -->
      @if (!isRunning() && !status() && prompt.length === 0) {
        <div class="card mb-6">
          <h3 class="card-title mb-3">Example Prompts</h3>
          <div class="space-y-2">
            @for (ex of examplePrompts; track ex) {
              <button class="w-full text-left p-3 rounded-lg bg-ink-800 hover:bg-ink-700 transition-colors text-sm text-ink-200"
                      (click)="prompt = ex">
                {{ ex }}
              </button>
            }
          </div>
        </div>
      }

      <!-- Progress -->
      @if (status()) {
        <div class="card mb-6 animate-fade-in">
          <div class="flex items-center justify-between mb-4">
            <h3 class="card-title">{{ stageLabel() }}</h3>
            <div class="flex items-center gap-2">
              @if (status()!.is_running) {
                <span class="badge-info animate-pulse-subtle">Running</span>
              } @else if (status()!.is_cancelled) {
                <span class="badge-warning">Cancelled</span>
              } @else if (status()!.error) {
                <span class="badge-error">Error</span>
              } @else {
                <span class="badge-success">Complete</span>
              }
            </div>
          </div>

          <p class="text-ink-300 text-sm mb-4">{{ status()!.message || 'Processing...' }}</p>

          <!-- Progress bar -->
          @if (status()!.is_running || status()!.is_completed) {
            <div class="progress-bar-bg mb-4">
              <div class="progress-bar-fill" [style.width.%]="status()!.progress"></div>
            </div>
          }

          <!-- Stats grid -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div class="bg-ink-800 rounded-lg p-3">
              <p class="text-xs text-ink-400">Discovered</p>
              <p class="text-lg font-semibold text-white">{{ status()!.websites_discovered }}</p>
            </div>
            <div class="bg-ink-800 rounded-lg p-3">
              <p class="text-xs text-ink-400">Processed</p>
              <p class="text-lg font-semibold text-white">{{ status()!.websites_processed }}</p>
            </div>
            <div class="bg-ink-800 rounded-lg p-3">
              <p class="text-xs text-ink-400">Leads Found</p>
              <p class="text-lg font-semibold text-teal-400">{{ status()!.leads_extracted }}</p>
            </div>
            <div class="bg-ink-800 rounded-lg p-3">
              <p class="text-xs text-ink-400">Duplicates</p>
              <p class="text-lg font-semibold text-ink-300">{{ status()!.duplicates_skipped }}</p>
            </div>
          </div>

          <!-- Failed URLs -->
          @if (status()!.failed_urls.length > 0) {
            <div class="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <p class="text-xs text-red-300 font-medium mb-1">Failed websites ({{ status()!.failed_urls.length }}):</p>
              <ul class="text-xs text-red-300/70 space-y-0.5 max-h-24 overflow-y-auto">
                @for (url of status()!.failed_urls; track url) {
                  <li class="truncate">{{ url }}</li>
                }
              </ul>
            </div>
          }

          <!-- Error -->
          @if (status()!.error) {
            <div class="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <p class="text-sm text-red-300">{{ status()!.error }}</p>
            </div>
          }

          <!-- Search config preview -->
          @if (status()!.search_config) {
            <div class="mt-4 p-3 rounded-lg bg-ink-800">
              <p class="text-xs text-ink-400 mb-2">Parsed Configuration</p>
              <div class="flex flex-wrap gap-2 text-xs">
                <span class="badge-neutral">{{ status()!.search_config?.business_type || 'Any' }}</span>
                <span class="badge-neutral">{{ status()!.search_config?.location || 'Any location' }}</span>
                <span class="badge-neutral">Limit: {{ status()!.search_config?.limit }}</span>
              </div>
            </div>
          }
        </div>
      }

      <!-- Completion message -->
      @if (status()?.is_completed && !status()?.error && !status()?.is_cancelled) {
        <div class="card border-teal-500/30 bg-teal-500/5 animate-fade-in">
          <div class="flex items-center gap-3">
            <svg class="w-6 h-6 text-teal-400 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <div>
              <p class="text-teal-300 font-medium">Generation complete!</p>
              <p class="text-teal-300/70 text-sm">
                {{ status()!.leads_extracted }} leads extracted, {{ status()!.duplicates_skipped }} duplicates skipped.
                View them in the All Leads page.
              </p>
            </div>
          </div>
        </div>
      }
    </div>
  `,
})
export class FindLeads implements OnDestroy {
  private generationService = inject(GenerationService);
  private settingsService = inject(SettingsService);

  prompt = '';
  hasKey = signal(false);
  status = signal<GenerationStatus | null>(null);
  isRunning = signal(false);

  private jobId: string | null = null;
  private pollInterval: ReturnType<typeof setInterval> | null = null;

  examplePrompts = [
    'Find 25 digital marketing agencies in Karachi, Pakistan. Extract company name, owner name, website, email, phone, city, and description.',
    'Find 30 software development companies in Lahore, Pakistan. Extract company name, website, email, phone, and description.',
    'Find 20 restaurants in Islamabad, Pakistan. Extract company name, website, phone, city, and description.',
    'Find 15 real estate agencies in Dubai, UAE. Extract company name, owner name, website, email, phone, and city.',
  ];

  constructor() {
    this.settingsService.getKeyStatus().subscribe({
      next: (res) => this.hasKey.set(res.has_key),
      error: () => this.hasKey.set(false),
    });
  }

  onGenerate() {
    if (!this.prompt.trim() || !this.hasKey() || this.isRunning()) return;

    this.status.set(null);
    this.isRunning.set(true);

    this.generationService.startGeneration(this.prompt.trim()).subscribe({
      next: (res) => {
        this.jobId = res.job_id;
        this.startPolling();
      },
      error: (err) => {
        this.isRunning.set(false);
        this.status.set({
          job_id: '',
          stage: 'error',
          message: 'Failed to start generation',
          total_websites: 0,
          websites_discovered: 0,
          websites_processed: 0,
          leads_extracted: 0,
          duplicates_skipped: 0,
          failed_websites: 0,
          failed_urls: [],
          progress: 0,
          is_running: false,
          is_completed: true,
          is_cancelled: false,
          error: err.error?.detail || err.message || 'Unknown error',
          search_config: null,
          new_lead_ids: [],
        });
      },
    });
  }

  private startPolling() {
    if (this.pollInterval) clearInterval(this.pollInterval);
    this.pollInterval = setInterval(() => {
      if (!this.jobId) return;
      this.generationService.getStatus(this.jobId).subscribe({
        next: (data) => {
          this.status.set(data);
          if (!data.is_running) {
            this.isRunning.set(false);
            this.stopPolling();
          }
        },
        error: (err) => {
          console.error('Polling error', err);
        },
      });
    }, 2000);
  }

  private stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  onCancel() {
    if (!this.jobId) return;
    this.generationService.cancelGeneration(this.jobId).subscribe({
      next: () => {
        this.stopPolling();
        this.isRunning.set(false);
      },
      error: (err) => console.error('Cancel error', err),
    });
  }

  stageLabel(): string {
    const stage = this.status()?.stage;
    const labels: Record<string, string> = {
      parsing_prompt: 'Interpreting Prompt',
      discovering: 'Discovering Businesses',
      scraping: 'Extracting Data',
      validating: 'Validating Data',
      saving: 'Saving Leads',
      complete: 'Complete',
      error: 'Error',
      cancelled: 'Cancelled',
      init: 'Starting...',
    };
    return labels[stage || ''] || stage || 'Processing';
  }

  ngOnDestroy() {
    this.stopPolling();
  }
}
