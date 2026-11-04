import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiKeyStatus, ApiKeyTestResult, AvailableModels, MessageResponse } from '../models';

@Injectable({ providedIn: 'root' })
export class SettingsService {
  private http = inject(HttpClient);
  private base = '/api/settings';

  getKeyStatus(): Observable<ApiKeyStatus> {
    return this.http.get<ApiKeyStatus>(`${this.base}/key`);
  }

  saveKey(apiKey: string): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.base}/key`, { api_key: apiKey });
  }

  updateKey(apiKey: string): Observable<MessageResponse> {
    return this.http.put<MessageResponse>(`${this.base}/key`, { api_key: apiKey });
  }

  removeKey(): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.base}/key`);
  }

  testKey(apiKey?: string): Observable<ApiKeyTestResult> {
    if (apiKey) {
      return this.http.post<ApiKeyTestResult>(`${this.base}/key/test`, { api_key: apiKey });
    }
    return this.http.get<ApiKeyTestResult>(`${this.base}/key/test`);
  }

  getAvailableModels(): Observable<AvailableModels> {
    return this.http.get<AvailableModels>(`${this.base}/models`);
  }

  setModel(model: string): Observable<MessageResponse> {
    return this.http.put<MessageResponse>(`${this.base}/model`, { model });
  }
}
