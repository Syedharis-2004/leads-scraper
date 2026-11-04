import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ActivityLogResponse } from '../models';

@Injectable({ providedIn: 'root' })
export class LogsService {
  private http = inject(HttpClient);
  private base = '/api/logs';

  getLogs(lines: number = 200, level: string = ''): Observable<ActivityLogResponse> {
    let params = new HttpParams().set('lines', String(lines));
    if (level) {
      params = params.set('level', level);
    }
    return this.http.get<ActivityLogResponse>(this.base, { params });
  }
}
