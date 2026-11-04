import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SettingsService } from '../../core/services/settings.service';
import { ApiKeyStatus, ApiKeyTestResult } from '../../core/models';

@Component({
  selector: 'app-api-settings',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 lg:p-8 max-w-3xl mx-auto">
      <h1 class="text-2xl font-bold text-white mb-1">API Settings</h1>
      <p class="text-ink-400 text-sm mb-6">Configure your Google AI Studio Gemini API key</p>

      <!-- Key status -->
      <div class="card mb-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="card-title">API Key Status</h2>
          @if (keyStatus()?.has_key) {
            <span class="badge-success">Configured</span>
          } @else {
            <span class="badge-error">Not Set</span>
          }
        </div>

        @if (keyStatus()?.has_key) {
          <div class="flex items-center gap-2 text-sm text-ink-300">
            <svg class="w-4 h-4 text-teal-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
            An API key is securely stored on this machine.
          </div>
        } @else {
          <div class="flex items-center gap-2 text-sm text-ink-300">
            <svg class="w-4 h-4 text-ink-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            No API key configured. Enter your key below to get started.
          </div>
        }

        <!-- Get key link -->
        <div class="mt-4 pt-4 border-t border-ink-700">
          <p class="text-xs text-ink-400 mb-2">Need an API key?</p>
          <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener" class="text-teal-400 text-sm hover:underline inline-flex items-center gap-1">
            Get a free key from Google AI Studio
            <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
          </a>
        </div>
      </div>

      <!-- Key input -->
      <div class="card mb-6">
        <h2 class="card-title mb-4">{{ keyStatus()?.has_key ? 'Update API Key' : 'Enter API Key' }}</h2>

        <label class="label" for="apiKey">Gemini API Key</label>
        <div class="relative">
          <input
            id="apiKey"
            [type]="showKey() ? 'text' : 'password'"
            class="input pr-10"
            placeholder="AIza..."
            [(ngModel)]="apiKey"
            autocomplete="off"/>
          <button
            type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 text-ink-400 hover:text-white p-1"
            (click)="showKey.set(!showKey())">
            @if (showKey()) {
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
              </svg>
            } @else {
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
              </svg>
            }
          </button>
        </div>

        <p class="text-xs text-ink-500 mt-1.5">Your key is stored securely using Windows Credential Manager. It never leaves your machine.</p>

        <div class="flex flex-wrap items-center gap-3 mt-4">
          @if (keyStatus()?.has_key) {
            <button class="btn-primary" (click)="updateKey()" [disabled]="!apiKey.trim() || saving()">
              {{ saving() ? 'Saving...' : 'Update Key' }}
            </button>
            <button class="btn-danger" (click)="removeKey()" [disabled]="removing()">
              {{ removing() ? 'Removing...' : 'Remove Key' }}
            </button>
          } @else {
            <button class="btn-primary" (click)="saveKey()" [disabled]="!apiKey.trim() || saving()">
              {{ saving() ? 'Saving...' : 'Save Key' }}
            </button>
          }
          <button class="btn-secondary" (click)="testKey()" [disabled]="testing()">
            {{ testing() ? 'Testing...' : 'Test Connection' }}
          </button>
        </div>
      </div>

      <!-- Test result -->
      @if (testResult()) {
        <div class="card mb-6 animate-fade-in" [class.border-teal-500]="testResult()!.valid" [class.border-red-500]="!testResult()!.valid">
          <div class="flex items-start gap-3">
            @if (testResult()!.valid) {
              <svg class="w-5 h-5 text-teal-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            } @else {
              <svg class="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            }
            <div>
              <p class="font-medium" [class.text-teal-300]="testResult()!.valid" [class.text-red-300]="!testResult()!.valid">
                {{ testResult()!.message }}
              </p>
              @if (testResult()!.detail) {
                <p class="text-sm text-ink-400 mt-1">{{ testResult()!.detail }}</p>
              }
              <p class="text-xs text-ink-500 mt-1">Model: {{ testResult()!.model }}</p>
            </div>
          </div>
        </div>
      }

      <!-- Model selection -->
      <div class="card">
        <h2 class="card-title mb-4">Gemini Model</h2>
        <label class="label" for="model">Select Model</label>
        <select id="model" class="input" [(ngModel)]="selectedModel" (ngModelChange)="onModelChange()">
          @for (model of keyStatus()?.available_models ?? []; track model) {
            <option [value]="model">{{ model }}</option>
          }
        </select>
        <p class="text-xs text-ink-500 mt-1.5">
          The selected model is used for prompt understanding and data extraction. Flash models are faster and cheaper.
        </p>
      </div>
    </div>
  `,
})
export class ApiSettings implements OnInit {
  private settingsService = inject(SettingsService);

  apiKey = '';
  showKey = signal(false);
  saving = signal(false);
  removing = signal(false);
  testing = signal(false);
  keyStatus = signal<ApiKeyStatus | null>(null);
  testResult = signal<ApiKeyTestResult | null>(null);
  selectedModel = 'gemini-2.0-flash';

  ngOnInit() {
    this.loadKeyStatus();
  }

  loadKeyStatus() {
    this.settingsService.getKeyStatus().subscribe({
      next: (res) => {
        this.keyStatus.set(res);
        this.selectedModel = res.model;
      },
      error: (err) => console.error('Failed to load key status', err),
    });
  }

  saveKey() {
    if (!this.apiKey.trim()) return;
    this.saving.set(true);
    this.settingsService.saveKey(this.apiKey.trim()).subscribe({
      next: () => {
        this.saving.set(false);
        this.apiKey = '';
        this.loadKeyStatus();
      },
      error: (err) => {
        this.saving.set(false);
        console.error('Save failed', err);
      },
    });
  }

  updateKey() {
    if (!this.apiKey.trim()) return;
    this.saving.set(true);
    this.settingsService.updateKey(this.apiKey.trim()).subscribe({
      next: () => {
        this.saving.set(false);
        this.apiKey = '';
        this.loadKeyStatus();
      },
      error: (err) => {
        this.saving.set(false);
        console.error('Update failed', err);
      },
    });
  }

  removeKey() {
    if (!confirm('Remove the stored API key? You will need to re-enter it to use lead generation.')) return;
    this.removing.set(true);
    this.settingsService.removeKey().subscribe({
      next: () => {
        this.removing.set(false);
        this.testResult.set(null);
        this.loadKeyStatus();
      },
      error: (err) => {
        this.removing.set(false);
        console.error('Remove failed', err);
      },
    });
  }

  testKey() {
    this.testing.set(true);
    this.testResult.set(null);
    const key = this.apiKey.trim() || undefined;
    this.settingsService.testKey(key).subscribe({
      next: (res) => {
        this.testing.set(false);
        this.testResult.set(res);
      },
      error: (err) => {
        this.testing.set(false);
        this.testResult.set({
          valid: false,
          model: this.selectedModel,
          message: 'Connection test failed',
          detail: err.error?.detail || err.message || 'Unknown error',
        });
      },
    });
  }

  onModelChange() {
    this.settingsService.setModel(this.selectedModel).subscribe({
      error: (err) => console.error('Model change failed', err),
    });
  }
}
